# run_all.py
import logging
import os
import sys

from database import Database
from src.publisher import run_publisher
from src.run_scraper import run_scraper
from src.utils import setup_logger

if __name__ == "__main__":
    setup_logger()

    db = None
    failed = False
    try:
        logging.info("🚀 Запуск основного пайплайна...")
        db = Database(os.getenv("DATABASE_URL"))

        logging.info("[STEP 1/2] Scraping hh...")
        try:
            run_scraper(db)
        except Exception as e:
            failed = True
            logging.critical(f"❌ Ошибка скрейпера: {e}", exc_info=True)

        # Публикация работает и при сбое скрейпера: уже собранные вакансии всё равно уйдут в канал.
        logging.info("[STEP 2/2] Publishing to Telegram...")
        try:
            run_publisher(db)
        except Exception as e:
            failed = True
            logging.critical(f"❌ Ошибка публикации: {e}", exc_info=True)

    except Exception as e:
        failed = True
        logging.critical(f"❌ Критическая ошибка инициализации: {e}", exc_info=True)
    finally:
        if db:
            db.close_all()

    if failed:
        sys.exit(1)
    logging.info("✅ Pipeline completed.")
