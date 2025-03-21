import random
import json

import redis
import telebot
import ssl

from environs import Env
from quiz_bot_utils import load_questions, create_keyboard


def register_handlers(bot, redis_client, quiz_dict):
    @bot.message_handler(commands=["start"])
    def start_command(message):
        chat_id = message.chat.id
        bot.send_message(
            chat_id,
            "Здравствуйте! Выберите действие:",
            reply_markup=create_keyboard("tg"),
        )

    @bot.message_handler(func=lambda message: True)
    def handle_message(message):
        chat_id = message.chat.id
        state = redis_client.get(f"user:tg-{chat_id}")
        user = json.loads(state) if state else {"current_question": None, "score": 0}
        text = message.text

        if text == "Новый вопрос":
            handle_new_question_request(chat_id, user, bot, redis_client, quiz_dict)
        elif text == "Сдаться":
            handle_give_up(chat_id, user, bot, redis_client, quiz_dict)
        elif text == "Мой счёт":
            bot.send_message(chat_id, f"🏆 Текущий счёт: {user['score']}")
        else:
            handle_answer(chat_id, user, text, bot, redis_client)

    return bot


def handle_new_question_request(chat_id, user, bot, redis_client, quiz_dict):
    question, answer = random.choice(list(quiz_dict.items()))
    user["current_question"] = {"question": question, "answer": answer}
    redis_client.set(f"user:tg-{chat_id}", json.dumps(user))
    bot.send_message(chat_id, f"❓ Вопрос:\n{question}")


def handle_give_up(chat_id, user, bot, redis_client, quiz_dict):
    if user["current_question"]:
        answer = user["current_question"]["answer"]
        bot.send_message(chat_id, f"🏁 Правильный ответ:\n{answer}")
        handle_new_question_request(chat_id, user, bot, redis_client, quiz_dict)
    else:
        bot.send_message(chat_id, "⚠️ Сначала получите новый вопрос!")


def handle_answer(chat_id, user, text, bot, redis_client):
    if user.get("current_question"):
        correct_answer = user["current_question"]["answer"].lower()
        user_answer = text.strip().lower()

        if user_answer == correct_answer:
            user["score"] += 1
            response = "✅ Правильно! Для следующего вопроса нажми «Новый вопрос»."
            user["current_question"] = None
        else:
            response = "❌ Неправильно. Попробуйте ещё раз или нажмите 'Сдаться'."
        redis_client.set(f"user:tg-{chat_id}", json.dumps(user))
        bot.send_message(chat_id, response)


def main():
    env = Env()
    env.read_env()

    redis_client = redis.Redis(
        host=env.str("REDIS_HOST"),
        port=env.int("REDIS_PORT"),
        password=env.str("REDIS_PASSWORD"),
        ssl=False,
        ssl_cert_reqs=ssl.CERT_NONE,
        decode_responses=True,
        socket_timeout=10,
    )

    bot = telebot.TeleBot(env.str("TG_TOKEN"))
    quiz_dict = load_questions("quiz-questions")

    bot = register_handlers(bot, redis_client, quiz_dict)

    print("Бот запущен!")
    bot.polling()


if __name__ == "__main__":
    main()

