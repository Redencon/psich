import telebot
import json
import schedule
import time

with open("secret.json", "r", encoding="utf-8") as f:
    secret = json.load(f)


TOKEN = secret["TOKEN"]
ADMIN = secret["ADMIN"]
ARBITRARY_THRESHOLD = secret["ARBITRARY_THRESHOLD"]
CHAT = secret["CHAT"]

bot = telebot.TeleBot(TOKEN)

TIMES = ("08:16", "12:11", "15:21", "20:01")


def send_poll(time):
    with open("status.json") as file:
        users = json.load(file)
        users = {int(user_id): value for user_id, value in users.items()}
    for user_id in users:
        if users[user_id] is not None:
            if users[user_id] == time:
                bot.send_voice(
                    user_id,
                    "AwACAgIAAxkBAAOQZBF96l0z6T0NosfWOxzM3X90I00AAoonAAIYM4hIMVdKHOssplcvBA",
                )
    return


for elem in TIMES:
    schedule.every().day.at(elem).do(send_poll, elem)
    while True:
        schedule.run_pending()
        time.sleep(1)
