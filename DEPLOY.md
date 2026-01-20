# Деплой на Sber Cloud VPS

## Быстрый старт (Docker)

```bash
# 1. Клонировать репозиторий
git clone <repo-url> && cd рассчетсебестоимости

# 2. Запустить
docker-compose up -d --build

# 3. Открыть
http://<server-ip>:8000
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
