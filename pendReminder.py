import json
import telebot

with open("secret.json") as file:
  secret = json.load(file)
  PENDING_FILE = secret["PENDING_FILE"]
  RESPONSES_FOLDER = secret["RESPONSES_FOLDER"]
  TOKEN = secret["TOKEN"]

bot = telebot.TeleBot(TOKEN)

with open(PENDING_FILE) as file:
  users = json.load(file)

for user in users:
  try:
    with open(RESPONSES_FOLDER + "/" + str(user) + ".json") as file:
      user_data = json.load(file)
  except FileNotFoundError:
    continue
  if user_data["code"] is None:
    try:
      bot.send_message(
        user,
        "".join(
          ["Я заметила, что ты проявлял(а) интерес ко мне, ",
          "но не прошёл(а) регистрацию. Если это произошло ",
          "из-за того что я не ответила на сообщение с адресом почты, ",
          "это произошло из-за ошибки со стороны Google и теперь всё работает. ",
          "Если хочешь, можешь попоробовать зарегистрироваться ещё раз. ",
          "Для этого напиши свой адрес в домене phystech.edu"]
        ),
      )
    except telebot.apihelper.ApiException:
      print("User {} declined the attempt".format(user))
