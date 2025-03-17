import random
import json

import logging
import redis

import vk_api
import ssl

from vk_api.longpoll import VkEventType, VkLongPoll
from vk_api.utils import get_random_id

from environs import Env
from quiz_bot_utils import load_questions, create_keyboard

logger = logging.getLogger(__name__)


def send_message(vk_api_client, user_id, message):
    try:
        vk_api_client.messages.send(
            user_id=user_id,
            message=message,
            keyboard=create_keyboard("vk"),
            random_id=get_random_id(),
        )
        logger.info(f"Sent message to {user_id}")
    except vk_api.exceptions.ApiError as e:
        logger.error(f"VK API Error: {e}")


def handle_new_question(redis_client, quiz_dict, vk_api, user_id):
    state = redis_client.get(f"user:vk-{user_id}")
    user = json.loads(state) if state else {"current_question": None, "score": 0}
    question, answer = random.choice(list(quiz_dict.items()))
    user["current_question"] = {"question": question, "answer": answer}
    redis_client.set(f"user:vk-{user_id}", json.dumps(user))
    send_message(vk_api, user_id, f"❓ Вопрос:\n{question}")


def handle_give_up(redis_client, quiz_dict, vk_api, user_id):
    state = redis_client.get(f"user:vk-{user_id}")
    user = json.loads(state) if state else {"current_question": None, "score": 0}

    if not user["current_question"]:
        send_message(vk_api, user_id, "⚠️ Сначала получите новый вопрос!")
        return
    answer = user["current_question"]["answer"]
    send_message(vk_api, user_id, f"🏁 Правильный ответ:\n{answer}")
    handle_new_question(redis_client, quiz_dict, vk_api, user_id)


def handle_score(redis_client, vk_api, user_id):
    state = redis_client.get(f"user:vk-{user_id}")
    user = json.loads(state) if state else {"current_question": None, "score": 0}
    send_message(vk_api, user_id, f"🏆 Текущий счёт: {user['score']}")


def handle_answer(redis_client, vk_api, user_id, text):
    state = redis_client.get(f"user:vk-{user_id}")
    user = json.loads(state) if state else {"current_question": None, "score": 0}

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
    redis_client.set(f"user:vk-{user_id}", json.dumps(user))
    send_message(vk_api, user_id, response)


def main():
    env = Env()
    env.read_env()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler()],
    )

    redis_client = redis.Redis(
        host=env.str("REDIS_HOST"),
        port=env.int("REDIS_PORT"),
        password=env.str("REDIS_PASSWORD"),
        ssl=False,
        ssl_cert_reqs=ssl.CERT_NONE,
        decode_responses=True,
        socket_timeout=10,
    )

    vk_session = vk_api.VkApi(token=env.str("VK_TOKEN"))
    longpoll = VkLongPoll(vk_session)
    vk = vk_session.get_api()
    quiz_dict = load_questions("quiz-questions")

    send_message(vk, env.int("ADMIN_ID"), "🟢 Бот успешно запущен!")
    logger.info("Бот запущен")

    for event in longpoll.listen():
        if event.type == VkEventType.MESSAGE_NEW and event.to_me:
            user_id = event.user_id
            text = event.text
            logger.info(f"Получено сообщение от {user_id}: {text}")

            if text == "Новый вопрос":
                handle_new_question(redis_client, quiz_dict, vk, user_id)
            elif text == "Сдаться":
                handle_give_up(redis_client, quiz_dict, vk, user_id)
            elif text == "Мой счёт":
                handle_score(redis_client, vk, user_id)
            else:
                handle_answer(redis_client, vk, user_id, text)


if __name__ == "__main__":
    main()

