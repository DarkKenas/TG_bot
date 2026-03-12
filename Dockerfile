FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Устанавливаем зависимости по списку
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем весь проект
COPY . .

# Старт: сначала миграции, потом запуск бота
CMD ["sh", "-c", "alembic upgrade head && python aiogram_run.py"]

