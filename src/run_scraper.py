# run_scraper.py
import logging

import requests

from database import Database
from src.parser import build_session, search_vacancies
from src.scraper import get_vacancy_details
from src.utils import extract_vacancy_id

INSERT_SQL = """
    INSERT INTO vacancies (
        title, description, url, published_date, company, location, salary, salary_range, experience,
        employment_type, schedule, working_hours, work_format, skills,
        is_relevant, processed_at, sent_to_telegram, published_at
    ) VALUES (
        %(title)s, %(description)s, %(url)s, %(published_date)s, %(company)s, %(location)s, %(salary)s,
        %(salary_range)s, %(experience)s, %(employment_type)s, %(schedule)s, %(working_hours)s,
        %(work_format)s, %(skills)s,
        NULL, NOW(), FALSE, %(published_at)s
    ) ON CONFLICT (url) DO NOTHING;
"""


def load_known_vacancy_ids(db: Database) -> set[int]:
    conn = db.get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT url FROM vacancies")
            ids = {extract_vacancy_id(row[0]) for row in cursor.fetchall()}
        return {int(i) for i in ids if i}
    finally:
        db.return_connection(conn)


def save_vacancies(db: Database, rows: list[dict]) -> int:
    conn = db.get_connection()
    try:
        inserted = 0
        with conn.cursor() as cursor:
            for row in rows:
                cursor.execute(INSERT_SQL, row)
                inserted += cursor.rowcount
        conn.commit()
        return inserted
    finally:
        db.return_connection(conn)


def run_scraper(db: Database) -> int:
    """Находит новые вакансии на hh и сохраняет их в vacancies. Возвращает число вставленных."""
    known_ids = load_known_vacancy_ids(db)
    logging.info(f"📊 В БД уже есть {len(known_ids)} вакансий hh.")

    session = build_session()
    found = search_vacancies(session)
    new_ids = sorted(set(found) - known_ids)
    logging.info(f"🆕 Новых вакансий для загрузки: {len(new_ids)} из {len(found)} найденных.")

    rows = []
    failed = 0
    for idx, vacancy_id in enumerate(new_ids, 1):
        logging.info(f"[{idx}/{len(new_ids)}] Загружаем вакансию {vacancy_id}")
        try:
            row = get_vacancy_details(session, vacancy_id)
        except requests.RequestException as e:
            failed += 1
            logging.warning(f"[Vacancy] Сетевая ошибка для {vacancy_id}: {e}")
            continue
        if row:
            rows.append(row)

    if failed:
        logging.warning(f"⚠️ Не удалось загрузить {failed} вакансий, они попадут в следующий запуск.")
        if not rows:
            raise RuntimeError(f"Не загружена ни одна из {len(new_ids)} новых вакансий hh")

    if not rows:
        logging.info("✅ Нет новых вакансий для сохранения.")
        return 0

    inserted = save_vacancies(db, rows)
    logging.info(f"✅ Сохранено {inserted} новых вакансий в БД.")
    return inserted
