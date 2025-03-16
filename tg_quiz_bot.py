import random
import telebot

from environs import Env
from quiz_bot_utils import (
    load_questions,
    get_user_state,
    save_user_state,
    create_keyboard,
    create_redis_client,
    create_ssl_context,
)

env = Env()
env.read_env()

context = create_ssl_context()

redis_client = create_redis_client(env)

bot = telebot.TeleBot(env.str("TG_TOKEN"))
questions_dir = "quiz-questions"
quiz_dict = load_questions(questions_dir)


@bot.message_handler(commands=["start"])
def start_command(message):
    chat_id = message.chat.id
    bot.send_message(
        chat_id, "Здравствуйте! Выберите действие:", reply_markup=create_keyboard("tg")
    )


@bot.message_handler(func=lambda message: True)
def handle_message(message):
    chat_id = message.chat.id
    user = get_user_state(redis_client, chat_id, "tg")
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
    save_user_state(redis_client, chat_id, user, "tg")
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
            response = (
                "✅ Правильно! Поздравляю! Для следующего вопроса нажми «Новый вопрос»."
            )
            user["current_question"] = None
        else:
            response = "❌ Неправильно. Попробуйте ещё раз или нажмите 'Сдаться'."
        save_user_state(redis_client, chat_id, user, "tg")
        bot.send_message(chat_id, response)


if __name__ == "__main__":
    print("Бот запущен!")
    bot.polling()
