# Используем официальный образ Python 3.11
FROM python:3.11
LABEL authors="chulkov-alex"

# Установка зависимостей
COPY requirements.txt /app/requirements.txt
WORKDIR /app
RUN pip install -r requirements.txt

# Копирование кода и файлов
COPY pics /app/pics
COPY texts /app/texts
COPY main.py /app/main.py

# Запуск бота
CMD ["python", "main.py"]