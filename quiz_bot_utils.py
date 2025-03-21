import os
import ssl


def load_questions(questions_dir):
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
                            line.strip() for line in blocks[i].split("\n")[1:]
                        )
                        if i + 1 < len(blocks) and blocks[i + 1].startswith("Ответ"):
                            answer = " ".join(
                                line.strip() for line in blocks[i + 1].split("\n")[1:]
                            )
                            questions[question] = answer
    return questions


def create_keyboard(platform):
    if platform == "tg":
        from telebot.types import ReplyKeyboardMarkup, KeyboardButton

        keyboard = ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
        buttons = [
            KeyboardButton("Новый вопрос"),
            KeyboardButton("Сдаться"),
            KeyboardButton("Мой счёт"),
        ]
        keyboard.add(*buttons)
        return keyboard
    elif platform == "vk":
        from vk_api.keyboard import VkKeyboard, VkKeyboardColor

        keyboard = VkKeyboard(one_time=False)
        keyboard.add_button("Новый вопрос", color=VkKeyboardColor.PRIMARY)
        keyboard.add_button("Сдаться", color=VkKeyboardColor.NEGATIVE)
        keyboard.add_line()
        keyboard.add_button("Мой счёт", color=VkKeyboardColor.SECONDARY)
        return keyboard.get_keyboard()


def create_ssl_context():
    context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    return context
