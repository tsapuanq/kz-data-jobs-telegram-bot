# config.py
from dotenv import load_dotenv
import os

load_dotenv()

HH_BASE_URL = "https://hh.kz"
HH_AREA_ID = 40  # Казахстан

# Профессиональные роли hh (справочник professionalRoleTree на странице поиска):
# 165 Дата-сайентист, 156 BI-аналитик/аналитик данных, 160 DevOps-инженер,
# 148 Системный аналитик, 164 Продуктовый аналитик, 150 Бизнес-аналитик,
# 157 Руководитель отдела аналитики, 10 Аналитик.
HH_PROFESSIONAL_ROLES = [165, 156, 160, 148, 164, 150, 157, 10]

# Поиск только по названию вакансии: Data/ML-инженеры часто размечены ролью
# «Программист» или «Другое», поэтому одних ролей недостаточно.
HH_TITLE_QUERIES = [
    '"data engineer" OR "инженер данных" OR "дата инженер" OR "data scientist" OR "data science" '
    'OR "data analyst" OR "аналитик данных" OR "data architect" OR "analytics engineer" '
    'OR "big data" OR DWH OR ETL',
    'ML OR MLOps OR "machine learning" OR "машинного обучения" OR LLM OR NLP '
    'OR "computer vision" OR "deep learning" OR "AI engineer" OR "AI инженер"',
    '"BI analyst" OR "BI аналитик" OR "BI-аналитик" OR "BI developer" OR "BI-разработчик" OR "Power BI"',
    "DevOps OR SRE",
]

HH_LOOKBACK_DAYS = int(os.getenv("HH_LOOKBACK_DAYS", "2"))
HH_MAX_PAGES_PER_QUERY = 20
HH_REQUEST_TIMEOUT = 30
HH_REQUEST_DELAY_SECONDS = (0.7, 1.5)
HH_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)
LOCAL_TIMEZONE = "Asia/Almaty"

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME")
TELEGRAM_API_ID = os.getenv("TELEGRAM_API_ID")
TELEGRAM_API_HASH = os.getenv("TELEGRAM_API_HASH")
TELEGRAM_SOURCE_CHANNEL = os.getenv("TELEGRAM_SOURCE_CHANNEL")
TELEGRAM_SESSION_STRING = os.getenv("TELEGRAM_SESSION_STRING")
TELEGRAM_SESSION_FILE = os.getenv("TELEGRAM_SESSION_FILE")
TELEGRAM_LOOKBACK_DAYS = int(os.getenv("TELEGRAM_LOOKBACK_DAYS", "2"))
TELEGRAM_SOURCE_LIMIT = int(os.getenv("TELEGRAM_SOURCE_LIMIT", "50"))
TELEGRAM_PROCESS_LIMIT = int(os.getenv("TELEGRAM_PROCESS_LIMIT", "20"))
TELEGRAM_PHOTO_OCR_ENABLED = os.getenv("TELEGRAM_PHOTO_OCR_ENABLED", "true").lower() in {"1", "true", "yes", "on"}
TELEGRAM_PHOTO_OCR_WITH_CAPTION = os.getenv("TELEGRAM_PHOTO_OCR_WITH_CAPTION", "true").lower() in {"1", "true", "yes", "on"}
TELEGRAM_PHOTO_OCR_LIMIT_PER_RUN = int(os.getenv("TELEGRAM_PHOTO_OCR_LIMIT_PER_RUN", "20"))
TELEGRAM_PHOTO_OCR_MAX_BYTES = int(os.getenv("TELEGRAM_PHOTO_OCR_MAX_BYTES", str(20 * 1024 * 1024)))
TELEGRAM_PHOTO_OCR_DETAIL = os.getenv("TELEGRAM_PHOTO_OCR_DETAIL", "high")
TELEGRAM_GPT_MAX_ATTEMPTS = 3

DATABASE_URL = os.getenv("DATABASE_URL")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_API_URL = os.getenv("OPENAI_API_URL", "https://api.openai.com/v1/responses")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
OPENAI_VISION_MODEL = os.getenv("OPENAI_VISION_MODEL", OPENAI_MODEL)
OPENAI_HEADERS = {"Content-Type": "application/json"}

TELEGRAM_DELAY_SECONDS = 5 
TELEGRAM_MAX_DELAY_SECONDS = 10  

LLM_API_RETRIES = 3  
LLM_API_DELAY = 2.0  
LLM_API_TIMEOUT = 30  

LLM_API_MIN_INTERVAL = 1.0
LLM_API_MAX_PER_MIN = 50
LLM_API_BACKOFF_BASE = 2.0
LLM_API_BACKOFF_CAP = 30.0

OTHER_LABEL = "Other"

DESCRIPTION_PROMPT_MAX_CHARS = 4000
NORMALIZE_BATCH_LIMIT = 2000
