from environs import Env
import telebot

env = Env()
env.read_env()

tg_token = env.str('TG_TOKEN')

bot = telebot.TeleBot(tg_token)


@bot.message_handler(commands=['start'])
def start_command(message):
    chat_id = message.chat.id
    bot.send_message(chat_id, "Здравствуйте!")


@bot.message_handler(func=lambda message: True)
def echo(message):
    chat_id = message.chat.id
    text = message.text

    bot.send_message(chat_id, text)


bot.polling()
