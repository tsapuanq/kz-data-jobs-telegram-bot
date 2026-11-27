#  **HH → Telegram Vacancy Bot**

Автоматический конвейер, который собирает **Data-вакансии с HH.kz**, фильтрует их с помощью **AI (OpenAI GPT)** и публикует в **Telegram**.  
Все работает полностью автономно.

**Канал:** [@KZDataJobs](https://t.me/KZDataJobs)

---

## Что делает бот

1. **Собирает** вакансии по ролям Data Scientist / Analyst / Engineer и др.  
2. **Фильтрует** нерелевантные: сначала словарный фильтр, затем GPT.  
3. **Создает саммари** (о компании, обязанностях, требованиях).  
4. **Сохраняет** в PostgreSQL (Supabase).  
5. **Публикует** в Telegram автоматически.

---

## Технологии

| Задача | Технология |
|--------|-------------|
| Скрейпинг | requests (встроенный JSON страниц hh) |
| AI-анализ | OpenAI (gpt-4.1-mini) |
| Чтение Telegram | Telethon |
| База данных | Supabase (PostgreSQL) |
| Telegram | python-telegram-bot |
| CI/CD | GitHub Actions |
| Язык | Python |

---

## Алгоритм работы

**HH.kz Scraper → AI фильтрация → AI саммари → Supabase DB → Telegram Publisher**

Как собираются вакансии hh:

- Страницы hh содержат встроенный JSON (`<template id="HH-Lux-InitialState">`) со всеми
  полями вакансии: город, зарплата, опыт, формат, график, навыки, дата. Парсер читает его,
  а не CSS-разметку, поэтому браузер не нужен. Если JSON на странице нет (капча, блокировка,
  смена вёрстки), запуск падает с ошибкой, а не тихо пропускает вакансии.
- Поиск идёт по профессиональным ролям hh (`HH_PROFESSIONAL_ROLES` в `src/config.py`) и по
  названию вакансии (`HH_TITLE_QUERIES`): Data/ML-инженеры часто размечены ролью
  «Программист» или «Другое». Читаются все страницы выдачи за последние `HH_LOOKBACK_DAYS` дней.
- Уже сохранённые вакансии (по id из URL) повторно не скачиваются. Строки в `vacancies`
  не удаляются: они нужны для дедупликации и аналитики.

Дополнительный источник:

**Telegram source channel → GPT фильтрация → Supabase DB (`telegram_posts`) → Telegram Publisher**

---

## Автоматизация

GitHub Actions запускает пайплайн 3 раза в день:

1. `python run_all.py` — основной HH-пайплайн.
2. `python run_telegram.py` — Telegram source pipeline.

Для Telegram source pipeline нужны secrets:

```text
TELEGRAM_API_ID
TELEGRAM_API_HASH
TELEGRAM_SOURCE_CHANNEL
TELEGRAM_SESSION_STRING
```

`TELEGRAM_SESSION_STRING` создаётся локально:

```bash
python scripts/export_telegram_session.py
```

Для безопасной проверки БД без публикации:

```bash
python run_telegram.py --no-publish
```

Настройки по умолчанию:

```text
TELEGRAM_LOOKBACK_DAYS=2
TELEGRAM_SOURCE_LIMIT=50
TELEGRAM_PROCESS_LIMIT=20
OPENAI_VISION_MODEL=gpt-4.1-mini
TELEGRAM_PHOTO_OCR_ENABLED=true
TELEGRAM_PHOTO_OCR_WITH_CAPTION=true
TELEGRAM_PHOTO_OCR_LIMIT_PER_RUN=20
TELEGRAM_PHOTO_OCR_DETAIL=high
HH_LOOKBACK_DAYS=2
```

Пайплайн читает посты за последние 2 дня, но повторно не отправляет уже
обработанные `source_url`: дедупликация хранится в PostgreSQL. Один пост обычно
стоит примерно 1.2k-2k input tokens и 200-500 output tokens; лимит 20 новых
постов даёт ориентир около 25k-40k input tokens за худший запуск. Ссылка на
исходный Telegram-канал используется только внутри БД для дедупликации и не
публикуется в итоговом сообщении.

Что попадает в `raw_text` поста:

- текст поста;
- `[Текст с изображения]` — OCR через OpenAI vision для фото и картинок, отправленных файлом;
- `[Превью ссылки]` — адрес, название и описание превью ссылки (например, пост LinkedIn).
  Картинка превью распознаётся, только если текста в посте и превью меньше 300 символов,
  иначе это обычно логотип.

OCR делается только для новых постов: уже сохранённые в `telegram_posts` не скачиваются
повторно. `TELEGRAM_PHOTO_OCR_LIMIT_PER_RUN` ограничивает число OCR-запросов за запуск.
Если GPT трижды вернул пустой или невалидный ответ, пост больше не обрабатывается
(`gpt_attempts`).

---

## Результат

✅ Только релевантные вакансии  
✅ Полностью автономный процесс  
✅ Удобные AI-описания  
✅ Хранение данных для аналитики

---

## Автор

**Sapsan Talaspay**  
📍 Data Science @ SDU  
📢 [@KZDataJobs](https://t.me/KZDataJobs) | 💬 [@tsapuanq](https://t.me/tsapuanq)
