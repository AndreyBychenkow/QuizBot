import os
import json

import ssl
import random

import logging
import redis

import vk_api
from vk_api.keyboard import VkKeyboard, VkKeyboardColor
from vk_api.longpoll import VkEventType, VkLongPoll

from vk_api.utils import get_random_id
from environs import Env

env = Env()
env.read_env()

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

questions_dir = "quiz-questions"

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

vk_session = vk_api.VkApi(token=env.str("VK_TOKEN"))
longpoll = VkLongPoll(vk_session)
vk = vk_session.get_api()
admin_id = env.int("ADMIN_ID")


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


def create_keyboard():
    keyboard = VkKeyboard(one_time=False)
    keyboard.add_button("Новый вопрос", color=VkKeyboardColor.PRIMARY)
    keyboard.add_button("Сдаться", color=VkKeyboardColor.NEGATIVE)
    keyboard.add_line()
    keyboard.add_button("Мой счёт", color=VkKeyboardColor.SECONDARY)
    return keyboard.get_keyboard()


def get_user_state(user_id):
    state = redis_client.get(f"user:vk-{user_id}")
    return json.loads(state) if state else {"current_question": None, "score": 0}


def save_user_state(user_id, state):
    redis_client.set(f"user:vk-{user_id}", json.dumps(state))


def send_message(user_id, message):
    try:
        vk.messages.send(
            user_id=user_id,
            message=message,
            keyboard=create_keyboard(),
            random_id=get_random_id(),
        )
        logger.info(f"Sent message to {user_id}")
    except vk_api.exceptions.ApiError as e:
        logger.error(f"VK API Error: {e}")


def handle_new_question(user_id):
    user = get_user_state(user_id)
    question, answer = random.choice(list(quiz_dict.items()))
    user["current_question"] = {"question": question, "answer": answer}
    save_user_state(user_id, user)
    send_message(user_id, f"❓ Вопрос:\n{question}")


def handle_give_up(user_id):
    user = get_user_state(user_id)
    if not user["current_question"]:
        send_message(user_id, "⚠️ Сначала получите новый вопрос!")
        return
    answer = user["current_question"]["answer"]
    send_message(user_id, f"🏁 Правильный ответ:\n{answer}")
    handle_new_question(user_id)


def handle_score(user_id):
    user = get_user_state(user_id)
    send_message(user_id, f"🏆 Текущий счёт: {user['score']}")


def handle_answer(user_id, text):
    user = get_user_state(user_id)
    if not user.get("current_question"):
        return
    correct = user["current_question"]["answer"].lower()
    user_answer = text.strip().lower()

    if user_answer == correct:
        user["score"] += 1
        response = "✅ Правильно! Для следующего вопроса нажми «Новый вопрос»."
        user["current_question"] = None
    else:
        response = "❌ Неправильно. Попробуйте ещё раз или нажмите 'Сдаться'."
    save_user_state(user_id, user)
    send_message(user_id, response)


def main():
    send_message(admin_id, "🟢 Бот успешно запущен!")
    logger.info("Бот запущен")

    for event in longpoll.listen():
        if event.type == VkEventType.MESSAGE_NEW and event.to_me:
            user_id = event.user_id
            text = event.text
            logger.info(f"Получено сообщение от {user_id}: {text}")

            if text == "Новый вопрос":
                handle_new_question(user_id)
            elif text == "Сдаться":
                handle_give_up(user_id)
            elif text == "Мой счёт":
                handle_score(user_id)
            else:
                handle_answer(user_id, text)


if __name__ == "__main__":
    main()
