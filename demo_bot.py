"""
Настенька
v. 1.0.0
"""

import os
import telebot
import json
import threading
import sys
import schedule
from telebot import types
import time
from gmail_send_message import send_code
import random
import gpt_users
import responses
from sql_base import DatabaseManager
from local import LocalizedStrings, UsefulStrings
from functools import partial

# from achievements import add_achievement
# from achievements import streak_achievement
# from achievements import average_consistency_achievement
from achievements import timestamp

# from achievements import achievement_message
from requests.exceptions import ConnectionError, HTTPError
from telebot.apihelper import ApiException
from surveys import convivnient_slicer, SurveyPool
from typing import Any, Optional, TypedDict


class Link(TypedDict):
  code: str
  link: str
  groups: list[str]
  used: bool


SECRET_FILE: str = sys.argv[1]
# TIMES = ("08:15", "12:10", "15:20", "20:00")

with open(SECRET_FILE, "r", encoding="utf-8") as f:
  secret = json.load(f)

TOKEN = secret["TOKEN"]
if len(sys.argv) > 2:
  TOKEN = sys.argv[2]
ADMIN = secret["ADMIN"]
ARBITRARY_THRESHOLD = secret["ARBITRARY_THRESHOLD"]
CHAT = secret["CHAT"]
SURVEY_FOLDER = secret["SURVEY_FOLDER"]
POOL_FILE = secret["POOL_FILE"]
START_FILE = secret["START_FILE"]
LOC_FILE = secret["LOC_FILE"]
DOMEN = secret["DOMEN"]
DB_PATH = secret["DB_PATH"]
s = True

TextPack = dict[str, dict[str, Any]]

loc_strings = LocalizedStrings(LOC_FILE)
service = loc_strings.service

bot = telebot.TeleBot(TOKEN)

chat_users = gpt_users.UserManager()
# poll_users = responses.UserManager(secret, chat_users)
poll_users = DatabaseManager(DB_PATH)
survey_pool = SurveyPool(
  SURVEY_FOLDER, ("data.bin" if TOKEN[0] == "5" else "data2.bin")
)

# gens = statusClasses.GeneralData(GENERAL_FILE, bot, ADMIN)
# pend = statusClasses.Pending_users(PENDING_FILE)
# blkl = statusClasses.Blacklist(BLACKLIST_FILE)


# def new_response(user_id, key, answer):
#   try:
#     with open(RESPONSES_FOLDER + "/" + str(user_id) + ".json") as file:
#       user_db = json.load(file)
#   except FileNotFoundError:
#     return False
#   if key in user_db["responses"].keys():
#     return False
#   user_db["responses"][key] = answer
#   with open(RESPONSES_FOLDER + "/" + str(user_id) + ".json", "w") as file:
#     json.dump(user_db, file)
#   return True


def wanna_get(message: types.Message):
  lang = poll_users.get_lang(message.from_user)
  bot.send_message(
    message.chat.id,
    service[lang]["wanna_get"],
    reply_markup=types.InlineKeyboardMarkup([[
      types.InlineKeyboardButton(
        ("Yes" if lang == "en" else "Да"), callback_data="ST_y"
      ),
      types.InlineKeyboardButton(
        ("No" if lang == "en" else "Нет"), callback_data="ST_n"
      ),
    ]]),
  )
  return


def demog_init(
  user_id: int,
  lang: str,
  chat_id: Optional[int] = None,
  message_id: Optional[int] = None,
):
  """Send the first message of demography poll.

  Provide chat and message id to edit a previous message into it instead
  """
  with open(POOL_FILE, encoding="utf-8") as file:
    questions = json.load(file)
  options = questions[lang][0][2]
  kwargs = dict(
    text=service[lang]["demog_init"] + "\n" + questions[lang][0][1],
    chat_id=chat_id if chat_id is not None else user_id,
    reply_markup=types.InlineKeyboardMarkup(
      [
        [
          types.InlineKeyboardButton(text, callback_data="DG_0" + str(i))
          for i, text in enumerate(options)
        ]
      ]
    ),
  )
  if message_id is not None and chat_id is not None:
    kwargs["message_id"] = message_id
    bot.edit_message_text(**kwargs)
  else:
    bot.send_message(**kwargs)


def registered_only(func):
  def new_func(message: types.Message, *m, **kw):
    lang = poll_users.get_lang(message.from_user)
    try:
      if poll_users.dem_finished(message.from_user.id):
        return func(message, *m, **kw)
      else:
        bot.send_message(message.chat.id, service[lang]["must_register"])
    except ApiException as e:
      bot.send_message(message.chat.id, service[lang]["must_register"])
      bot.send_message(ADMIN, "{}".format(e))

  return new_func


@bot.message_handler(
  commands=["setchat"], func=lambda message: message.from_user.id == ADMIN
)
def setchat(message: types.Message):
  CHAT = message.chat.id
  secret["CHAT"] = CHAT
  with open(SECRET_FILE, "w", encoding="utf-8") as f:
    json.dump(secret, f, ensure_ascii=False, indent=4)
  bot.send_message(CHAT, "Использую этот чат как чат операторов.")
  return


@bot.message_handler(commands=["start"])
def start(message: types.Message):
  assert message.text is not None
  poll_user = poll_users.new_user(
    message.from_user.id,
    message.from_user.username,
    message.from_user.first_name
  )
  if poll_user is not None:
    lang = poll_users.get_lang(message.from_user)
    if DOMEN is not None:
      bot.send_message(message.from_user.id, service[lang]["verification"])
      poll_users.set_meta(message.from_user.id, "verified", "False")
      return
      argv = message.text.split()
      if len(argv) != 2:
        bot.send_message(message.chat.id, service[lang]["only_link"])
        return
      with open("codes.json") as file:
        data: list[Link] = json.load(file)
        links: dict[str, Link] = {link["code"]: link for link in data}
        del data
      if argv[1] not in links or links[argv[1]]["used"]:
        bot.send_message(message.chat.id, service[lang]["used_link"])
        return
      # bot.send_message(message.chat.id, service[lang]["verification"])
      links[argv[1]]["used"] = True
      groups = links[argv[1]]["groups"]
      with open("codes.json", "w") as file:
        json.dump(list(links.values()), file)
      poll_user = poll_users.new_user(
        message.from_user.id,
        message.from_user.username,
        message.from_user.first_name,
      )
      poll_user.meta["verified"] = True
      for group in groups:
        poll_users.add_user_to_group(message.from_user.id, group)

      # poll_user.meta["code"] = None
      poll_users.dump_user(message.from_user.id)
    wanna_get(message)
    return
  uid = message.from_user.id
  if poll_users.is_user_verified(uid) and not poll_users.dem_finished(uid):
    wanna_get(message)
    return
  # Start is equal to /help when user is not new
  lang = poll_users.get_lang(message.from_user)
  bot.reply_to(message, loc_strings.get_help(lang, "help"))
  return


@bot.message_handler(["help"])
def help(message: types.Message):
  assert message.text is not None
  lang = poll_users.get_lang(message.from_user)
  # help_db = get_help()
  argv = message.text.split()
  if len(argv) == 1:
    cmd = "help"
  else:
    cmd = argv[1]
  if not loc_strings.is_in_help(cmd):
    bot.reply_to(message, service[lang]["help_fail"])
    return
  bot.reply_to(message, loc_strings.get_help(lang, cmd))
  return


@bot.message_handler(["poll"])
@registered_only
def request_poll(message: types.Message):
  lang = poll_users.get_lang(message.from_user)
  bot.send_message(
    message.chat.id,
    service[lang]["get_poll"],
    reply_markup=types.InlineKeyboardMarkup(
      [
        [
          types.InlineKeyboardButton("🌠", callback_data="PR_mood"),
          types.InlineKeyboardButton("💊", callback_data="PR_health"),
          types.InlineKeyboardButton("❎", callback_data="PR_cancel"),
        ]
      ]
    ),
  )


@bot.callback_query_handler(lambda call: call.data[:3] == "PR_")
def poll_response(call: types.CallbackQuery):
  lang = poll_users.get_lang(call.from_user)
  bot.answer_callback_query(call.id, service[lang]["ok"])
  tpe = call.data[3:]
  if tpe == "cancel":
    bot.edit_message_text(
      service[lang]["ok"], call.message.chat.id, call.message.id
    )
    return
  assert tpe == "mood" or tpe == "health"
  bot.edit_message_reply_markup(call.message.chat.id, call.message.id, None)
  poll_users.send_poll(bot, call.from_user.id, tpe, lang, True)


@bot.callback_query_handler(lambda call: call.data[:3] == "ST_")
def start_response(call: types.CallbackQuery):
  lang = poll_users.get_lang(call.from_user)
  uid = call.from_user.id
  bot.answer_callback_query(call.id, service[lang]["thanks"])
  bot.edit_message_text(
    service[lang]["thanks"], call.message.chat.id, call.message.id
  )
  if not poll_users.user_exists(uid):
    bot.send_message(uid, service[lang]["must_register"])
    return
  if call.data[-1] == "y":
    if not poll_users.dem_finished(uid):
      demog_init(uid, lang)
      return
    send_time(uid, lang)
    return


@bot.callback_query_handler(lambda call: call.data[:3] == "DS_")
def parse_survey(call: types.CallbackQuery):
  assert call.message.text is not None
  lang = poll_users.get_lang(call.from_user)
  uid = call.from_user.id
  tpe = dict(h="health", m="mood")[call.data[-3]]
  if tpe == "mood":
    hearts = poll_users.get_user_hearts(uid)
  else:
    hearts = UsefulStrings.hearts[tpe]
  answer = int(call.data[-1])
  text = call.message.text.split("\n")
  bot.answer_callback_query(
    call.id, service[lang]["poll_answer"].format(answer=hearts[answer])
  )
  poll_users.add_response(call.from_user.id, tpe, answer)
  bot.edit_message_text(
    "\n".join(text)
    + "\n"
    + service[lang]["poll_answer"].format(answer=hearts[answer]),
    call.message.chat.id,
    call.message.id,
    reply_markup=None,
  )
  poll_users.update_admin(bot, tpe, ADMIN)
  if tpe == "mood":
    bot.send_message(
      call.message.chat.id, random.choice(LocalizedStrings().respons_texts[lang][answer])
    )
  # for i in (3, 7, 14, 30, 61, 150):
  #   a = streak_achievement(call.from_user.id, i, RESPONSES_FOLDER + "/")
  #   if a is not None:
  #     if a:
  #       bot.send_message(
  #         call.message.chat.id, achievement_message("streak_" + str(i), lang)
  #       )
  #     else:
  #       break
  # for i in (15, 30):
  #   a = average_consistency_achievement(call.from_user.id, i)
  #   if a:
  #     bot.send_message(
  #       call.message.chat.id, achievement_message("consistency_" + str(i), lang)
  #     )
  # # TODO: add experience system, see #11


@bot.message_handler(commands=["unsub", "sub"])
def unsub(message):
  wanna_get(message)
  return


@bot.callback_query_handler(lambda call: call.data[:3] == "DG_")
def demogr(call: types.CallbackQuery):
  lang = poll_users.get_lang(call.from_user)
  bot.answer_callback_query(call.id)
  with open(POOL_FILE, encoding="utf-8") as file:
    questions = json.load(file)
  cur = int(call.data[3])
  ans = int(call.data[4:])
  poll_users.dem_response(
    call.from_user.id, questions[lang][cur][0], questions[lang][cur][2][ans]
  )
  cur += 1
  if cur >= len(questions[lang]):
    bot.edit_message_text(
      service[lang]["demog_end"], call.message.chat.id, call.message.id
    )
    send_time(call.from_user.id, lang)
    # dab_upd(STATUS_FILE, call.from_user.id, TIMES[1])
    bot.send_message(ADMIN, f"Новый пользователь: {call.from_user.full_name}")
    # if time.localtime()[3] > 12 or (time.localtime()[3] == 12 and time.localtime()[4] > 10):
    #   poll(call.from_user.id, lang)
    return
  else:
    bot.edit_message_text(
      service[lang]["demog_init"] + "\n" + questions[lang][cur][1],
      call.message.chat.id,
      call.message.id,
      reply_markup=types.InlineKeyboardMarkup(
        convivnient_slicer(
          [
            types.InlineKeyboardButton(
              text, callback_data="DG_" + str(cur) + str(i)
            )
            for i, text in enumerate(questions[lang][cur][2])
          ]
        ),
        row_width=5,
      ),
    )
    return


# def calendar(user_id, month, year, tpe="mood"):
#   def days_in_month(month, year):
#     if month == 2:
#       if year % 4 == 0:
#         return 29
#       return 28
#     if month in (1, 3, 5, 7, 8, 10, 12):
#       return 31
#     return 30
#   user_calendar = poll_users.users[user_id].calendar(tpe)
#   stamp = time.mktime((year, month, 1, 0, 0, 0, 0, 0, -1))
#   time_struct = time.localtime(stamp)
#   grey = (time_struct.tm_wday - 1 + 1) % 7
#   month = [
#     time.strftime(
#       responses.DATE_FORMAT, time.strptime(f"{year}-{month}-{i}", "%Y-%m-%d")
#     )
#     for i in range(1, days_in_month(month, year) + 1)
#   ]
#   stat = [user_calendar[i] if i in user_calendar else 7 for i in month]
#   text = [["⚫"] * grey]
#   for s in stat:
#     if len(text[-1]) == 7:
#       text.append([])
#     text[-1].append(UsefulStrings.colorcoding[s])
#   text[-1] += ["⚫"] * (7 - len(text[-1]))
#   text = "\n".join(["".join(a) for a in text])
#   return text


# def today(tpe, user_id, lang):
#   hearts = UsefulStrings.hearts
#   if poll_users.agg_today(tpe) < 3:
#     bot.send_message(user_id, service[lang]["today_fail"])
#     return
#   bot.send_message(
#     user_id,
#     service[lang]["today_text"].format(tpe, hearts[tpe][poll_users.agg_today(tpe)]),
#   )
#   return


@bot.message_handler(commands=["stats"])
@registered_only
def stats(message: types.Message):
  assert message.text is not None
  lang = poll_users.get_lang(message.from_user)
  curyear = time.localtime()[0]
  curmonth = time.localtime()[1]
  argv = message.text.split()[1:]
  if len(argv) > 0:
    if argv[0].isdigit():
      curmonth = int(argv[0])
      if curmonth > time.localtime()[1]:
        curyear -= 1
  user_id = message.from_user.id
  # if add_achievement(message.from_user.id, "stats", RESPONSES_FOLDER + "/"):
  #   bot.send_message(message.chat.id, achievement_message("stats", lang))
  bot.send_message(
    message.chat.id,
    "{0} {1}/{2}:\n{3}".format(
      service[lang]["stats"],
      str(curmonth),
      str(curyear),
      poll_users.get_user_calendar_string(user_id, curmonth, curyear, False),
    ),
    reply_markup=types.InlineKeyboardMarkup(
      [
        [
          types.InlineKeyboardButton("◀️", callback_data="SS_-"),
          types.InlineKeyboardButton("❤", callback_data="SS_T"),
          types.InlineKeyboardButton("▶️", callback_data="SS_+"),
        ]
      ]
    ),
  )
  return


@bot.message_handler(["skin"])
@registered_only
def skin(message: types.Message):
  lang = poll_users.get_lang(message.from_user)
  with open("skins.json", encoding="utf-8") as f:
    skins: list[list[str]] = json.load(f)
  bot.send_message(
    message.chat.id,
    service[lang]["skin"],
    reply_markup=types.InlineKeyboardMarkup([
      [types.InlineKeyboardButton("".join(skin_s), callback_data="SK_{}".format(i))]
      for i, skin_s in enumerate(skins)
    ])
  )


@bot.callback_query_handler(lambda call: call.data[:3] == "SK_")
def reskin(call: types.CallbackQuery):
  assert call.message.reply_markup is not None
  lang = poll_users.get_lang(call.from_user)
  i = int(call.data[3:])
  with open("skins.json", encoding="utf-8") as f:
    skins: list[list[str]] = json.load(f)
  skin_s = skins[i]
  bot.edit_message_text(
    service[lang]["skin_set"].format("".join(skin_s)),
    call.message.chat.id,
    call.message.id
  )
  poll_users.set_user_hearts(call.from_user.id, skin_s)


@bot.callback_query_handler(lambda call: call.data[:3] == "SS_")
def switch_calendar(call: types.CallbackQuery):
  assert call.message.reply_markup is not None
  assert call.message.text is not None
  lang = poll_users.get_lang(call.from_user)
  data = call.data[-1]
  uid = call.from_user.id
  month, year = map(int, call.message.text.split("\n")[0].split()[-1][:-1].split("/"))
  default = call.message.reply_markup.keyboard[0][1].text != "❤"
  if data == "+":
    month += 1
    if month == 13:
      year += 1
      month = 1
  elif data == "-":
    month -= 1
    if month == 0:
      year -= 1
      month = 12
  elif data == "T":
    call.message.reply_markup.keyboard[0][1].callback_data = "SS_F"
    call.message.reply_markup.keyboard[0][1].text = poll_users.get_user_hearts(uid)[0]
    default = True
  else:
    call.message.reply_markup.keyboard[0][1].callback_data = "SS_T"
    call.message.reply_markup.keyboard[0][1].text = "❤"
    default = False
  bot.edit_message_text(
    "{stats} {month}/{year}:\n{calendar}".format(
      stats=service[lang]["stats"],
      month=month,
      year=year,
      calendar=poll_users.get_user_calendar_string(uid, month, year, default),
    ),
    call.message.chat.id,
    call.message.id,
    reply_markup=call.message.reply_markup,
  )
  bot.answer_callback_query(call.id, service[lang]["stats_next"])


@bot.message_handler(commands=["delete"])
def delete(message):
  lang = poll_users.get_lang(message.from_user)
  bot.send_message(
    message.chat.id,
    service[lang]["delete"],
    reply_markup=types.InlineKeyboardMarkup(
      [
        [
          types.InlineKeyboardButton("Да", callback_data="CL_y"),
          types.InlineKeyboardButton("Нет", callback_data="CL_n"),
        ]
      ]
    ),
  )
  return


@bot.message_handler(commands=["today"])
@registered_only
def today(message: types.Message):
  lang = poll_users.get_lang(message.from_user)
  # if add_achievement(message.from_user.id, "today", RESPONSES_FOLDER + "/"):
  #   bot.send_message(message.chat.id, achievement_message("today", lang))
  bot.send_message(
    message.chat.id,
    service[lang]["today_request"],
    reply_markup=types.InlineKeyboardMarkup(
      [
        [
          types.InlineKeyboardButton("🌠", callback_data="TR_mood"),
          types.InlineKeyboardButton("💊", callback_data="TR_health"),
          types.InlineKeyboardButton("❎", callback_data="TR_none"),
        ],
      ]
    ),
  )
  return


@bot.callback_query_handler(lambda call: call.data[:3] == "TR_")
def tr_request(call: types.CallbackQuery):
  lang = poll_users.get_lang(call.from_user)
  tpe = call.data[3:]
  bot.answer_callback_query(call.id)
  if tpe == "none":
    bot.edit_message_reply_markup(
      call.message.chat.id, call.message.id, reply_markup=None
    )
    return
  text = poll_users.tracker_text(tpe, lang)
  poll_users.add_tracker(
    call.message.chat.id, call.message.id, tpe, text
  )
  bot.edit_message_text(
    text, call.message.chat.id, call.message.id, reply_markup=None
  )


@bot.callback_query_handler(lambda call: call.data[:3] == "CL_")
def wipe(call: types.CallbackQuery):
  lang = poll_users.get_lang(call.from_user)
  bot.answer_callback_query(call.id, service[lang]["ok"])
  if call.data[-1] == "n":
    bot.delete_message(call.message.chat.id, call.message.id)
    bot.delete_message(call.message.chat.id, call.message.id - 1)
    return
  poll_users.rm_user(call.from_user.id)
  chat_users.delete_user(call.from_user.id)
  bot.delete_message(call.message.chat.id, call.message.id)
  return


def email_is_awaited(message: types.Message):
  assert message.text is not None
  if message.chat.type != "private":
    return False
  if message.text[0] == "/":
    return False
  if DOMEN is None:
    return False
  if not poll_users.user_exists(message.from_user.id):
    return False
  return not poll_users.is_user_verified(message.from_user.id)


@bot.message_handler(func=email_is_awaited)
def email(message: types.Message):
  lang = poll_users.get_lang(message.from_user)
  response = message.text
  uid = message.from_user.id
  assert response is not None
  if response.isdigit():
    code = poll_users.get_meta(uid, "code")
    if code is not None:
      if int(response) == int(code):
        bot.send_message(message.chat.id, service[lang]["success"])
        poll_users.set_meta(uid, "verified", "True")
        wanna_get(message)
        return
      else:
        bot.send_message(message.chat.id, service[lang]["email_wrong_code"])
        return
    return
  else:
    try:
      code = send_code(response, DOMEN)
    except Exception as e:
      bot.send_message(
        ADMIN,
        "Токен GMail сгорел. Обнови. Его хотели использовать\n{}: {}".format(message.from_user.id, message.from_user.username),
      )
      bot.send_message(message.chat.id, service[lang]["registration_closed"])
      return
    if code is None:
      bot.send_message(message.chat.id, service[lang]["email_wrong_adress"])
      return
    if code == -1:
      bot.send_message(message.chat.id, service[lang]["email_wrong_domen"])
      return
    print(code)
    poll_users.set_meta(uid, "code", str(code))
    bot.send_message(message.chat.id, service[lang]["email_sent"])
    return


def default_time_keyboard():
  Ikb = types.InlineKeyboardButton
  return types.InlineKeyboardMarkup(
    [
      [
        Ikb("+6h", None, "TP_+6h"),
        Ikb("+1h", None, "TP_+1h"),
        Ikb("✅", None, "TP_done"),
        Ikb("+5m", None, "TP_+5m"),
        Ikb("+15m", None, "TP_+15m"),
      ],
      [
        Ikb("🔁", None, "TP_default"),
        Ikb("12", None, "TP_none"),
        Ikb(":", None, "TP_none"),
        Ikb("10", None, "TP_none"),
        Ikb("🌠", None, "TP_type"),
      ],
      [
        Ikb("-6h", None, "TP_-6h"),
        Ikb("-1h", None, "TP_-1h"),
        Ikb("❎", None, "TP_cancel"),
        Ikb("-5m", None, "TP_-5m"),
        Ikb("-15m", None, "TP_-15m"),
      ],
    ]
  )


def send_time_picker(user_id: int, lang: str = "en"):
  keyboard = default_time_keyboard()
  bot.send_message(user_id, service[lang]["time_choose"], reply_markup=keyboard)


@bot.callback_query_handler(lambda call: call.data[:3] == "TP_")
def time_picker_handler(call: types.CallbackQuery):
  assert call.message.reply_markup is not None
  data = call.data[3:]
  lang = poll_users.get_lang(call.from_user)
  if data == "none":
    bot.answer_callback_query(call.id)
    return
  if data == "cancel":
    bot.answer_callback_query(call.id, service[lang]["ok"])
    bot.edit_message_text(
      service[lang]["time_cancel"], call.message.chat.id, call.message.id
    )
    return
  keyboard = call.message.reply_markup.keyboard
  current_type = keyboard[1][4].text
  type_map = {"🌠": "mood", "💊": "health"}
  if data == "type":
    bot.answer_callback_query(
      call.id, "👍"
    )
    return
    rtm = {value: key for key, value in type_map.items()}
    new_type = rtm["mood" if type_map[current_type] == "health" else "health"]
    keyboard[1][4].text = new_type
    bot.edit_message_reply_markup(
      call.message.chat.id,
      call.message.id,
      reply_markup=types.InlineKeyboardMarkup(keyboard),
    )
    return
  if data[0] in ("+", "-"):
    amount = int(data[:-1])
    if data[-1] == "h":
      h = int(keyboard[1][1].text)
      h = (h + amount) % 24
      keyboard[1][1].text = str(h)
    if data[-1] == "m":
      m = int(keyboard[1][3].text)
      m = (m + amount) % 60
      keyboard[1][3].text = str(m)
    bot.answer_callback_query(call.id, data)
    bot.edit_message_reply_markup(
      call.message.chat.id,
      call.message.id,
      reply_markup=types.InlineKeyboardMarkup(keyboard),
    )
    return
  if data == "default":
    bot.answer_callback_query(call.id)
    if call.message.reply_markup == default_time_keyboard():
      return
    bot.edit_message_reply_markup(
      call.message.chat.id, call.message.id, reply_markup=default_time_keyboard()
    )
    return
  if data == "done":
    import re
    bot.answer_callback_query(call.id)
    bot.edit_message_text(
      service[lang]["ok"], call.message.chat.id, call.message.id
    )
    actual_current_type = type_map[current_type]
    h = keyboard[1][1].text
    m = keyboard[1][3].text
    text = call.message.text
    assert text is not None
    match = re.search(r"\(UTC ([+-]\d+)\)", text)
    if match is None:
      time_shift = 0
    else:
      time_shift = int(match.group(1)) - 3
    h = str(int(h) - time_shift)
    uid = call.from_user.id
    poll_users.add_poll(
      uid, "{}:{}".format(h, m), actual_current_type
    )
    polls = poll_users.get_pending_polls(uid)
    for tpe in polls:
      poll_users.send_poll(bot, call.from_user.id, tpe, lang)


def send_time(uid: int, lang: str):
  bot.send_message(
    uid,
    service[lang]["type_choice"],
    reply_markup=types.InlineKeyboardMarkup(
      [
        [
          types.InlineKeyboardButton("🌠", callback_data="PC_mood"),
          # types.InlineKeyboardButton("💊", callback_data="PC_health"),
          types.InlineKeyboardButton("🔴", callback_data="PC_cancel"),
          types.InlineKeyboardButton("❎", callback_data="PC_none"),
        ]
      ]
    ),
  )


@bot.message_handler(commands=["time"])
@registered_only
def time_present(message: types.Message):
  lang = poll_users.get_lang(message.from_user)
  bot.send_message(
    message.chat.id,
    service[lang]["time_rm"],
    reply_markup=types.InlineKeyboardMarkup(polls_keyboard(message.from_user.id)),
  )
  return


def polls_keyboard(uid: int):
  polls = poll_users.get_user_polls(uid)
  time_shift = poll_users.get_user_timezone(uid)
  keyboard = []
  for i, poll in enumerate(polls):
    if time_shift:
      h, m = poll.time.split(":")
      h = str((int(h) + time_shift) % 24)
      time_str = f"{h}:{m}"
    else:
      time_str = poll.time
    keyboard.append(
      [
        types.InlineKeyboardButton(
          "{} - {}".format(time_str, poll.tpe), callback_data="PD_{}".format(i)
        )
      ]
    )
  keyboard.append([types.InlineKeyboardButton("➕", callback_data="PC_mood")])
  keyboard.append([types.InlineKeyboardButton("❎", callback_data="PD_none")])
  return keyboard


@bot.callback_query_handler(lambda call: call.data[:3] == "PC_")
def poll_choose(call: types.CallbackQuery):
  bot.answer_callback_query(call.id)
  lang = poll_users.get_lang(call.from_user)
  time_shift = poll_users.get_user_timezone(call.from_user.id)
  tpe = call.data[3:]
  uid = call.from_user.id
  if tpe == "none":
    bot.delete_message(call.message.chat.id, call.message.id)
    return
  if tpe == "cancel":
    bot.edit_message_text(
      service[lang]["time_rm"],
      call.message.chat.id,
      call.message.id,
      reply_markup=types.InlineKeyboardMarkup(polls_keyboard(uid)),
    )
    return
  markup = default_time_keyboard()
  markup.keyboard[1][4].text = UsefulStrings.poll_types[tpe]
  bot.edit_message_text(
    service[lang]["time_kb"].format("{:+d}".format(time_shift + 3)),
    call.message.chat.id,
    call.message.id,
    reply_markup=markup,
  )


@bot.callback_query_handler(lambda call: call.data[:3] == "PD_")
def time_remove(call: types.CallbackQuery):
  lang = poll_users.get_lang(call.from_user)
  bot.answer_callback_query(call.id)
  uid = call.from_user.id
  time_shift = poll_users.get_user_timezone(uid)
  i = call.data[3:]
  if i == "none":
    bot.edit_message_text(
      service[lang]["ok"],
      call.message.chat.id,
      call.message.id,
      reply_markup=None,
    )
    return
  uid = call.from_user.id
  assert call.message.reply_markup is not None
  text = call.message.reply_markup.keyboard[int(i)][0].text
  tme, tpe = text.split(" - ")
  if time_shift:
    h, m = tme.split(":")
    h = str((int(h) - time_shift) % 24)
    time_str = f"{h}:{m}"
  else:
    time_str = tme
  poll_users.rm_poll(uid, time_str, tpe)
  bot.edit_message_reply_markup(
    call.message.chat.id,
    call.message.id,
    reply_markup=types.InlineKeyboardMarkup(polls_keyboard(uid)),
  )


# @bot.message_handler(commands=["achievements"])
# @registered_only
# def achievements(message: types.Message):
#   lang = poll_users.  get_lang(message.from_user)
#   with open(
#     RESPONSES_FOLDER + "/" + str(message.from_user.id) + ".json",
#     "r",
#     encoding="utf-8",
#   ) as f:
#     data = json.load(f)
#   if "achievements" not in data.keys():
#     data["achievements"] = []
#     with open(
#       RESPONSES_FOLDER + "/" + str(message.from_user.id) + ".json",
#       "w",
#       encoding="utf-8",
#     ) as f:
#       json.dump(data, f)
#   bot.send_message(
#     message.chat.id,
#     "{init}:\n{achievements}".format(
#       init=service[lang]["achievements"],
#       achievements="\n\n".join(
#         [
#           "✨{name}:\n{description}".format(
#             name=achievements_d[lang][name]["name"],
#             description=achievements_d[lang][name]["description"],
#           )
#           for name in data["achievements"]
#         ]
#       ),
#     ),
# )


# @bot.message_handler(
#   commands=["thanks"],
#   func=lambda message: message.chat.id == CHAT
#   and message.reply_to_message is not None,
# )
# def thanks(message: types.Message):
#   pseudonym = message.reply_to_message.text.split("\n")[0][2:]
#   if add_achievement(
#     chat_users.get_user_by_pseudonym(pseudonym).id,
#     "good_conversation",
#     RESPONSES_FOLDER + "/",
#   ):
#     bot.send_message(
#       chat_users.get_user_by_pseudonym(pseudonym).id,
#       achievement_message("good_conversation"),
#     )


# @bot.message_handler(commands=["grant"], func=lambda message: message.chat.id == ADMIN)
# def grant(message: types.Message):
#   text = message.text.split()[1:]
#   with open("achievements.json", "r", encoding="utf-8") as f:
#     gen_data = json.load(f)
#   if len(text) < 2:
#     return
#   if not text[0].isdigit():
#     return
#   if text[1] not in gen_data.keys():
#     return
#   user = int(text[0])
#   if add_achievement(user, text[1], RESPONSES_FOLDER + "/"):
#     bot.send_message(user, achievement_message(text[1]))
#     bot.send_message(ADMIN, "Добавила достижение.")


"""Making friends
@bot.message_handler(["friends"])
@registered_only
def friends_menu(message: types.Message):
  lang = poll_users.get_lang(message.from_user)
  bot.send_message(
    message.chat.id,
    service[lang]["friends_main"],
    reply_markup=types.InlineKeyboardMarkup([
      [types.InlineKeyboardButton(service[lang]["friends_list"], callback_data="FN_ls")],
      [types.InlineKeyboardButton(service[lang]["friends_add"], callback_data="FN_ad")]
    ])
  )


@bot.callback_query_handler(lambda call: call.data == "FN_ls")
def add_friend(message: types.Message):
  assert message.text is not None


@bot.callback_query_handler(lambda call: call.data == "FN_ls")
def show_friends(call: types.CallbackQuery):
  lang = poll_users.get_lang(call.from_user)
  uid = call.from_user.id
  user = poll_users.users[uid]
  friends = user.meta.get("friends", None)
  if friends is None:
    user.meta["friends"] = []
    poll_users.dump_user(uid)
    friends = []
  if len(friends) == 0:
    bot.send_message(
      call.message.chat.id,
      service[lang]["no_friends"]
    )
    return
    
  bot.send_message(
    call.message.chat.id,
    "{}\n{}".format("@")
  )
"""


@bot.message_handler(["checkuser"], func=lambda message: message.from_user.id == ADMIN)
def checkuser(message):
  entities = message.entities
  buffer = ""
  for entity in entities:
    buffer += entity.type
    buffer += " " + str(entity.user.id) if entity.user is not None else "None"
    buffer += "\n"
  bot.reply_to(message, buffer)


@bot.message_handler(
  commands=["patch"],
  func=lambda message: message.from_user.id == ADMIN,
  chat_types=["private"],
)
def patch(message: types.Message):
  assert message.text is not None
  assert message.entities is not None
  if message.text == "/patch":
    bot.reply_to(
      message,
      "Команда рассылки объявлений через бота.\nСинтаксис: /patch <importance> <message>",
      entities=[types.MessageEntity("code", 51, 29)],
    )
    return
  text = " ".join(message.text.split()[1:])
  entities = message.entities
  for entity in entities:
    entity.offset = entity.offset - (7)
  for user in poll_users.get_active_users():
    bot.send_message(
      user,
      text,
      entities=entities,
      disable_web_page_preview=True
    )

  # Used to debug
  # bot.send_message(ADMIN, text, entities=entities, disable_web_page_preview=True)
  # if importance in subscription[ADMIN] or importance == 'extra':
  #  bot.send_message(ADMIN, text, entities=entities)
  return


# @bot.message_handler(["run"], func=lambda message: message.from_user.id == ADMIN)
# def run(message):
#   poll_users.forced_polls(bot)
#   bot.reply_to(message, "Отправила опросы.")
#   return


@bot.message_handler(["language"])
def language(message: types.Message):
  bot.send_message(
    message.chat.id,
    "Выбери язык/Choose language",
    reply_markup=types.InlineKeyboardMarkup(
      [
        [
          types.InlineKeyboardButton("Русский", callback_data="LG_ru"),
          types.InlineKeyboardButton("English", callback_data="LG_en"),
        ]
      ]
    ),
  )


# @bot.message_handler(["groups"])
# @registered_only
# def groups(message: types.Message):
#   lang = poll_users.get_lang(message.from_user)
#   bot.send_message(
#     message.chat.id,
#     service[lang]["groups_init"].format(
#       groups="\n\n".join(
#         [
#           "{}: {}".format(
#             poll_users.groups[group].name,
#             poll_users.groups[group].description,
#           )
#           for group in groups
#         ]
#       )
#     ),
#   )


@bot.callback_query_handler(func=lambda call: call.data[:3] == "SA_")
def survey_answer(call: types.CallbackQuery):
  lang = poll_users.get_lang(call.from_user)
  argvn = len(call.data.split("_"))
  if argvn == 3:  # Then it's an answer to initial question
    _, code, ans = call.data.split("_")
    if ans == "n":
      bot.answer_callback_query(call.id, service[lang]["ok"])
      bot.edit_message_text(
        service[lang]["thanks"], call.message.chat.id, call.message.id
      )
      survey_pool.user_declined(code, call.from_user.id)
      return
    bot.answer_callback_query(call.id)
    if code not in survey_pool.active_surveys:
      bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.id,
        text=service[lang]["survey_expired"],
      )
      return
    bot.edit_message_text(
      chat_id=call.message.chat.id,
      message_id=call.message.id,
      **survey_pool.active_surveys[code].get_question(0),
    )
    return
  assert argvn == 4, "callback data is wrong"
  if survey_pool.answer(call.from_user.id, call.data):
    _, code, qid, _ = call.data.split("_")
    qid = int(qid) + 1
    if code not in survey_pool.active_surveys:
      bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.id,
        text=service[lang]["survey_expired"],
      )
      return
    bot.edit_message_text(
      chat_id=call.message.chat.id,
      message_id=call.message.id,
      **survey_pool.get_question(code, qid),
    )


@bot.message_handler(
  ["survey"], func=lambda m: m.from_user.id == ADMIN and len(m.text.split()) >= 2
)
def start_survey(message: types.Message):
  assert message.text is not None
  argv = message.text.split()
  code = argv[1]
  if code == "kill":
    if len(argv) == 2:
      return
    code = argv[2]
    if survey_pool.kill_survey(code):
      bot.reply_to(message, "Survey {} killed".format(code))
    else:
      bot.reply_to(message, "Survey {} not found".format(code))
    return
  if code == "list":
    bot.reply_to(
      message,
      "Survey list:\n{}".format("\n".join(survey_pool.active_surveys.keys())),
    )
    return
  if code == "codes":
    files = [
      file[:-5] 
      for file in os.listdir("surveys") 
      if file.endswith(".json")
    ]
    bot.reply_to(
      message,
      "Available survey codes list:\n{}".format("\n".join(files)),
    )
    return
  if code.endswith(".json"):
    survey = survey_pool.spawn_survey(config_filename=code)
  else:
    survey = survey_pool.spawn_survey(code=code)
  if survey is None:
    bot.reply_to(message, "No config with such name {} found".format(code))
    return
  for user in survey.participants:
    if not poll_users.user_exists(user):
      survey_pool.user_declined(survey.code, user)
      continue
    lang = "en"
    try:
      bot.send_message(
        user,
        service[lang]["survey_request"].format(survey.init),
        reply_markup=types.InlineKeyboardMarkup([[
          types.InlineKeyboardButton(
            text=("Yes" if lang == "en" else "Да"),
            callback_data="SA_{}_y".format(survey.code),
          ),
          types.InlineKeyboardButton(
            text=("No" if lang == "en" else "Нет"),
            callback_data="SA_{}_n".format(survey.code),
          ),
        ]]),
      )
    except ApiException:
      survey_pool.user_declined(survey.code, user)
  bot.reply_to(message, "Survey started")


@bot.message_handler(content_types=["document"], func=lambda m: m.from_user.id == ADMIN)
def recieve_survey_json(message: types.Message):
  # document = message.document.file_id
  pass


@bot.callback_query_handler(func=lambda call: call.data[:3] == "LG_")
def language_choice(call: types.CallbackQuery):
  poll_users.set_meta(call.from_user.id, "lang", call.data[3:])
  bot.answer_callback_query(call.id, call.data[3:])
  bot.edit_message_text(
    service[call.data[3:]]["language"], call.message.chat.id, call.message.id
  )


# @bot.message_handler(["report"], func=lambda m: m.chat.id == ADMIN)
# def send_report(_):
#   from report import make_report

#   a = make_report(poll_users)
#   with open(a, "rb") as file:
#     bot.send_document(ADMIN, file, caption="Report for " + timestamp())
#   os.remove(a)
#   return


@bot.message_handler(["demog"])
def demog_manual(message: types.Message):
  lang = poll_users.get_lang(message.from_user)
  demog_init(message.from_user.id, lang)
  poll_users.dem_wipe(message.from_user.id)


# @bot.message_handler(["forcedemog"], func=lambda m: m.from_user.id == ADMIN)
# def force_demog(_: types.Message):
#   for uid, user in poll_users.users.items():
#     demog_init(uid, user.meta.get("lang", "en"))
#     user.meta["demog"] = {}
#     poll_users.dump_user(uid)
#   bot.send_message(ADMIN, "Sent renewed demog polls")


def safe_send_message(chat_id, message):
  try:
    return bot.send_message(chat_id, message)
  except ConnectionError:
    time.sleep(3)
    return safe_send_message(chat_id, message)


@bot.message_handler(
  content_types=["text"],
  func=lambda message: message.from_user.id == message.chat.id
  and message.text[0] != "/",
)
@registered_only
def anon_message(message: types.Message):
  lang = poll_users.get_lang(message.from_user)
  text = message.text
  uid = message.from_user.id
  assert text is not None
  hearts = ["❤️", "🧡", "💛", "💚", "💙", "💜", "❤️‍🩹"]
  user = chat_users.get_user_by_id(uid)
  if user is None:
    user = chat_users.new_user(uid, message.from_user.first_name)
    if user is None:
      bot.send_message(ADMIN, "USER OVERFLOW!!!")
      bot.send_message(uid, service[lang]["user_overflow"])
      return
  user.last_personal_message = message.id
  score = poll_users.get_today_status(uid)
  if score is not None:
    status = hearts[score]
  else:
    status = "❓"
  try:
    safe_send_message(CHAT, status + " " + user.pseudonym + "\n" + text)
  except telebot.apihelper.ApiTelegramException:
    print("Чат не найден:", CHAT)
  return


@bot.message_handler(
  content_types=["text"],
  func=lambda message: message.chat.id == CHAT
  and message.reply_to_message is not None,
)
def reply_to_anon_message(message: types.Message):
  assert message.reply_to_message is not None
  assert message.reply_to_message.text is not None
  assert message.text is not None
  if message.reply_to_message.from_user.id != bot.get_me().id:
    return
  reply = message.reply_to_message.text
  if reply[0] not in ("❤️", "🧡", "💛", "💚", "💙", "💜", "❤️‍🩹", "❓"):
    return
  pseudonym = reply.split("\n")[0][2:]
  user = chat_users.get_user_by_pseudonym(pseudonym)
  if user is None:
    bot.send_message(CHAT, "Этого пользователя уже не существует.")
    return
  text = message.text.format(name=user.name)
  safe_send_message(user.id, text)
  return


@bot.message_handler(
  content_types=["new_chat_members"], func=lambda message: message.chat.id == CHAT
)
def new_operator(message: types.Message):
  assert message.new_chat_members is not None
  for user in message.new_chat_members:
    lang = poll_users.get_lang(user)
    # if add_achievement(user.id, "operator", RESPONSES_FOLDER + "/"):
    #   bot.send_message(user.id, achievement_message("operator", lang))
    bot.send_message(CHAT, service[lang]["new_operator"])


@bot.my_chat_member_handler()
def banned(update: types.ChatMemberUpdated):
  user = update.from_user.id
  if update.new_chat_member.status == "kicked":
    chat_users.delete_user(user)
    poll_users.rm_user(user)


def better_polling():
  global s
  while s:
    try:
      bot.infinity_polling()
    except Exception as e:
      bot.send_message(ADMIN, "{}".format(e))


if __name__ == "__main__":
  schedule.every().minute.at(":00").do(partial(poll_users.send_polls, bot))
  threading.Thread(
    target=better_polling, name="bot_infinity_polling", daemon=True
  ).start()
  # poll_users.forced_polls(bot)
  bot.delete_my_commands(scope=types.BotCommandScopeAllPrivateChats())
  loc_strings.setup_bot(bot)
  # for lan in ("ru", "en"):
  #   for uid in poll_users.users:
  #     bot.delete_my_commands(types.BotCommandScopeChat(uid), lan)
  #     loc_strings.setup_bot(bot, types.BotCommandScopeChat(uid))
  print("Начала работу")
  while s:
    schedule.run_pending()
    time.sleep(1)
