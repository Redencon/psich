import telebot
import json

with open('secret2.json', 'r', encoding='utf-8') as f:
    secret = json.load(f)


TOKEN = secret['TOKEN']
ADMIN = secret['ADMIN']
ARBITRARY_THRESHOLD = secret['ARBITRARY_THRESHOLD']
CHAT = secret['CHAT']

bot = telebot.TeleBot(TOKEN)

# with open('goodnight.json', 'r') as file:
#     gn = json.load(file)

with open('Nastya_Dicks.ogg', 'rb') as f:
    mess = bot.send_voice(ADMIN, f)
bot.send_voice(5050678382, mess.voice.file_id)
# for user in [834476079, 264630131, 1311246531]:
#     voice = bot.send_voice(user, mess.voice.file_id)
#     print('sent!', end=' ')
# print(mess.voice.file_id)
