import random
import logging
import vk_api

from vk_api.longpoll import VkEventType, VkLongPoll
from vk_api.utils import get_random_id

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

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

context = create_ssl_context()

redis_client = create_redis_client(env)

vk_session = vk_api.VkApi(token=env.str("VK_TOKEN"))
longpoll = VkLongPoll(vk_session)
vk = vk_session.get_api()
admin_id = env.int("ADMIN_ID")
quiz_dict = load_questions("quiz-questions")


def send_message(user_id, message):
    try:
        vk.messages.send(
            user_id=user_id,
            message=message,
            keyboard=create_keyboard("vk"),
            random_id=get_random_id(),
        )
        logger.info(f"Sent message to {user_id}")
    except vk_api.exceptions.ApiError as e:
        logger.error(f"VK API Error: {e}")


def handle_new_question(user_id):
    user = get_user_state(redis_client, user_id, "vk")
    question, answer = random.choice(list(quiz_dict.items()))
    user["current_question"] = {"question": question, "answer": answer}
    save_user_state(redis_client, user_id, user, "vk")
    send_message(user_id, f"❓ Вопрос:\n{question}")


def handle_give_up(user_id):
    user = get_user_state(redis_client, user_id, "vk")
    if not user["current_question"]:
        send_message(user_id, "⚠️ Сначала получите новый вопрос!")
        return
    answer = user["current_question"]["answer"]
    send_message(user_id, f"🏁 Правильный ответ:\n{answer}")
    handle_new_question(user_id)


def handle_score(user_id):
    user = get_user_state(redis_client, user_id, "vk")
    send_message(user_id, f"🏆 Текущий счёт: {user['score']}")


def handle_answer(user_id, text):
    user = get_user_state(redis_client, user_id, "vk")
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
    save_user_state(redis_client, user_id, user, "vk")
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
