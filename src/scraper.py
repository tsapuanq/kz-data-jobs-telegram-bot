# scraper.py
"""Детали вакансии hh из встроенного JSON страницы (vacancyView.vacancyFull.vacancy).

Значения переводятся в тот же вид, в котором они уже хранятся в таблице vacancies
(«1–3 года», «5/2», «от 500 000 ₸ за месяц, на руки»), чтобы не ломать аналитику.
"""
import logging
import re
from datetime import datetime
from html.parser import HTMLParser
from zoneinfo import ZoneInfo

import requests

from src.config import HH_BASE_URL, LOCAL_TIMEZONE
from src.parser import fetch_state, parse_hh_datetime

NOT_SPECIFIED = "Не указано"

EXPERIENCE = {
    "noExperience": "не требуется",
    "between1And3": "1–3 года",
    "between3And6": "3–6 лет",
    "moreThan6": "более 6 лет",
}
EMPLOYMENT = {
    "FULL": "Полная занятость",
    "PART": "Частичная занятость",
    "PROJECT": "Проектная работа",
    "SIDE_JOB": "Подработка",
    "FLY_IN_FLY_OUT": "Вахта",
}
WORK_FORMATS = {
    "ON_SITE": "на месте работодателя",
    "REMOTE": "удалённо",
    "HYBRID": "гибрид",
    "FIELD_WORK": "разъездной",
}
SCHEDULE_WORDS = {"FLEXIBLE": "свободный", "WEEKEND": "по выходным", "OTHER": "другое"}
HOURS_WORDS = {"FLEXIBLE": "по договорённости", "OTHER": "другое"}
CURRENCIES = {"KZT": "₸", "RUR": "₽", "RUB": "₽", "USD": "$", "EUR": "€", "UZS": "сум", "KGS": "сом"}
SALARY_MODES = {"MONTH": "за месяц", "SHIFT": "за смену", "HOUR": "за час", "FLY_IN_FLY_OUT": "за вахту"}
MONTHS = [
    "января", "февраля", "марта", "апреля", "мая", "июня",
    "июля", "августа", "сентября", "октября", "ноября", "декабря",
]


def vacancy_url(vacancy_id: int | str) -> str:
    return f"{HH_BASE_URL}/vacancy/{vacancy_id}"


class _HtmlToText(HTMLParser):
    """Описание hh приходит HTML-ом: сохраняем абзацы и пункты списков."""

    BLOCK_TAGS = {"p", "div", "br", "ul", "ol", "h1", "h2", "h3", "h4"}

    def __init__(self):
        super().__init__()
        self.parts: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag == "li":
            self.parts.append("\n• ")
        elif tag in self.BLOCK_TAGS:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in self.BLOCK_TAGS:
            self.parts.append("\n")

    def handle_data(self, data):
        self.parts.append(data)


def html_to_text(value: str | None) -> str:
    if not value:
        return ""
    parser = _HtmlToText()
    parser.feed(value)
    text = "".join(parser.parts).replace("\xa0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r" *\n *", "\n", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def _codes(value) -> list[str]:
    """hh отдаёт списки кодов то списком, то {"...Element": [...]} — приводим к списку."""
    if isinstance(value, dict):
        value = next(iter(value.values()), [])
    if isinstance(value, str):
        return [value]
    return [v for v in (value or []) if isinstance(v, str)]


def _join_ru(items: list[str]) -> str:
    """["5/2", "свободный"] → "5/2 или свободный"; три и больше — через запятую."""
    items = [i for i in items if i]
    if not items:
        return NOT_SPECIFIED
    if len(items) == 1:
        return items[0]
    return ", ".join(items[:-1]) + " или " + items[-1]


def format_schedule(value) -> str:
    def one(code: str) -> str:
        match = re.fullmatch(r"([A-Z]+)_ON_([A-Z]+)_OFF", code)
        numbers = {"ONE": 1, "TWO": 2, "THREE": 3, "FOUR": 4, "FIVE": 5, "SIX": 6, "SEVEN": 7}
        if match and match.group(1) in numbers and match.group(2) in numbers:
            return f"{numbers[match.group(1)]}/{numbers[match.group(2)]}"
        return SCHEDULE_WORDS.get(code, code.lower())

    return _join_ru([one(c) for c in _codes(value)])


def format_working_hours(value) -> str:
    def one(code: str) -> str:
        match = re.fullmatch(r"HOURS_(\d+)", code)
        return match.group(1) if match else HOURS_WORDS.get(code, code.lower())

    return _join_ru([one(c) for c in _codes(value)])


def format_work_format(value) -> str:
    text = _join_ru([WORK_FORMATS.get(c, c.lower()) for c in _codes(value)])
    return text[:1].upper() + text[1:] if text != NOT_SPECIFIED else text


def _money(amount) -> str:
    return f"{int(amount):,}".replace(",", " ")


def format_salary(compensation: dict | None) -> tuple[str, str]:
    """Возвращает (salary, salary_range) в формате, который уже лежит в БД."""
    compensation = compensation or {}
    low, high = compensation.get("from"), compensation.get("to")
    if compensation.get("noCompensation") or (low is None and high is None):
        return NOT_SPECIFIED, NOT_SPECIFIED

    code = compensation.get("currencyCode") or ""
    currency = CURRENCIES.get(code, code)
    if low is not None and high is not None:
        amount, short = f"от {_money(low)} до {_money(high)}", f"{int(low)}-{int(high)}"
    elif low is not None:
        amount, short = f"от {_money(low)}", f"от {int(low)}"
    else:
        amount, short = f"до {_money(high)}", f"до {int(high)}"

    parts = [f"{amount} {currency}".strip()]
    mode = SALARY_MODES.get(compensation.get("mode") or "")
    if mode:
        parts[0] += f" {mode}"
    if compensation.get("gross") is True:
        parts.append("до вычета налогов")
    elif compensation.get("gross") is False:
        parts.append("на руки")
    return ", ".join(parts), f"{short} {currency}".strip()


def to_local_date(value: str | None):
    published = parse_hh_datetime(value)
    if not published:
        return None
    return published.astimezone(ZoneInfo(LOCAL_TIMEZONE)).date()


def format_ru_date(value) -> str:
    return f"{value.day} {MONTHS[value.month - 1]} {value.year}" if value else ""


def vacancy_to_row(vacancy: dict) -> dict | None:
    """Переводит JSON вакансии hh в строку таблицы vacancies."""
    description = html_to_text(vacancy.get("description"))
    if not description:
        return None

    published_at = to_local_date(vacancy.get("publicationTimeIso"))
    salary, salary_range = format_salary(vacancy.get("compensation"))
    employment = EMPLOYMENT.get(vacancy.get("employmentForm") or "", NOT_SPECIFIED)
    if vacancy.get("internship"):
        employment = f"{employment}\nСтажировка"
    skills = [s.strip() for s in vacancy.get("keySkills") or [] if isinstance(s, str) and s.strip()]

    return {
        "title": (vacancy.get("name") or "").strip() or NOT_SPECIFIED,
        "company": ((vacancy.get("company") or {}).get("name") or "").strip() or NOT_SPECIFIED,
        "location": ((vacancy.get("area") or {}).get("name") or "").strip() or NOT_SPECIFIED,
        "salary": salary,
        "salary_range": salary_range,
        "description": description,
        "experience": EXPERIENCE.get(vacancy.get("workExperience") or "", NOT_SPECIFIED),
        "employment_type": employment,
        "schedule": format_schedule(vacancy.get("workScheduleByDays")),
        "working_hours": format_working_hours(vacancy.get("workingHours")),
        "work_format": format_work_format(vacancy.get("workFormats")),
        "published_at": published_at,
        "published_date": format_ru_date(published_at),
        "skills": ", ".join(skills) if skills else NOT_SPECIFIED,
        "url": vacancy_url(vacancy["vacancyId"]),
    }


def get_vacancy_details(session: requests.Session, vacancy_id: int) -> dict | None:
    """Скачивает страницу вакансии. None — вакансию нельзя взять (архив, удалена, без описания)."""
    url = vacancy_url(vacancy_id)
    try:
        state = fetch_state(session, url)
    except requests.HTTPError as e:
        if e.response is not None and e.response.status_code in (404, 410):
            logging.warning(f"[Vacancy] Недоступна ({e.response.status_code}): {url}")
            return None
        raise

    vacancy = ((state.get("vacancyView") or {}).get("vacancyFull") or {}).get("vacancy")
    if not vacancy:
        logging.warning(f"[Vacancy] На странице нет данных вакансии: {url}")
        return None
    if (vacancy.get("status") or {}).get("archived"):
        logging.info(f"[Vacancy] В архиве, пропускаем: {url}")
        return None

    row = vacancy_to_row(vacancy)
    if row is None:
        logging.warning(f"[Vacancy] Пропуск вакансии без описания: {url}")
        return None
    logging.info(f"[Vacancy] ✅ {row['title']} — {row['company']} ({row['location']})")
    return row
