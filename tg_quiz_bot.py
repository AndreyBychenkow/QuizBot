import os
import json

import ssl
import random

import telebot
import redis

from telebot.types import ReplyKeyboardMarkup, KeyboardButton
from environs import Env

env = Env()
env.read_env()

context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
context.minimum_version = ssl.TLSVersion.TLSv1_2
context.check_hostname = False
context.verify_mode = ssl.CERT_NONE

redis_client = redis.Redis(
    host=env.str("REDIS_HOST"),
    port=env.int("REDIS_PORT"),
    password=env.str("REDIS_PASSWORD"),
    ssl=False,
    ssl_cert_reqs=ssl.CERT_NONE,
    decode_responses=True,
    socket_timeout=10
)

bot = telebot.TeleBot(env.str("TG_TOKEN"))
questions_dir = "quiz-questions"
quiz_dict = {}


def load_questions():
    """Загрузка вопросов из файлов."""
    questions = {}
    for filename in os.listdir(questions_dir):
        if filename.endswith(".txt"):
            file_path = os.path.join(questions_dir, filename)
            with open(file_path, "r", encoding="KOI8-R") as f:
                content = f.read()
                blocks = content.strip().split("\n\n")
                for i in range(len(blocks)):
                    if blocks[i].startswith("Вопрос"):
                        question = " ".join(
                            line.strip() for line in blocks[i].split("\n")[1:])
                        if i + 1 < len(blocks) and blocks[i + 1].startswith("Ответ"):
                            answer = " ".join(
                                line.strip() for line in blocks[i + 1].split("\n")[1:])
                            questions[question] = answer
    return questions


quiz_dict = load_questions()


def get_user_state(chat_id):
    state = redis_client.get(f"user:tg-{chat_id}")
    return json.loads(state) if state else {"current_question": None, "score": 0}


def save_user_state(chat_id, state):
    redis_client.set(f"user:tg-{chat_id}", json.dumps(state))


def create_keyboard():
    keyboard = ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    buttons = [
        KeyboardButton("Новый вопрос"),
        KeyboardButton("Сдаться"),
        KeyboardButton("Мой счёт"),
    ]
    keyboard.add(*buttons)
    return keyboard


@bot.message_handler(commands=["start"])
def start_command(message):
    chat_id = message.chat.id
    bot.send_message(chat_id, "Здравствуйте! Выберите действие:",
                     reply_markup=create_keyboard())


@bot.message_handler(func=lambda message: True)
def handle_message(message):
    chat_id = message.chat.id
    user = get_user_state(chat_id)
    text = message.text

    if text == "Новый вопрос":
        handle_new_question_request(chat_id, user)
    elif text == "Сдаться":
        handle_solution_attempt(chat_id, user)
    elif text == "Мой счёт":
        bot.send_message(chat_id, f"🏆 Текущий счёт: {user['score']}")
    else:
        handle_answer(chat_id, user, text)


def handle_new_question_request(chat_id, user):
    question, answer = random.choice(list(quiz_dict.items()))
    user["current_question"] = {"question": question, "answer": answer}
    save_user_state(chat_id, user)
    bot.send_message(chat_id, f"❓ Вопрос:\n{question}")


def handle_solution_attempt(chat_id, user):
    if user["current_question"]:
        answer = user["current_question"]["answer"]
        bot.send_message(chat_id, f"🏁 Правильный ответ:\n{answer}")
        handle_new_question_request(chat_id, user)
    else:
        bot.send_message(chat_id, "⚠️ Сначала получите новый вопрос!")


def handle_answer(chat_id, user, text):
    if user.get("current_question"):
        correct_answer = user["current_question"]["answer"].lower()
        user_answer = text.strip().lower()

        if user_answer == correct_answer:
            user["score"] += 1
            response = "✅ Правильно! Поздравляю! Для следующего вопроса нажми «Новый вопрос»."
            user["current_question"] = None
        else:
            response = "❌ Неправильно. Попробуйте ещё раз или нажмите 'Сдаться'."
        save_user_state(chat_id, user)
        bot.send_message(chat_id, response)


if __name__ == "__main__":
    print("Бот запущен!")
    bot.polling()
