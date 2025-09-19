FROM python:3.9-slim

# Устанавливаем системные зависимости, необходимые для pandas
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . .

# Сначала устанавливаем numpy отдельно, так как pandas зависит от него
RUN pip install --no-cache-dir numpy==1.24.3

# Устанавливаем предварительно собранную версию pandas
RUN pip install --no-cache-dir pandas==2.0.3 --only-binary=:all:

# Затем устанавливаем остальные зависимости
RUN pip install --no-cache-dir -r requirements.txt

CMD ["python", "bot.py"]