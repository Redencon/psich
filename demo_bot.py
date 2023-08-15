"""
Настенька
v. 0.1.1
"""

import os
import telebot
import json
import threading
import sys

# import typing  # just in case
import schedule
from telebot import types
import time
from gmail_send_message import send_code
import yaml
import random
import gpt_users
import responses
from achievements import add_achievement
from achievements import streak_achievement
from achievements import average_consistency_achievement
from achievements import timestamp
from achievements import achievement_message
from requests.exceptions import ConnectionError, HTTPError
from telebot.apihelper import ApiException
import statusClasses

SECRET_FILE = sys.argv[1]
# TIMES = ("08:15", "12:10", "15:20", "20:00")

with open(SECRET_FILE, "r", encoding="utf-8") as f:
    secret = json.load(f)

TOKEN = secret["TOKEN"]
if len(sys.argv) > 2:
    TOKEN = sys.argv[2]
ADMIN = secret["ADMIN"]
ARBITRARY_THRESHOLD = secret["ARBITRARY_THRESHOLD"]
CHAT = secret["CHAT"]
RESPONSES_FOLDER = secret["RESPONSES_FOLDER"]
# STATUS_FILE = secret["STATUS_FILE"]
POOL_FILE = secret["POOL_FILE"]
TRACK_FILE = secret["TRACK_FILE"]
# GENERAL_FILE = secret["GENERAL_FILE"]
# PENDING_FILE = secret["PENDING_FILE"]
# BLACKLIST_FILE = secret["BLACKLIST_FILE"]
START_FILE = secret["START_FILE"]
LOC_FILE = secret["LOC_FILE"]
DOMEN = secret["DOMEN"]
s = True

TextPack = dict[str, dict[str, str]]

with open(LOC_FILE, "r", encoding="utf-8") as file:
    all_text = yaml.safe_load(file)
    service: TextPack = {key: all_text[key]["service"] for key in all_text}
    commands: TextPack = {key: all_text[key]["commands"] for key in all_text}
    respons_texts: TextPack = {key: all_text[key]["responses"] for key in all_text}
    achievements_d: TextPack = {key: all_text[key]["achievements"] for key in all_text}
    help_d: TextPack = {key: all_text[key]["help"] for key in all_text}
    description: TextPack = {
        key: all_text[key]["description"][(0 if TOKEN[0] == "5" else 1)]
        for key in all_text
    }
    short_description: TextPack = {
        key: all_text[key]["short_description"] for key in all_text
    }
    del all_text


bot = telebot.TeleBot(TOKEN)

chat_users = gpt_users.UserManager()
poll_users = responses.UserManager(TRACK_FILE, RESPONSES_FOLDER, chat_users)

# gens = statusClasses.GeneralData(GENERAL_FILE, bot, ADMIN)
# pend = statusClasses.Pending_users(PENDING_FILE)
# blkl = statusClasses.Blacklist(BLACKLIST_FILE)


class UsefulStrings:
    def __init__(self) -> None:
        raise NotImplementedError("No object if this class should be created")

    colorcoding = ["🟥", "🟧", "🟨", "🟩", "🟦", "🟪", "🟫", "⬜"]
    hearts = {
        "mood": ["❤️", "🧡", "💛", "💚", "💙", "💜", "❤️‍🩹"],
        "health": ["🔴", "🟠", "🟡", "🟢", "🔵", "🟣", "🟤"],
    }
    poll_types = {"mood": "🌠", "health": "💊", "FINCHY": "🐺"}
    poll_list = ["mood", "health"]
    


def get_help():
    with open("help.json", encoding="utf-8") as file:
        help_db = json.load(file)
    return help_db


def days_in_month(month, year):
    if month == 2:
        if year % 4 == 0:
            return 29
        return 28
    if month in (1, 3, 5, 7, 8, 10, 12):
        return 31
    return 30


def convivnient_slicer(li):
    ret = [[]]
    for elem in li:
        if len(ret[-1]) == 3:
            ret.append([])
        ret[-1].append(elem)
    return ret


def is_late(ref: str) -> bool:
    now = time.localtime()
    ref_hrs = int(ref[:2])
    ref_mns = int(ref[3:])
    if now.tm_hour < ref_hrs:
        return False
    if now.tm_hour == ref_hrs:
        if now.tm_min <= ref_mns:
            return False
    return True


def dab_upd(filename, user_id, argument=None, **kwargs):
    """Open the specified dab file and change it"""
    with open(filename) as file:
        dab = {int(key): val for key, val in json.load(file).items()}
    if user_id not in dab.keys() and kwargs:
        dab[user_id] = {}
    dab[user_id] = argument
    with open(filename, "w") as file:
        json.dump(dab, file)
    return


# def new_response(user_id, key, answer):
#     try:
#         with open(RESPONSES_FOLDER + "/" + str(user_id) + ".json") as file:
#             user_db = json.load(file)
#     except FileNotFoundError:
#         return False
#     if key in user_db["responses"].keys():
#         return False
#     user_db["responses"][key] = answer
#     with open(RESPONSES_FOLDER + "/" + str(user_id) + ".json", "w") as file:
#         json.dump(user_db, file)
#     return True


def dem_response(user_id, key, answer):
    user = poll_users.users[user_id]
    if "demog" not in user.meta:
        user.meta["demog"] = {}
    user.meta["demog"].update({key: answer})
    poll_users.dump_user(user_id)


def poll(user_id, tpe: str = "mood", lang="ru"):
    hearts = UsefulStrings.hearts
    if lang is None: lang = "en"
    text = f'{timestamp()}\n{service[lang]["poll"][tpe]}'
    markup = types.InlineKeyboardMarkup(
        [
            [
                types.InlineKeyboardButton(
                    hearts[tpe][i], callback_data=f"DS_{tpe[0]}_{i}"
                )
                for i in range(7)
            ]
        ]
    )
    try:
        bot.send_message(user_id, text, reply_markup=markup)
        poll_users.users[user_id].lastday.register_poll(tpe)
    except ApiException:
        poll_users.users[user_id].polls = []
        # dab_upd(STATUS_FILE, user_id, None)


def send_polls():
    for user_id, tpe in poll_users.needed_polls_stack():
        poll(user_id, tpe, poll_users.users[user_id].meta.get("lang", "ru"))


def wanna_get(message: types.Message):
    lang = get_lang(message.from_user)
    bot.send_message(
        message.chat.id,
        service[lang]["wanna_get"],
        reply_markup=types.InlineKeyboardMarkup(
            [
                [
                    types.InlineKeyboardButton(
                        ("Yes" if lang == "en" else "Да"), callback_data="ST_y"
                    ),
                    types.InlineKeyboardButton(
                        ("No" if lang == "en" else "Нет"), callback_data="ST_n"
                    ),
                ]
            ]
        ),
    )
    return


def get_lang(user: types.User):
    """Get the language code for chosen User instance"""
    if user.id not in poll_users.users:
        if user.language_code in ("ru", "en"):
            return user.language_code
        else:
            return "en"
    poll_user = poll_users.users[user.id]
    if "lang" not in poll_user.meta:
        if user.language_code in ("ru", "en"):
            poll_user.meta["lang"] = user.language_code
        else:
            poll_user.meta["lang"] = "en"
        poll_users.dump_user(user.id)
    return poll_user.meta["lang"]


def demog_init(user_id: int, lang: str, chat_id: int = None, message_id: int = None):
    """Send the first message of demography poll.

    Provide chat and message id to edit a previous message into it instead
    """
    with open(POOL_FILE) as file:
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
        try:
            lang = get_lang(message.from_user)
            poll_user = poll_users.users.get(message.from_user.id)
            if (
                poll_user
                and "demog" in poll_user.meta
                and "lgbt" in poll_user.meta["demog"]
            ):
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


@bot.message_handler(
    commands=["update"], func=lambda message: message.from_user.id == ADMIN
)
def update(_: types.Message):
    import sys
    import subprocess

    subprocess.Popen(START_FILE, creationflags=subprocess.CREATE_NEW_CONSOLE)
    global s
    s = False
    sys.exit()


@bot.message_handler(commands=["start"])
def start(message: types.Message):
    if message.from_user.id not in poll_users.users:
        lang = get_lang(message.from_user)
        poll_user = poll_users.new_user(
            message.from_user.id,
            message.from_user.username,
            message.from_user.first_name,
        )

        if DOMEN is not None:
            bot.send_message(message.chat.id, service[lang]["verification"])
            poll_user.meta["verified"] = False
            poll_user.meta["code"] = None
            poll_users.dump_user(message.from_user.id)
        else:
            wanna_get(message)
    else:
        # Start is equal to /help when user is not new
        lang = get_lang(message.from_user)
        bot.reply_to(message, help_d[lang]["help"])
    return


@bot.message_handler(["help"])
def help(message: types.Message):
    lang = get_lang(message.from_user)
    # help_db = get_help()
    argv = message.text.split()
    if len(argv) == 1:
        cmd = "help"
    else:
        cmd = argv[1]
    if cmd not in help_d[lang].keys():
        bot.reply_to(message, service[lang]["help_fail"])
        return
    bot.reply_to(message, help_d[lang][cmd])
    return


@bot.callback_query_handler(lambda call: call.data[:3] == "ST_")
def start_response(call: types.CallbackQuery):
    lang = get_lang(call.from_user)
    bot.answer_callback_query(call.id, service[lang]["thanks"])
    bot.edit_message_text(
        service[lang]["thanks"], call.message.chat.id, call.message.id
    )
    if call.from_user.id not in poll_users.users:
        bot.send_message(call.from_user.id, service[lang]["must_register"])
        return
    poll_user = poll_users.users[call.from_user.id]
    if call.data[-1] == "y":
        if "demog" not in poll_user.meta or "lgbt" not in poll_user.meta["demog"]:
            demog_init(call.from_user.id, lang)
            return
        send_time(call.from_user.id, lang)
        return
    if call.data[-1] == "n":
        poll_user.polls = []


@bot.callback_query_handler(lambda call: call.data[:3] == "DS_")
def parse_survey(call: types.CallbackQuery):
    lang = get_lang(call.from_user)
    hearts = UsefulStrings.hearts
    tpe = dict(h="health", m="mood")[call.data[-3]]
    answer = int(call.data[-1])
    text = call.message.text.split("\n")
    bot.answer_callback_query(
        call.id, service[lang]["poll_answer"].format(answer=hearts[tpe][answer])
    )
    poll_users.new_response(call.from_user.id, tpe, answer)
    bot.edit_message_text(
        "\n".join(text)
        + "\n"
        + service[lang]["poll_answer"].format(answer=hearts[tpe][answer]),
        call.message.chat.id,
        call.message.id,
        reply_markup=None,
    )
    bot.send_message(call.message.chat.id, random.choice(respons_texts[lang][answer]))
    # for i in (3, 7, 14, 30, 61, 150):
    #     a = streak_achievement(call.from_user.id, i, RESPONSES_FOLDER + "/")
    #     if a is not None:
    #         if a:
    #             bot.send_message(
    #                 call.message.chat.id, achievement_message("streak_" + str(i), lang)
    #             )
    #         else:
    #             break
    # for i in (15, 30):
    #     a = average_consistency_achievement(call.from_user.id, i)
    #     if a:
    #         bot.send_message(
    #             call.message.chat.id, achievement_message("consistency_" + str(i), lang)
    #         )
    # # TODO: add experience system, see #11
    return


@bot.message_handler(commands=["unsub", "sub"])
@registered_only
def unsub(message):
    wanna_get(message)
    return


@bot.callback_query_handler(lambda call: call.data[:3] == "DG_")
def demogr(call: types.CallbackQuery):
    lang = get_lang(call.from_user)
    bot.answer_callback_query(call.id)
    with open(POOL_FILE) as file:
        questions = json.load(file)
    cur = int(call.data[3])
    ans = int(call.data[4:])
    dem_response(
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
        #     poll(call.from_user.id, lang)
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


def calendar(user_id, month, year, tpe="mood"):
    user_calendar = poll_users.users[user_id].calendar(tpe)
    stamp = time.mktime((year, month, 1, 0, 0, 0, 0, 0, -1))
    time_struct = time.localtime(stamp)
    grey = (time_struct.tm_wday - 1 + 1) % 7
    month = [
        time.strftime(
            responses.DATE_FORMAT, time.struct_time((year, month, i, 1, 0, 0, 0, 0, 0, -1))
        )
        for i in range(1, days_in_month(month, year) + 1)
    ]
    stat = [user_calendar[i] if i in user_calendar else 7 for i in month]
    text = [["⚫"] * grey]
    for s in stat:
        if len(text[-1]) == 7:
            text.append([])
        text[-1].append(UsefulStrings.colorcoding[s])
    text[-1] += ["⚫"] * (7 - len(text[-1]))
    text = "\n".join(["".join(a) for a in text])
    return text


def today(tpe, user_id, lang):
    hearts = UsefulStrings.hearts
    if poll_users.agg_today(tpe) < 3:
        bot.send_message(user_id, service[lang]["today_fail"])
        return
    bot.send_message(
        user_id,
        service[lang]["today_text"].format(tpe, hearts[tpe][poll_users.agg_today(tpe)]),
    )
    return


def update_admin(tpe):
    hearts = UsefulStrings.hearts
    tpe_data = [
        (
            tpe,
            poll_users.tracker.types_data[tpe].count,
            poll_users.tracker.types_data[tpe].total,
        )
        for tpe in poll_users.tracker.types_data
    ]
    text = "\n".join(
        list(
            time.strftime(responses.DATE_FORMAT),
            *[
                "\n".join(
                    "Статистика по {}:".format(tpe),
                    "Ответов: {}, Среднее: {}".format(
                        cnt, UsefulStrings.hearts[tpe][round(ttl / cnt)]
                    ),
                )
                for tpe, cnt, ttl in tpe_data
            ],
        )
    )
    if (
        not poll_users.tracker.tr_messages
        or poll_users.tracker.tr_messages[0].chat_id != ADMIN
    ):
        message = bot.send_message(ADMIN, text)
        poll_users.tracker.tr_messages.insert(
            0, responses.TrackingMessage(ADMIN, message.id, "ADMIN", message.text)
        )
        poll_users.dump_tracker()
        return
    if poll_users.tracker.tr_messages[0].current_txt == text:
        return
    try:
        bot.edit_message_text(text, ADMIN, poll_users.tracker.tr_messages[0].message_id)
    except telebot.apihelper.ApiTelegramException:
        message = bot.send_message(ADMIN, text)
        poll_users.tracker.tr_messages.insert(
            0, responses.TrackingMessage(ADMIN, message.id, "ADMIN", message.text)
        )
        poll_users.dump_tracker()
    for tracker in poll_users.tracker.tr_messages:
        if tracker.tpe != tpe:
            continue
        if text == tracker.current_txt:
            continue
        a = poll_users.users.get(tracker.chat_id, None)
        if a is None:
            lang = "en"
        else:
            lang = a.meta.get("lang", "en")
        try:
            bot.edit_message_text(
                service[lang]["today_text"].format(
                    tpe,
                    hearts[tpe][poll_users.tracker.types_data[tpe].average()],
                ),
                tracker.chat_id,
                tracker.message_id,
            )
        except telebot.apihelper.ApiTelegramException:
            print("It failed. Again :<")
    return


@bot.message_handler(commands=["stats"])
@registered_only
def stats(message: types.Message):
    lang = get_lang(message.from_user)
    curyear = time.localtime()[0]
    curmonth = time.localtime()[1]
    argv = message.text.split()[1:]
    if len(argv) > 0:
        if argv[0].isdigit():
            curmonth = int(argv[0])
            if curmonth > time.localtime()[1]:
                curyear -= 1
    user = message.from_user.id
    # if add_achievement(message.from_user.id, "stats", RESPONSES_FOLDER + "/"):
    #     bot.send_message(message.chat.id, achievement_message("stats", lang))
    bot.send_message(
        message.chat.id,
        "{0} {1}/{2}:\n{3}".format(
            service[lang]["stats"],
            str(curmonth),
            str(curyear),
            calendar(user, curmonth, curyear, UsefulStrings.poll_list[0]),
        ),
        reply_markup=types.InlineKeyboardMarkup(
            [
                [
                    types.InlineKeyboardButton("◀️", callback_data="SS_-"),
                    types.InlineKeyboardButton(UsefulStrings.poll_types[UsefulStrings.poll_list[0]], callback_data="SS_0"),
                    types.InlineKeyboardButton("▶️", callback_data="SS_+"),
                ]
            ]
        ),
    )
    return


@bot.callback_query_handler(lambda call: call.data[:3] == "SS_")
def switch_calendar(call: types.CallbackQuery):
    lang = get_lang(call.from_user)
    data = call.data[-1]
    i = int(call.message.reply_markup.keyboard[0][1].callback_data[3:]) % len(UsefulStrings.poll_list)
    month, year = map(int, call.message.text.split("\n")[0].split()[-1][:-1].split("/"))
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
    else:
        i = (i+1) % len(UsefulStrings.poll_list)
        call.message.reply_markup.keyboard[0][1].callback_data = 'SS_{}'.format(i)
    tpe = UsefulStrings.poll_list[i]
    call.message.reply_markup.keyboard[0][1].text = UsefulStrings.poll_types[tpe]
    bot.edit_message_text(
        "{stats} {month}/{year}:\n{calendar}".format(
            stats=service[lang]["stats"],
            month=month,
            year=year,
            calendar=calendar(call.from_user.id, month, year, tpe),
        ),
        call.message.chat.id,
        call.message.id,
        reply_markup=call.message.reply_markup,
    )
    bot.answer_callback_query(call.id, service[lang]["stats_next"])


@bot.message_handler(commands=["delete"])
def delete(message):
    lang = get_lang(message.from_user)
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
    lang = get_lang(message.from_user)
    # if add_achievement(message.from_user.id, "today", RESPONSES_FOLDER + "/"):
    #     bot.send_message(message.chat.id, achievement_message("today", lang))
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
    lang = get_lang(call.from_user)
    tpe = call.data[3:]
    bot.answer_callback_query(call.id)
    if tpe == "none":
        bot.edit_message_reply_markup(
            call.message.chat.id, call.message.id, reply_markup=None
        )
        return
    if tpe not in poll_users.tracker.types_data:
        text = service[lang]['today_fail']
        bot.edit_message_text(
            text, call.message.chat.id, call.message.id, reply_markup=None
        )
        return
    avg = poll_users.tracker.types_data[tpe].average()
    if avg:
        text = service[lang]["today_text"].format(
            tpe,
            UsefulStrings.hearts[tpe][avg],
        )
        poll_users.tracker.tr_messages.append(
            responses.TrackingMessage(call.message.chat.id, call.message.id, tpe, text)
        )
        poll_users.dump_tracker()
    else:
        text = service[lang]['today_fail']
    bot.edit_message_text(
        text, call.message.chat.id, call.message.id, reply_markup=None
    )


@bot.callback_query_handler(lambda call: call.data[:3] == "CL_")
def wipe(call: types.CallbackQuery):
    lang = get_lang(call.from_user)
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
    if message.text[0] == "/":
        return False
    if DOMEN is None:
        return False
    if message.from_user.id not in poll_users.users:
        return False
    return not poll_users.users[message.from_user.id].meta["verified"]


@bot.message_handler(func=email_is_awaited)
def email(message: types.Message):
    lang = get_lang(message.from_user)
    response = message.text
    user_meta = poll_users.users[message.from_user.id].meta
    if response.isdigit():
        if user_meta["code"] is not None:
            if int(response) == user_meta["code"]:
                bot.send_message(message.chat.id, service[lang]["success"])
                user_meta["verified"] = True
                poll_users.dump_user(message.from_user.id)
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
                "Токен GMail сгорел. Обнови. Его хотели использовать\n{}".format(e),
            )
            bot.send_message(message.chat.id, service[lang]["registration_closed"])
        if code is None:
            bot.send_message(message.chat.id, service[lang]["email_wrong_adress"])
            return
        if code == -1:
            bot.send_message(message.chat.id, service[lang]["email_wrong_domen"])
            return
        print(code)
        poll_users.users[message.from_user.id].meta["code"] = code
        poll_users.dump_user(message.from_user.id)
        bot.send_message(message.chat.id, service[lang]["email_sent"])
        return


def default_time_keyboard():
    ikb = types.InlineKeyboardButton
    return types.InlineKeyboardMarkup(
        [
            [
                ikb("+6h", None, "TP_+6h"),
                ikb("+1h", None, "TP_+1h"),
                ikb("✅", None, "TP_done"),
                ikb("+5m", None, "TP_+5m"),
                ikb("+15m", None, "TP_+15m"),
            ],
            [
                ikb("🔁", None, "TP_default"),
                ikb("12", None, "TP_none"),
                ikb(":", None, "TP_none"),
                ikb("10", None, "TP_none"),
                ikb("🌠", None, "TP_type"),
            ],
            [
                ikb("-6h", None, "TP_-6h"),
                ikb("-1h", None, "TP_-1h"),
                ikb("❎", None, "TP_cancel"),
                ikb("-5m", None, "TP_-5m"),
                ikb("-15m", None, "TP_-15m"),
            ],
        ]
    )


def send_time_picker(user_id: int, lang: str = "en"):
    keyboard = default_time_keyboard()
    bot.send_message(user_id, service[lang]["time_choose"], reply_markup=keyboard)


@bot.callback_query_handler(lambda call: call.data[:3] == "TP_")
def time_picker_handler(call: types.CallbackQuery):
    data = call.data[3:]
    lang = get_lang(call.from_user)
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
        rtm = {value: key for key, value in type_map.items()}
        new_type = rtm["mood" if type_map[current_type] == "health" else "health"]
        keyboard[1][4].text = new_type
        bot.answer_callback_query(
            call.id, service[lang]["type_change"].format(new_type)
        )
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
        bot.edit_message_reply_markup(
            call.message.chat.id, call.message.id, reply_markup=default_time_keyboard()
        )
        return
    if data == "done":
        bot.answer_callback_query(call.id)
        bot.edit_message_text(
            service[lang]["ok"],
            call.message.chat.id, call.message.id
        )
        actual_current_type = type_map[current_type]
        h = keyboard[1][1].text
        m = keyboard[1][3].text
        poll_users.users[call.from_user.id].add_poll(
            "{}:{}".format(h, m), actual_current_type
        )
        if poll_users.users[call.from_user.id].is_poll_needed(actual_current_type):
            poll(call.from_user.id, actual_current_type, lang)
        poll_users.dump_user(call.from_user.id)


def send_time(uid: int, lang: str):
    bot.send_message(
        uid,
        service[lang]["type_choice"],
        reply_markup=types.InlineKeyboardMarkup(
            [
                [
                    types.InlineKeyboardButton("🌠", callback_data="PC_mood"),
                    types.InlineKeyboardButton("💊", callback_data="PC_health"),
                    types.InlineKeyboardButton("🔴", callback_data="PC_cancel"),
                    types.InlineKeyboardButton("❎", callback_data="PC_none"),
                ]
            ]
        ),
    )


@bot.message_handler(commands=["time"])
@registered_only
def time_present(message: types.Message):
    lang = get_lang(message.from_user)
    send_time(message.from_user.id, lang)
    return


def polls_keyboard(uid: int):
    polls = poll_users.users[uid].polls
    keyboard = [
        [
            types.InlineKeyboardButton(
                "{} - {}".format(poll.time, poll.type), callback_data="PD_{}".format(i)
            )
        ]
        for i, poll in enumerate(polls)
    ]
    keyboard.append([types.InlineKeyboardButton("❎", callback_data="PD_none")])
    return keyboard


@bot.callback_query_handler(lambda call: call.data[:3] == "PC_")
def poll_choose(call: types.CallbackQuery):
    bot.answer_callback_query(call.id)
    lang = get_lang(call.from_user)
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
        service[lang]["time_kb"],
        call.message.chat.id,
        call.message.id,
        reply_markup=markup,
    )


@bot.callback_query_handler(lambda call: call.data[:3] == "PD_")
def time_remove(call: types.CallbackQuery):
    lang = get_lang(call.from_user)
    bot.answer_callback_query(call.id)
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
    poll_users.users[uid].polls.pop(int(i))
    poll_users.dump_user(uid)
    bot.edit_message_reply_markup(
        call.message.chat.id, call.message.id, reply_markup=types.InlineKeyboardMarkup(polls_keyboard(uid))
    )


# @bot.message_handler(commands=["achievements"])
# @registered_only
# def achievements(message: types.Message):
#     lang = get_lang(message.from_user)
#     with open(
#         RESPONSES_FOLDER + "/" + str(message.from_user.id) + ".json",
#         "r",
#         encoding="utf-8",
#     ) as f:
#         data = json.load(f)
#     if "achievements" not in data.keys():
#         data["achievements"] = []
#         with open(
#             RESPONSES_FOLDER + "/" + str(message.from_user.id) + ".json",
#             "w",
#             encoding="utf-8",
#         ) as f:
#             json.dump(data, f)
#     bot.send_message(
#         message.chat.id,
#         "{init}:\n{achievements}".format(
#             init=service[lang]["achievements"],
#             achievements="\n\n".join(
#                 [
#                     "✨{name}:\n{description}".format(
#                         name=achievements_d[lang][name]["name"],
#                         description=achievements_d[lang][name]["description"],
#                     )
#                     for name in data["achievements"]
#                 ]
#             ),
#         ),
# )


# @bot.message_handler(
#     commands=["thanks"],
#     func=lambda message: message.chat.id == CHAT
#     and message.reply_to_message is not None,
# )
# def thanks(message: types.Message):
#     pseudonym = message.reply_to_message.text.split("\n")[0][2:]
#     if add_achievement(
#         chat_users.get_user_by_pseudonym(pseudonym).id,
#         "good_conversation",
#         RESPONSES_FOLDER + "/",
#     ):
#         bot.send_message(
#             chat_users.get_user_by_pseudonym(pseudonym).id,
#             achievement_message("good_conversation"),
#         )


# @bot.message_handler(commands=["grant"], func=lambda message: message.chat.id == ADMIN)
# def grant(message: types.Message):
#     text = message.text.split()[1:]
#     with open("achievements.json", "r", encoding="utf-8") as f:
#         gen_data = json.load(f)
#     if len(text) < 2:
#         return
#     if not text[0].isdigit():
#         return
#     if text[1] not in gen_data.keys():
#         return
#     user = int(text[0])
#     if add_achievement(user, text[1], RESPONSES_FOLDER + "/"):
#         bot.send_message(user, achievement_message(text[1]))
#         bot.send_message(ADMIN, "Добавила достижение.")


@bot.message_handler(["checkuser"], func=lambda message: message.from_user.id == ADMIN)
def checkuser(message):
    entities = message.entities
    buffer = ""
    for entity in entities:
        buffer += entity.type
        buffer += " " + str(entity.user.id) if entity.user is not None else "None"
        buffer += "\n"
    bot.reply_to(message, buffer)


@bot.message_handler(["run"], func=lambda message: message.from_user.id == ADMIN)
def run(message):
    forced_polls()
    bot.reply_to(message, "Отправила опросы.")
    return


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


@bot.callback_query_handler(func=lambda call: call.data[:3] == "LG_")
def language_choice(call: types.CallbackQuery):
    poll_users.users[call.from_user.id].meta["lang"] = call.data[3:]
    poll_users.dump_user(call.from_user.id)
    bot.answer_callback_query(call.id, call.data[3:])
    bot.edit_message_text(
        service[call.data[3:]]["language"], call.message.chat.id, call.message.id
    )


@bot.message_handler(["report"], func=lambda m: m.chat.id == ADMIN)
def send_report(_):
    from report import make_report

    a = make_report(poll_users)
    with open(a, "rb") as file:
        bot.send_document(ADMIN, file, caption="Report for " + timestamp())
    os.remove(a)
    return


@bot.message_handler(["demog"])
def demog_manual(message: types.Message):
    lang = get_lang(message.from_user)
    demog_init(message.from_user.id, lang)
    poll_users.users[message.from_user.id].meta["demog"] = {}
    poll_users.dump_user(message.from_user.id)


@bot.message_handler(["forcedemog"], func=lambda m: m.from_user.id == ADMIN)
def force_demog(_: types.Message):
    for uid, user in poll_users.users.items():
        demog_init(uid, user.meta.get("lang", "en"))
        user.meta["demog"] = {}
        poll_users.dump_user(uid)
    bot.send_message(ADMIN, "Sent renewed demog polls")


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
    text = message.text
    hearts = ["❤️", "🧡", "💛", "💚", "💙", "💜", "❤️‍🩹"]
    user = chat_users.get_user_by_id(message.from_user.id)
    if user is None:
        user = chat_users.new_user(message.from_user.id, message.from_user.first_name)
    user.last_personal_message = message.id
    if poll_users.users[user.id].days[-1].date == time.strftime(responses.DATE_FORMAT):
        status = hearts[poll_users.users[user.id].days[-1].responses[-1].score]
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
    for user in message.new_chat_members:
        lang = get_lang(user)
        # if add_achievement(user.id, "operator", RESPONSES_FOLDER + "/"):
        #     bot.send_message(user.id, achievement_message("operator", lang))
        bot.send_message(CHAT, service[lang]["new_operator"])


@bot.my_chat_member_handler()
def banned(update: types.ChatMemberUpdated):
    user = update.from_user.id
    if update.new_chat_member.status == "kicked":
        chat_users.delete_user(user)
        poll_users.rm_user(user)


def forced_polls():
    for uid, tpe in poll_users.needed_polls_stack():
        poll(uid, tpe, poll_users.users[uid].meta.get("lang", "ru"))


def set_commands(scope=types.BotCommandScopeDefault):
    for lang in ("ru", "en"):
        bot.delete_my_commands(scope=scope, language_code=lang)
        bot.set_my_commands(
            [types.BotCommand(name, commands[lang][name]) for name in commands[lang]],
            scope=scope,
            language_code=lang,
        )
    return


if __name__ == "__main__":
    schedule.every(5).minutes.do(send_polls)
    threading.Thread(
        target=bot.infinity_polling, name="bot_infinity_polling", daemon=True
    ).start()
    forced_polls()
    set_commands(types.BotCommandScope())
    bot.delete_my_commands(scope=types.BotCommandScopeAllPrivateChats())
    for lan in ("ru", "en"):
        bot.set_my_description(description[lan], language_code=lan)
        bot.set_my_short_description(short_description[lan], language_code=lan)
    del description
    del short_description
    print("Начала работу")
    while s:
        schedule.run_pending()
        time.sleep(1)
