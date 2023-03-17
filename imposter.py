import telebot
import json

with open('secret.json', 'r', encoding='utf-8') as f:
    secret = json.load(f)


TOKEN = secret['TOKEN']
ADMIN = secret['ADMIN']
ARBITRARY_THRESHOLD = secret['ARBITRARY_THRESHOLD']
CHAT = secret['CHAT']

bot = telebot.TeleBot(TOKEN)

with open('Nastya_fanart.ogg', 'rb') as file:
    voice = bot.send_voice(ADMIN, file)
    for user in (834476079, ):
        bot.send_voice(user, voice.voice.file_id)
        print('sent!')