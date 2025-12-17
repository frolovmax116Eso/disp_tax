# DEPLOYMENT
# Развертывание системы

Этот документ описывает процесс развертывания Telegram Dispatcher Platform в production.

---

## Требования

### Системные требования

- **Python:** 3.10 или выше
- **ОС:** Linux (Ubuntu 20.04+), Windows Server, или Docker
- **RAM:** Минимум 512 MB, рекомендуется 1 GB+
- **Диск:** Минимум 1 GB свободного места
- **Сеть:** Стабильное интернет-соединение

### Зависимости

Все зависимости указаны в `requirements.txt`:
- aiogram 3.x
- telethon 0.30+
- sqlalchemy 2.0+
- и другие (см. requirements.txt)

---

## Подготовка

### 1. Получение API ключей

#### Telegram Bot Token
1. Создайте бота через [@BotFather](https://t.me/BotFather)
2. Получите токен вида: `1234567890:ABCdefGHIjklMNOpqrsTUVwxyz`
3. Сохраните токен

#### Telegram API ID и Hash (для Telethon)
1. Перейдите на https://my.telegram.org
2. Войдите с номером телефона
3. Перейдите в "API development tools"
4. Создайте приложение
5. Получите `api_id` и `api_hash`
6. Сохраните оба значения

### 2. Настройка окружения

Создайте файл `.env`:

```bash
# Bot
BOT_TOKEN=your_bot_token_here

# Telegram API
API_ID=your_api_id
API_HASH=your_api_hash

# Database
DATABASE_URL=sqlite:///./dispatcher.db
# Для PostgreSQL:
# DATABASE_URL=postgresql+asyncpg://user:password@localhost/dispatcher

# Admin IDs (через запятую)
ADMIN_IDS=123456789,987654321

# Sessions
SESSIONS_DIR=./sessions

# Logging
LOG_LEVEL=INFO
LOG_FILE=./logs/dispatcher.log
```

---

## Установка

### Вариант 1: Прямая установка

#### Linux

```bash
# 1. Клонирование репозитория
git clone <repository_url>
cd disp-tax

# 2. Создание виртуального окружения
python3 -m venv venv
source venv/bin/activate

# 3. Установка зависимостей
pip install -r requirements.txt

# 4. Настройка .env
cp .env.example .env
nano .env  # Заполните все поля

# 5. Инициализация БД
alembic upgrade head

# 6. Создание директорий
mkdir -p sessions logs

# 7. Запуск
python main.py
```

#### Windows

```powershell
# 1. Клонирование
git clone <repository_url>
cd disp-tax

# 2. Создание виртуального окружения
python -m venv venv
venv\Scripts\activate

# 3. Установка зависимостей
pip install -r requirements.txt

# 4. Настройка .env
copy .env.example .env
# Отредактируйте .env в текстовом редакторе

# 5. Инициализация БД
alembic upgrade head

# 6. Создание директорий
mkdir sessions
mkdir logs

# 7. Запуск
python main.py
```

---

### Вариант 2: Docker

#### Dockerfile

```dockerfile
FROM python:3.10-slim

WORKDIR /app

# Установка зависимостей
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копирование кода
COPY . .

# Создание директорий
RUN mkdir -p sessions logs

# Запуск
CMD ["python", "main.py"]
```

#### docker-compose.yml

```yaml
version: '3.8'

services:
  dispatcher:
    build: .
    container_name: telegram_dispatcher
    restart: unless-stopped
    env_file:
      - .env
    volumes:
      - ./sessions:/app/sessions
      - ./logs:/app/logs
      - ./dispatcher.db:/app/dispatcher.db
    networks:
      - dispatcher_net

networks:
  dispatcher_net:
    driver: bridge
```

#### Запуск

```bash
# Сборка и запуск
docker-compose up -d

# Просмотр логов
docker-compose logs -f

# Остановка
docker-compose down
```

---

## База данных

### SQLite (Development)

По умолчанию используется SQLite. Файл БД создается автоматически.

**Преимущества:**
- Простота
- Не требует настройки
- Подходит для небольших проектов

**Недостатки:**
- Ограниченная производительность
- Не подходит для production с высокой нагрузкой

### PostgreSQL (Production)

Для production рекомендуется PostgreSQL.

#### Установка PostgreSQL

```bash
# Ubuntu
sudo apt update
sudo apt install postgresql postgresql-contrib

# Создание БД
sudo -u postgres psql
CREATE DATABASE dispatcher;
CREATE USER dispatcher_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE dispatcher TO dispatcher_user;
\q
```

#### Настройка

```bash
# .env
DATABASE_URL=postgresql+asyncpg://dispatcher_user:your_password@localhost/dispatcher
```

#### Миграции

```bash
alembic upgrade head
```

---

## Миграции БД

### Создание миграции

```bash
alembic revision --autogenerate -m "description"
```

### Применение миграций

```bash
# Применить все миграции
alembic upgrade head

# Откатить последнюю миграцию
alembic downgrade -1

# Просмотр текущей версии
alembic current
```

---

## Запуск как сервис

### Systemd (Linux)

Создайте файл `/etc/systemd/system/telegram-dispatcher.service`:

```ini
[Unit]
Description=Telegram Dispatcher Platform
After=network.target

[Service]
Type=simple
User=your_user
WorkingDirectory=/path/to/disp-tax
Environment="PATH=/path/to/disp-tax/venv/bin"
ExecStart=/path/to/disp-tax/venv/bin/python /path/to/disp-tax/main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Активация:

```bash
sudo systemctl daemon-reload
sudo systemctl enable telegram-dispatcher
sudo systemctl start telegram-dispatcher

# Просмотр статуса
sudo systemctl status telegram-dispatcher

# Просмотр логов
sudo journalctl -u telegram-dispatcher -f
```

---

## Мониторинг

### Логи

Логи сохраняются в `logs/dispatcher.log`:

```bash
# Просмотр логов
tail -f logs/dispatcher.log

# Поиск ошибок
grep ERROR logs/dispatcher.log

# Последние 100 строк
tail -n 100 logs/dispatcher.log
```

### Health Check

Создайте endpoint для проверки здоровья (опционально):

```python
# health.py
from aiohttp import web

async def health_check(request):
    return web.json_response({"status": "ok"})

app = web.Application()
app.router.add_get('/health', health_check)
```

---

## Безопасность

### Защита .env файла

```bash
# Установка прав
chmod 600 .env

# Исключение из git
echo ".env" >> .gitignore
```

### Защита сессий

```bash
# Права на директорию sessions
chmod 700 sessions
```

### Firewall

Откройте только необходимые порты (если используете веб-сервер).

---

## Резервное копирование

### База данных

#### SQLite

```bash
# Простое копирование файла
cp dispatcher.db backups/dispatcher_$(date +%Y%m%d).db
```

#### PostgreSQL

```bash
# Дамп БД
pg_dump -U dispatcher_user dispatcher > backups/dispatcher_$(date +%Y%m%d).sql

# Восстановление
psql -U dispatcher_user dispatcher < backups/dispatcher_20240115.sql
```

### Сессии

```bash
# Копирование директории sessions
tar -czf backups/sessions_$(date +%Y%m%d).tar.gz sessions/
```

### Автоматическое резервное копирование

Создайте скрипт `backup.sh`:

```bash
#!/bin/bash
BACKUP_DIR="/path/to/backups"
DATE=$(date +%Y%m%d_%H%M%S)

# Создание директории
mkdir -p $BACKUP_DIR

# Бэкап БД
cp dispatcher.db $BACKUP_DIR/dispatcher_$DATE.db

# Бэкап сессий
tar -czf $BACKUP_DIR/sessions_$DATE.tar.gz sessions/

# Удаление старых бэкапов (старше 7 дней)
find $BACKUP_DIR -type f -mtime +7 -delete

echo "Backup completed: $DATE"
```

Добавьте в crontab:

```bash
# Ежедневный бэкап в 3:00
0 3 * * * /path/to/backup.sh
```

---

## Обновление

### Процесс обновления

```bash
# 1. Остановка сервиса
sudo systemctl stop telegram-dispatcher

# 2. Бэкап
./backup.sh

# 3. Обновление кода
git pull origin main

# 4. Обновление зависимостей
source venv/bin/activate
pip install -r requirements.txt

# 5. Применение миграций
alembic upgrade head

# 6. Запуск
sudo systemctl start telegram-dispatcher
```

---

## Troubleshooting

### Проблемы с авторизацией

**Ошибка:** "API ID/Hash invalid"
- Проверьте правильность API_ID и API_HASH в .env
- Убедитесь, что нет лишних пробелов

**Ошибка:** "Session expired"
- Удалите файл сессии в `sessions/`
- Переавторизуйтесь через бота

### Проблемы с БД

**Ошибка:** "Database locked" (SQLite)
- Проверьте, что нет других процессов, использующих БД
- Перезапустите приложение

**Ошибка:** "Connection refused" (PostgreSQL)
- Проверьте, что PostgreSQL запущен
- Проверьте настройки подключения в .env

### Проблемы с отправкой

**Ошибка:** "FloodWait"
- Это нормально, система обработает автоматически
- Увеличьте задержки в сценариях

**Ошибка:** "Message too long"
- Проверьте длину текста заказа
- Telegram ограничивает сообщения до 4096 символов

---

## Production Checklist

- [ ] Настроен .env файл
- [ ] Установлены все зависимости
- [ ] Инициализирована БД
- [ ] Применены миграции
- [ ] Созданы директории (sessions, logs)
- [ ] Настроен systemd сервис (Linux)
- [ ] Настроено резервное копирование
- [ ] Проверена работа бота
- [ ] Проверена авторизация диспетчеров
- [ ] Настроен мониторинг логов
- [ ] Добавлены админы в ADMIN_IDS

---

## Заключение

Система готова к развертыванию после выполнения всех шагов. Рекомендуется:
- Использовать PostgreSQL для production
- Настроить автоматическое резервное копирование
- Мониторить логи регулярно
- Обновлять систему по мере необходимости

