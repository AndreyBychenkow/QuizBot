# 🐍 Проект «QuizBot - Бот-викторина»

## 📌 Описание проекта

Чат-боты для проведения викторин в Telegram и VK с использованием Redis. Боты присылают вопрос и проверяют ваш ответ.

[Пример VK-бота](https://vk.com/club229680400)

[Пример TG-бота](https://web.telegram.org/k/#@my_quiz_rus_bot)


## 📌 Установка и настройка

### 🔧 Предварительные требования:

- Python 3.10 или выше
- СУБД по вашему выбору
- Виртуальное окружение (рекомендуется)

1. 📌 **Клонируйте репозиторий:**
   ```bash
   git clone https://github.com/AndreyBychenkow/QuizBot
   ```
   
2. 📌 **Установите зависимости:**
   ```bash
   pip install -r requirements.txt   
   ```
   
3. 📌 **Настройка переменных окружения:**

**Создайте файл .env в корне проекта и добавьте необходимые переменные окружения:**

```bash
# Для Telegram бота:
TG_TOKEN='ваш telegram_bot_token'

# Для VK бота:
VK_TOKEN="ваш_токен_вк"
ADMIN_ID="ваш ID вк"

# Для Redis
REDIS_HOST="адрес_redis"
REDIS_PORT="порт_redis"
REDIS_PASSWORD="ваш пароль_redis"
```

## 🚀 Запуск ботов

### 🖋 Запуск Telegram-бота
```bash
   python tg_quiz_bot.py   
   ```
   
### 🖋 Запуск VK-бота
```bash
   python vk_quiz_bot.py   
   ```

## 📌 Примеры работы:


### 🚀 Пример работы Телеграм бота:

![tg-video](https://github.com/user-attachments/assets/55972f23-7b8a-4a84-9c28-ff7c01632776)


### 🚀 Пример работы VK бота:

![ВК_видео](https://i.postimg.cc/bv3ZyhxN/vk-video.gif)


## ✅ Цели проекта

Код написан в учебных целях — это урок в курсе по Python и веб-разработке на сайте [Devman](https://dvmn.org).
