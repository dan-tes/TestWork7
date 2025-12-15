## Установка зависимостей

```bash
uv sync
```


## Переменные окружения

Создайте файл `.env` в корне проекта:

```env
OPENAI_API_KEY=<токен для LLM использовался с https://developers.sber.ru/studio/workspaces/>
TELEGRAM_BOT_TOKEN=<телеграм токен, если нужен телеграм>
DB_PATH=<путь до директории проекта>
```

Создайте каталог для базы данных:

```bash
mkdir -p db
```

---

## Запуск Telegram-бота

```bash
uv run python -m app.bot
```

## Запуск LangGraph Dev


```bash
uv run langgraph dev
```

