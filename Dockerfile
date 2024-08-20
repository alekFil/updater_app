# Используем официальный образ Python
FROM python:3.12-slim

# Устанавливаем рабочую директорию внутри контейнера
WORKDIR /app

# Устанавливаем зависимости
COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /resources

# Указываем команду для запуска приложения
ENTRYPOINT ["python", "-m", "updater_app.app"]
