import os
import json

import random
import telebot
import redis

from telebot.types import ReplyKeyboardMarkup, KeyboardButton
from environs import Env

env = Env()
env.read_env()

redis_client = redis.Redis(
    host=env.str("REDIS_HOST"),
    port=env.int("REDIS_PORT"),
    password=env.str("REDIS_PASSWORD"),
    ssl=False,
    decode_responses=True,
)

bot = telebot.TeleBot(env.str("TG_TOKEN"))
questions_dir = "quiz-questions"
quiz_dict = {}


def parse_questions(file_content):
    blocks = file_content.strip().split("\n\n")
    questions = {}
    for i in range(len(blocks)):
        if blocks[i].startswith("Вопрос"):
            question_lines = blocks[i].split("\n")[1:]
            question = " ".join(line.strip() for line in question_lines)
            if i + 1 < len(blocks) and blocks[i + 1].startswith("Ответ"):
                answer_lines = blocks[i + 1].split("\n")[1:]
                answer = " ".join(line.strip() for line in answer_lines)
                questions[question] = answer
    return questions


for filename in os.listdir(questions_dir):
    if filename.endswith(".txt"):
        file_path = os.path.join(questions_dir, filename)
        with open(file_path, "r", encoding="KOI8-R") as f:
            quiz_dict.update(parse_questions(f.read()))


def get_user_state(chat_id):
    state = redis_client.get(f"user:{chat_id}")
    return json.loads(state) if state else {"current_question": None, "score": 0}


def save_user_state(chat_id, state):
    redis_client.set(f"user:{chat_id}", json.dumps(state))


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
    bot.send_message(
        chat_id, "Здравствуйте! Выберите действие:", reply_markup=create_keyboard()
    )


@bot.message_handler(func=lambda message: True)
def handle_message(message):
    chat_id = message.chat.id
    user = get_user_state(chat_id)
    text = message.text

    if text == "Новый вопрос":
        return handle_new_question_request(message)
    elif text == "Сдаться":
        return handle_solution_attempt(message)
    elif text == "Мой счёт":
        bot.send_message(chat_id, f"🏆 Текущий счёт: {user['score']}")
    else:
        return handle_answer(message)


def handle_new_question_request(message):
    chat_id = message.chat.id
    user = get_user_state(chat_id)
    question, answer = random.choice(list(quiz_dict.items()))
    user["current_question"] = {"question": question, "answer": answer}
    save_user_state(chat_id, user)
    bot.send_message(chat_id, f"❓ Вопрос:\n{question}")


def handle_solution_attempt(message):
    chat_id = message.chat.id
    user = get_user_state(chat_id)

    if user["current_question"]:
        answer = user["current_question"]["answer"]
        bot.send_message(chat_id, f"🏁 Правильный ответ:\n{answer}")

        question, answer = random.choice(list(quiz_dict.items()))
        user["current_question"] = {"question": question, "answer": answer}
        save_user_state(chat_id, user)
        bot.send_message(chat_id, f"❓ Новый вопрос:\n{question}")
    else:
        bot.send_message(chat_id, "⚠️ Сначала получите новый вопрос!")


def handle_answer(message):
    chat_id = message.chat.id
    user = get_user_state(chat_id)

    if user.get("current_question"):
        correct_answer = user["current_question"]["answer"].lower()
        user_answer = message.text.strip().lower()

        if user_answer == correct_answer:
            user["score"] += 1
            response = (
                "✅ Правильно! Поздравляю! Для следующего вопроса нажми «Новый вопрос»."
            )
            user["current_question"] = None
        else:
            response = "❌ Неправильно. Попробуйте ещё раз или нажмите 'Сдаться'."
        bot.send_message(chat_id, response)
        save_user_state(chat_id, user)


if __name__ == "__main__":
    print("Бот запущен!")
    bot.polling()
