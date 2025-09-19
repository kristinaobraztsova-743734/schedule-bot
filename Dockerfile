FROM python:3.9-slim

# Устанавливаем минимальные системные зависимости
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Сначала устанавливаем numpy отдельно (важно для pandas)
RUN pip install --no-cache-dir numpy==1.21.6

# Затем устанавливаем облегченную версию pandas
RUN pip install --no-cache-dir pandas==1.3.5 --no-build-isolation

# Копируем и устанавливаем остальные зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем основной код
COPY . .

CMD ["python", "bot.py"]