import telebot
import json

with open('secret.json', 'r', encoding='utf-8') as f:
    secret = json.load(f)


TOKEN = secret['TOKEN']
ADMIN = secret['ADMIN']
ARBITRARY_THRESHOLD = secret['ARBITRARY_THRESHOLD']
CHAT = secret['CHAT']

bot = telebot.TeleBot(TOKEN)

with open('goodnight.json', 'r') as file:
    gn = json.load(file)

for filename in gn:
    voice = bot.send_voice(gn[filename]['user_id'], gn[filename]['file_id'])
    print('sent goodnights!', end=' ')
print()
