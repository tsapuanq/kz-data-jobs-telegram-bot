# parser.py
"""Поиск вакансий на hh.kz.

hh отдаёт в HTML встроенный JSON (<template id="HH-Lux-InitialState">) со всеми
вакансиями страницы — их 50, хотя в разметке без прокрутки отрисовано только 20.
Поэтому читаем JSON, а не CSS-селекторы.
"""
import html
import json
import logging
import random
import re
import time
from datetime import datetime, timedelta, timezone

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from src.config import (
    HH_AREA_ID,
    HH_BASE_URL,
    HH_LOOKBACK_DAYS,
    HH_MAX_PAGES_PER_QUERY,
    HH_PROFESSIONAL_ROLES,
    HH_REQUEST_DELAY_SECONDS,
    HH_REQUEST_TIMEOUT,
    HH_TITLE_QUERIES,
    HH_USER_AGENT,
)

_STATE_RE = re.compile(r'<template[^>]*id="HH-Lux-InitialState"[^>]*>(.*?)</template>', re.S)


class HHBlockedError(RuntimeError):
    """hh вернул страницу без данных (капча, блокировка, смена вёрстки)."""


def build_session() -> requests.Session:
    session = requests.Session()
    session.headers.update({"User-Agent": HH_USER_AGENT, "Accept-Language": "ru-RU,ru;q=0.9"})
    retry = Retry(
        total=3,
        backoff_factor=2,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=("GET",),
    )
    session.mount("https://", HTTPAdapter(max_retries=retry))
    return session


def fetch_state(session: requests.Session, url: str, params: dict | None = None) -> dict:
    """Загружает страницу hh и возвращает её встроенный JSON-state."""
    time.sleep(random.uniform(*HH_REQUEST_DELAY_SECONDS))
    resp = session.get(url, params=params, timeout=HH_REQUEST_TIMEOUT)
    resp.raise_for_status()
    match = _STATE_RE.search(resp.text)
    if not match:
        raise HHBlockedError(f"Нет HH-Lux-InitialState на {resp.url} (HTTP {resp.status_code})")
    return json.loads(html.unescape(match.group(1)))


def parse_hh_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    # hh пишет доли секунды 1–6 цифрами ("…:25.74+03:00"), а fromisoformat в Python 3.10
    # (версия в CI) принимает только 3 или 6 — дополняем до 6.
    value = re.sub(r"\.(\d{1,6})(?=[+-]\d{2}:\d{2}$|$)", lambda m: "." + m.group(1).ljust(6, "0"), value)
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        logging.warning(f"[HH] Не удалось разобрать дату: {value}")
        return None


def _search_pages(session: requests.Session, label: str, params: dict, cutoff: datetime) -> dict[int, dict]:
    """Листает выдачу (новые сверху), пока не дойдёт до вакансий старше cutoff."""
    found: dict[int, dict] = {}
    for page in range(HH_MAX_PAGES_PER_QUERY):
        state = fetch_state(
            session,
            f"{HH_BASE_URL}/search/vacancy",
            {**params, "area": HH_AREA_ID, "order_by": "publication_time", "page": page},
        )
        result = state.get("vacancySearchResult")
        if result is None:
            raise HHBlockedError(f"В state нет vacancySearchResult: {label}, страница {page + 1}")

        vacancies = result.get("vacancies") or []
        fresh = 0
        last_published = None
        for item in vacancies:
            last_published = parse_hh_datetime((item.get("publicationTime") or {}).get("$"))
            if last_published and last_published < cutoff:
                continue
            found[int(item["vacancyId"])] = item
            fresh += 1

        logging.info(
            f"[HH Search] {label}: страница {page + 1}, вакансий {len(vacancies)}, "
            f"свежих {fresh}, всего по запросу {result.get('totalResults')}"
        )
        next_page = (result.get("paging") or {}).get("next") or {}
        # Выдача отсортирована по дате публикации (кроме закреплённых сверху):
        # если последняя на странице уже старая — дальше только старее.
        reached_old = last_published is not None and last_published < cutoff
        if not vacancies or reached_old or next_page.get("disabled", True):
            break
    return found


def search_vacancies(session: requests.Session) -> dict[int, dict]:
    """Собирает свежие вакансии по профролям и по названию. Ключ — id вакансии hh."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=HH_LOOKBACK_DAYS)
    found: dict[int, dict] = {}

    found.update(
        _search_pages(session, "профроли", {"professional_role": HH_PROFESSIONAL_ROLES}, cutoff)
    )
    for query in HH_TITLE_QUERIES:
        found.update(
            _search_pages(session, f"название: {query[:40]}…", {"text": query, "search_field": "name"}, cutoff)
        )

    logging.info(f"✅ [HH Search] Уникальных свежих вакансий: {len(found)}")
    return found
