import telebot
import json
import yaml
from telebot.apihelper import ApiException

for a in ("secret.json", "secret2.json"):
    with open(a, "r", encoding="utf-8") as f:
        secret = json.load(f)
    with open("loc.yaml", "r", encoding="utf-8") as f:
        loc = yaml.safe_load(f)

    TOKEN = secret["TOKEN"]
    ADMIN = secret["ADMIN"]
    ARBITRARY_THRESHOLD = secret["ARBITRARY_THRESHOLD"]
    CHAT = secret["CHAT"]
    STATUS_FILE = secret["STATUS_FILE"]

    bot = telebot.TeleBot(TOKEN)

    with open(STATUS_FILE) as file:
        users = json.load(file)

    for user in users:
        if users[user] is None:
            continue
        try:
            bot.send_message(user, loc["ru"]["service"]["beta_survey"])
            print("User {}: success".format(user))
        except ApiException:
            print("User {}: failure".format(user))
