# Деплой на Sber Cloud VPS

## Быстрый старт (Docker)

```bash
# 1. Клонировать репозиторий
git clone https://github.com/averagedigital/sebestoimost.git && cd sebestoimost

# 2. Запустить
docker compose up -d --build

# 3. Открыть
http://<server-ip>:8001
```

## Без Docker

```bash
# 1. Установить Python 3.11+
sudo apt update && sudo apt install python3.11 python3.11-venv

# 2. Создать venv
python3.11 -m venv venv
source venv/bin/activate

# 3. Установить зависимости
pip install -r requirements.txt

# 4. Запустить
uvicorn server:app --host 0.0.0.0 --port 8000
```

## Systemd (автозапуск)

```bash
sudo nano /etc/systemd/system/cost-calc.service
```

```ini
[Unit]
Description=Cost Calculator
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/рассчетсебестоимости
ExecStart=/home/ubuntu/рассчетсебестоимости/venv/bin/uvicorn server:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable cost-calc
sudo systemctl start cost-calc
```

## Nginx (опционально)

```nginx
server {
    listen 80;
    server_name calc.example.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## Обновление приложения

### Docker (рекомендуется)
```bash
# 1. Зайти на сервер
ssh user@your-server-ip

# 2. Перейти в папку
cd рассчетсебестоимости

# 3. Получить обновления
git pull origin main

# 4. Пересобрать и перезапустить
docker compose up -d --build
# ПРИМЕЧАНИЕ: Если команда docker compose (с пробелом) недоступна, используйте docker-compose (с дефисом)
```

### Устранение неполадок (Troubleshooting)

**Ошибка: `Traceback ... /usr/lib/python3/dist-packages/ur...` при запуске docker-compose**

Это проблема старой версии `docker-compose`, установленной через apt/python.
Решение: использовать новую команду `docker compose` (v2) или переустановить:

Вариант 1 (рекомендуемый): Попробуйте запустить с пробелом:
```bash
docker compose up -d --build
```

Вариант 2 (обновить старый docker-compose):
```bash
sudo curl -L "https://github.com/docker/compose/releases/download/v2.24.5/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

### Без Docker (Systemd)
```bash
cd рассчетсебестоимости
git pull origin main
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart cost-calc
```
