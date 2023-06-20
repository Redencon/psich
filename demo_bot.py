'''
Настенька
v. 0.1.1
'''

import os
import telebot
import json
import threading
import sys
import typing  # just in case
import schedule
from telebot import types
import time
from gmail_send_message import send_code
import yaml
import random
import gpt_users
from achievements import add_achievement
from achievements import streak_achievement
from achievements import average_consistency_achievement
from achievements import timestamp
from achievements import achievement_message
from requests.exceptions import ConnectionError
import statusClasses

SECRET_FILE = sys.argv[1]
TIMES = ('08:15', '12:10', '15:20', '20:00')

with open(SECRET_FILE, 'r', encoding='utf-8') as f:
    secret = json.load(f)

TOKEN = secret['TOKEN']
if len(sys.argv) > 2:
    TOKEN = sys.argv[2]
ADMIN = secret['ADMIN']
ARBITRARY_THRESHOLD = secret['ARBITRARY_THRESHOLD']
CHAT = secret['CHAT']
RESPONSES_FOLDER = secret['RESPONSES_FOLDER']
STATUS_FILE = secret['STATUS_FILE']
POOL_FILE = secret['POOL_FILE']
GENERAL_FILE = secret['GENERAL_FILE']
PENDING_FILE = secret['PENDING_FILE']
BLACKLIST_FILE = secret['BLACKLIST_FILE']
START_FILE = secret['START_FILE']
LOC_FILE = secret['LOC_FILE']
DOMEN = secret['DOMEN']
S = True

with open(LOC_FILE, 'r', encoding='utf-8') as file:
    all_text = yaml.safe_load(file)
    service = {key: all_text[key]['service'] for key in all_text}
    commands = {key: all_text[key]['commands'] for key in all_text}
    responses = {key: all_text[key]['responses'] for key in all_text}
    achievements_d = {key: all_text[key]['achievements'] for key in all_text}
    help_d = {key: all_text[key]['help'] for key in all_text}
    description = {key: all_text[key]['description'][
        (0 if TOKEN[0] == '5' else 1)
        ] for key in all_text}
    short_description = {key: all_text[key]['short_description'] for key in all_text}
    del all_text


bot = telebot.TeleBot(TOKEN)

chat_users = gpt_users.UserManager()

gens = statusClasses.GeneralData(GENERAL_FILE, bot, ADMIN)
pend = statusClasses.Pending_users(PENDING_FILE)
blkl = statusClasses.Blacklist(BLACKLIST_FILE)

colorcoding = [
    '🟥',
    '🟧',
    '🟨',
    '🟩',
    '🟦',
    '🟪',
    '🟫',
    '⬜'
]


def get_help():
    with open('help.json', encoding='utf-8') as file:
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
    '''Open the specified dab file and change it'''
    with open(filename) as file:
        dab = {int(key): val for key, val in json.load(file).items()}
    if user_id not in dab.keys() and kwargs:
        dab[user_id] = {}
    dab[user_id] = argument
    with open(filename, 'w') as file:
        json.dump(dab, file)
    return


def new_response(user_id, key, answer):
    try:
        with open(RESPONSES_FOLDER+'/'+str(user_id)+'.json') as file:
            user_db = json.load(file)
    except FileNotFoundError:
        return False
    if key in user_db['responses'].keys():
        return False
    user_db['responses'][key] = answer
    with open(RESPONSES_FOLDER+'/'+str(user_id)+'.json', 'w') as file:
        json.dump(user_db, file)
    return True


def dem_response(user_id, key, answer):
    with open(RESPONSES_FOLDER + '/'+str(user_id)+'.json') as file:
        user_db = json.load(file)
    user_db['demog'][key] = answer
    with open(RESPONSES_FOLDER+'/'+str(user_id)+'.json', 'w') as file:
        json.dump(user_db, file)
    return


def poll(user_id, lang='ru'):
    hearts = ['❤️', '🧡', '💛', '💚', '💙', '💜', '❤️‍🩹']
    text = timestamp()+'\n'+service[lang]['poll']
    markup = types.InlineKeyboardMarkup([
        [types.InlineKeyboardButton(hearts[i], callback_data='DS_'+str(i))
         for i in range(7)]])
    try:
        bot.send_message(user_id, text, reply_markup=markup)
    except:
        dab_upd(STATUS_FILE, user_id, None)


def send_poll(time):
    with open(STATUS_FILE) as file:
        users = json.load(file)
        users = {int(user_id): value for user_id, value in users.items()}
    last_today = time == TIMES[-1]
    if time == TIMES[0]:
        gens.new_day(timestamp())
        blkl.clear()
        blkl.add(timestamp())
    for user_id in users:
        if users[user_id] is not None:
            try:
                with open(RESPONSES_FOLDER+'/'+str(user_id)+'.json', 'r', encoding='utf-8') as f:
                    user_data = json.load(f)
            except FileNotFoundError:
                dab_upd(STATUS_FILE, user_id, None)
            if 'lang' not in user_data:
                lang = 'ru'
            else:
                lang = user_data['lang']
            if users[user_id] == time and user_id not in blkl.dab:
                poll(user_id, lang)
                blkl.add(user_id)
            if last_today and users[user_id] != time:
                if timestamp() not in user_data['responses'].keys():
                    try:
                        bot.send_message(user_id, service[lang]['reminder'])
                    except:
                        dab_upd(STATUS_FILE, user_id, None)
    return


def wanna_get(message: types.Message):
    lang = get_lang(message.from_user)
    bot.send_message(
        message.chat.id,
        service[lang]['wanna_get'],
        reply_markup=types.InlineKeyboardMarkup([[
            types.InlineKeyboardButton('Да', callback_data='ST_y'),
            types.InlineKeyboardButton('Нет', callback_data='ST_n')
        ]])
    )
    return


def get_lang(user: types.User):
    '''Get the language code for chosen User instance'''
    try:
        with open(RESPONSES_FOLDER+'/'+str(user.id)+'.json', 'r') as file:
            user_db = json.load(file)
    except FileNotFoundError:
        return user.language_code
    if 'lang' not in user_db.keys():
        if user.language_code in ('ru', 'en'):
            user_db['lang'] = user.language_code
        else:
            user_db['lang'] = 'en'
        with open(RESPONSES_FOLDER+'/'+str(user.id)+'.json', 'w') as file:
            json.dump(user_db, file)
    return user_db['lang']


def registered_only(func):
    def new_func(message: types.Message):
        try:
            lang = get_lang(message.from_user)
            with open(RESPONSES_FOLDER+'/'+str(message.from_user.id)+'.json') as file:
                user_db = json.load(file)
            if 'lgbt' in user_db['demog']:
                return func(message)
            else:
                bot.send_message(
                    message.chat.id,
                    service[lang]['must_register']
                )
        except:
            bot.send_message(
                    message.chat.id,
                    service[lang]['must_register']
                )
    return new_func


@bot.message_handler(commands=['setchat'], func=lambda message: message.from_user.id == ADMIN)
def setchat(message: types.Message):
    CHAT = message.chat.id
    secret['CHAT'] = CHAT
    with open(SECRET_FILE, 'w', encoding='utf-8') as f:
        json.dump(secret, f, ensure_ascii=False, indent=4)
    bot.send_message(CHAT, 'Использую этот чат как чат операторов.')
    return


@bot.message_handler(commands=['update'], func=lambda message: message.from_user.id == ADMIN)
def update(_: types.Message):
    import sys
    import subprocess
    subprocess.Popen(START_FILE, creationflags=subprocess.CREATE_NEW_CONSOLE)
    global S
    S = False
    sys.exit()


@bot.message_handler(commands=['start'])
def start(message: types.Message):
    with open(STATUS_FILE) as file:
        users = json.load(file)
    if str(message.from_user.id) not in users.keys():
        with open(RESPONSES_FOLDER+'/' + str(message.from_user.id) + '.json', 'w') as file:
            json.dump({'demog': {}, 'responses': {}, 'code': None}, file)
        lang = get_lang(message.from_user)
        if DOMEN is not None:
            bot.send_message(message.chat.id, service[lang]['verification'])
            pend.add_pending(message.from_user.id)
        else:
            dab_upd(STATUS_FILE, message.from_user.id, None)
            wanna_get(message)
    else:
        # Start is equal to /help when user is not new
        lang = get_lang(message.from_user)
        bot.reply_to(message, help_d[lang]['help'])
    return


@bot.message_handler(['help'])
def help(message: types.Message):
    lang = get_lang(message.from_user)
    # help_db = get_help()
    argv = message.text.split()
    if len(argv) == 1:
        cmd = 'help'
    else:
        cmd = argv[1]
    if cmd not in help_d[lang].keys():
        bot.reply_to(message, service[lang]['help_fail'])
        return
    bot.reply_to(message, help_d[lang][cmd])
    return


@bot.callback_query_handler(lambda call: call.data[:3] == 'ST_')
def start_response(call: types.CallbackQuery):
    lang = get_lang(call.from_user)
    bot.answer_callback_query(call.id, service[lang]['thanks'])
    bot.edit_message_text(service[lang]['thanks'], call.message.chat.id, call.message.id)
    try:
        with open(RESPONSES_FOLDER+'/'+str(call.from_user.id)+'.json') as file:
            user_db = json.load(file)
    except FileNotFoundError:
        bot.answer_callback_query(
            call.id,
            'No user data found, redo register',
            True
        )
    if call.data[-1] == 'n':
        if 'lgbt' in user_db['demog'].keys():
            dab_upd(STATUS_FILE, call.from_user.id, None)
        return
    if 'lgbt' in user_db['demog'].keys():
        with open(STATUS_FILE) as file:
            statuses = json.load(file)
        if statuses[str(call.from_user.id)] is None:
            time_present(call.message)
        return
    with open(POOL_FILE) as file:
        questions = json.load(file)
    options = questions[lang][0][2]
    bot.edit_message_text(
        service[lang]['demog_init']+'\n'+questions[lang][0][1],
        call.message.chat.id,
        call.message.id,
        reply_markup=types.InlineKeyboardMarkup([[
            types.InlineKeyboardButton(text, callback_data='DG_0'+str(i))
            for i, text in enumerate(options)]])
    )
    return


@bot.callback_query_handler(lambda call: call.data[:3] == 'DS_')
def parse_survey(call: types.CallbackQuery):
    lang = get_lang(call.from_user)
    hearts = ['❤️', '🧡', '💛', '💚', '💙', '💜', '❤️‍🩹']
    answer = int(call.data[-1])
    text = call.message.text.split('\n')
    if text[0] != timestamp():
        bot.answer_callback_query(call.id, service[lang]['poll_expired'])
        bot.edit_message_reply_markup(call.message.chat.id, call.message.id)
        return
    bot.answer_callback_query(call.id, service[lang]['poll_answer'].format(answer=hearts[answer]))
    if new_response(call.from_user.id, text[0], answer):
        gens.add_response(text[0], answer)
    bot.edit_message_text(
        '\n'.join(text)
        + '\n'+service[lang]['poll_answer'].format(answer=hearts[answer]),
        call.message.chat.id, call.message.id, reply_markup=None)
    bot.send_message(
        call.message.chat.id,
        random.choice(responses[lang][answer])
    )
    for i in (3, 7, 14, 30, 61, 150):
        a = streak_achievement(call.from_user.id, i, RESPONSES_FOLDER+'/')
        if a is not None:
            if a:
                bot.send_message(call.message.chat.id, achievement_message('streak_'+str(i), lang))
            else:
                break
    for i in (15, 30):
        a = average_consistency_achievement(call.from_user.id, i)
        if a:
            bot.send_message(call.message.chat.id, achievement_message('consistency_'+str(i), lang))
    # TODO: add experience system, see #11
    return


@bot.message_handler(commands=['unsub', 'sub'])
@registered_only
def unsub(message):
    wanna_get(message)
    return


@bot.callback_query_handler(lambda call: call.data[:3] == 'US_')
def unsub_check(call: types.CallbackQuery):
    lang = get_lang(call.from_user)
    if call.data[-1] == 'y':
        bot.answer_callback_query(call.id, service[lang]['unsub_no'])
        dab_upd(STATUS_FILE, call.from_user.id, TIMES[1])
        bot.edit_message_text(service[lang]['unsub_no'], call.message.chat.id, call.message.id)
    else:
        dab_upd(STATUS_FILE, call.from_user.id, None)
        bot.answer_callback_query(call.id, service[lang]['unsub_yes'])
        bot.edit_message_text(service[lang]['unsub_yes'], call.message.chat.id, call.message.id)
    return


@bot.callback_query_handler(lambda call: call.data[:3] == 'DG_')
def demogr(call: types.CallbackQuery):
    lang = get_lang(call.from_user)
    bot.answer_callback_query(call.id)
    with open(POOL_FILE) as file:
        questions = json.load(file)
    cur = int(call.data[3])
    ans = int(call.data[4:])
    dem_response(call.from_user.id, questions[lang][cur][0], questions[lang][cur][2][ans])
    cur += 1
    if cur >= len(questions[lang]):
        bot.edit_message_text(service[lang]['demog_end'], call.message.chat.id, call.message.id)
        time_present(call.message, lang)
        # dab_upd(STATUS_FILE, call.from_user.id, TIMES[1])
        bot.send_message(ADMIN, f'Новый пользователь: {call.from_user.full_name}')
        # if time.localtime()[3] > 12 or (time.localtime()[3] == 12 and time.localtime()[4] > 10):
        #     poll(call.from_user.id, lang)
        return
    else:
        bot.edit_message_text(
            service[lang]['demog_init']+'\n'+questions[lang][cur][1],
            call.message.chat.id,
            call.message.id,
            reply_markup=types.InlineKeyboardMarkup(
                convivnient_slicer([
                    types.InlineKeyboardButton(
                        text,
                        callback_data='DG_'+str(cur)+str(i)
                    )
                    for i, text
                    in enumerate(questions[lang][cur][2])]
                ),
                row_width=5
            )
        )
        return


def calendar(user_id, month, year):
    with open(RESPONSES_FOLDER+'/'+str(user_id)+'.json') as file:
        data = json.load(file)
    stamp = time.mktime((year, month, 1, 0, 0, 0, 0, 0, -1))
    time_struct = time.localtime(stamp)
    grey = (time_struct.tm_wday - 1 + 1) % 7
    month = [str(year)+'/'+str(month)+'/'+str(i) for i in range(1, days_in_month(month, year)+1)]
    stat = [data['responses'][i] if i in data['responses'].keys() else 7 for i in month]
    text = [['⚫'] * grey]
    for s in stat:
        if len(text[-1]) == 7:
            text.append([])
        text[-1].append(colorcoding[s])
    text[-1] += ['⚫']*(7-len(text[-1]))
    text = '\n'.join([''.join(a) for a in text])
    return text


@bot.message_handler(commands=['stats'])
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
    if add_achievement(message.from_user.id, 'stats', RESPONSES_FOLDER+'/'):
        bot.send_message(message.chat.id, achievement_message('stats', lang))
    bot.send_message(
        message.chat.id,
        '{0} {1}/{2}:\n{3}'.format(
            service[lang]['stats'], str(curmonth), str(curyear),
            calendar(user, curmonth, curyear)
        ),
        reply_markup=types.InlineKeyboardMarkup([[
            types.InlineKeyboardButton('◀️', callback_data='SS_-'),
            types.InlineKeyboardButton('▶️', callback_data='SS_+')
        ]])
    )
    return


@bot.callback_query_handler(lambda call: call.data[:3] == 'SS_')
def switch_calendar(call: types.CallbackQuery):
    lang = get_lang(call.from_user)
    data = call.data[-1]
    month, year = map(int, call.message.text.split('\n')[0].split()[-1][:-1].split('/'))
    if data == '+':
        month += 1
        if month == 13:
            year += 1
            month = 1
    else:
        month -= 1
        if month == 0:
            year -= 1
            month = 12
    bot.edit_message_text(
        '{stats} {month}/{year}:\n{calendar}'.format(
            stats=service[lang]['stats'],
            month=month, year=year,
            calendar=calendar(call.from_user.id, month, year)
        ),
        call.message.chat.id,
        call.message.id,
        reply_markup=call.message.reply_markup
    )
    bot.answer_callback_query(call.id, service[lang]['stats_next'])


@bot.message_handler(commands=['delete'])
def delete(message):
    lang = get_lang(message.from_user)
    bot.send_message(message.chat.id, service[lang]['delete'], reply_markup=types.InlineKeyboardMarkup([[
        types.InlineKeyboardButton('Да', callback_data='CL_y'),
        types.InlineKeyboardButton('Нет', callback_data='CL_n')
    ]]))
    return


@bot.message_handler(commands=['today'])
@registered_only
def today(message):
    lang = get_lang(message.from_user)
    if add_achievement(message.from_user.id, 'today', RESPONSES_FOLDER+'/'):
        bot.send_message(message.chat.id, achievement_message('today', lang))
    gens.today(message.from_user.id)
    return


@bot.callback_query_handler(lambda call: call.data[:3] == 'CL_')
def wipe(call: types.CallbackQuery):
    lang = get_lang(call.from_user)
    bot.answer_callback_query(call.id, service[lang]['ok'])
    if call.data[-1] == 'n':
        bot.delete_message(call.message.chat.id, call.message.id)
        bot.delete_message(call.message.chat.id, call.message.id-1)
        return
    os.remove(RESPONSES_FOLDER+'/'+str(call.from_user.id)+'.json')
    dab_upd(STATUS_FILE, call.from_user.id, None)
    chat_users.delete_user(call.from_user.id)
    bot.delete_message(call.message.chat.id, call.message.id)
    return


@bot.message_handler(func=lambda message: pend.check_pending(message.from_user.id) and message.text[0] != '/')
def email(message: types.Message):
    lang = get_lang(message.from_user)
    response = message.text
    with open(RESPONSES_FOLDER+'/'+str(message.from_user.id)+'.json') as file:
        user_db = json.load(file)
    if response.isdigit():
        if user_db['code'] is not None:
            if int(response) == user_db['code']:
                bot.send_message(message.chat.id, service[lang]['success'])
                pend.retreat_pending(message.from_user.id)
                dab_upd(STATUS_FILE, message.from_user.id, None)
                wanna_get(message)
                return
            else:
                bot.send_message(message.chat.id, service[lang]['email_wrong_code'])
                return
        return
    else:
        try:
            code = send_code(response, DOMEN)
        except:
            bot.send_message(ADMIN, 'Токен GMail сгорел. Обнови. Его хотели использовать')
            bot.send_message(message.chat.id, service[lang]['registration_closed'])
        if code is None:
            bot.send_message(message.chat.id, service[lang]['email_wrong_adress'])
            return
        if code == -1:
            bot.send_message(message.chat.id, service[lang]['email_wrong_domen'])
            return
        print(code)
        user_db['code'] = code
        with open(RESPONSES_FOLDER+'/'+str(message.from_user.id)+'.json', 'w') as file:
            json.dump(user_db, file)
        bot.send_message(message.chat.id, service[lang]['email_sent'])
        return


@bot.message_handler(commands=['time'])
@registered_only
def time_present(message: types.Message, lang=None):
    if lang is None:
        lang = get_lang(message.from_user)
    markup = [[]]
    linewidth = len(TIMES) // 2 if len(TIMES) // 2 < 4 else 4
    for i, elem in enumerate(TIMES):
        if len(markup[-1]) == linewidth:
            markup.append([])
        markup[-1].append(types.InlineKeyboardButton(elem, callback_data='TM_'+str(i)))
    markup = types.InlineKeyboardMarkup(markup)
    bot.send_message(
        message.chat.id,
        service[lang]['time'],
        reply_markup=markup
    )
    return


@bot.callback_query_handler(lambda call: call.data[:3] == 'TM_')
def time_choose(call: types.CallbackQuery):
    lang = get_lang(call.from_user)
    user_id = call.from_user.id
    choice = int(call.data[3:])
    bot.answer_callback_query(call.id, service[lang]['time_chosen']+TIMES[choice])
    dab_upd(STATUS_FILE, call.from_user.id, TIMES[choice])
    if is_late(TIMES[choice]):
        with open(RESPONSES_FOLDER+'/'+str(user_id)+'.json') as file:
            data = json.load(file)
        if timestamp() not in data['responses'].keys():
            poll(user_id, lang)
    bot.edit_message_text(
        service[lang]['time_chosen']+f'*{TIMES[choice]}*',
        call.message.chat.id,
        call.message.id,
        parse_mode='Markdown'
    )
    return


@bot.message_handler(commands=['achievements'])
@registered_only
def achievements(message: types.Message):
    lang = get_lang(message.from_user)
    with open(RESPONSES_FOLDER+'/'+str(message.from_user.id)+'.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    if 'achievements' not in data.keys():
        data['achievements'] = []
        with open(RESPONSES_FOLDER+'/'+str(message.from_user.id)+'.json', 'w', encoding='utf-8') as f:
            json.dump(data, f)
    bot.send_message(
        message.chat.id,
        '{init}:\n{achievements}'.format(
            init=service[lang]['achievements'],
            achievements='\n\n'.join([
                '✨{name}:\n{description}'.format(
                    name=achievements_d[lang][name]['name'],
                    description=achievements_d[lang][name]['description'])
                for name in data['achievements']])
        )
    )


@bot.message_handler(
        commands=['thanks'],
        func=lambda message: message.chat.id == CHAT and message.reply_to_message is not None)
def thanks(message: types.Message):
    pseudonym = message.reply_to_message.text.split('\n')[0][2:]
    if add_achievement(
        chat_users.get_user_by_pseudonym(pseudonym).id,
        'good_conversation',
        RESPONSES_FOLDER+'/'
    ):
        bot.send_message(chat_users.get_user_by_pseudonym(pseudonym).id, achievement_message('good_conversation'))


@bot.message_handler(commands=['grant'], func=lambda message: message.chat.id == ADMIN)
def grant(message: types.Message):
    text = message.text.split()[1:]
    with open('achievements.json', 'r', encoding='utf-8') as f:
        gen_data = json.load(f)
    if len(text) < 2:
        return
    if not text[0].isdigit():
        return
    if text[1] not in gen_data.keys():
        return
    user = int(text[0])
    if add_achievement(user, text[1], RESPONSES_FOLDER+'/'):
        bot.send_message(user, achievement_message(text[1]))
        bot.send_message(ADMIN, 'Добавила достижение.')


@bot.message_handler(['checkuser'], func=lambda message: message.from_user.id == ADMIN)
def checkuser(message):
    entities = message.entities
    buffer = ''
    for entity in entities:
        buffer += entity.type
        buffer += ' ' + str(entity.user.id) if entity.user is not None else 'None'
        buffer += '\n'
    bot.reply_to(message, buffer)


@bot.message_handler(['run'], func=lambda message: message.from_user.id == ADMIN)
def run(message):
    forced_polls()
    bot.reply_to(message, 'Отправила опросы.')
    return


@bot.message_handler(['language'])
def language(message: types.Message):
    bot.send_message(
        message.chat.id,
        'Выбери язык/Choose language',
        reply_markup=types.InlineKeyboardMarkup([[
            types.InlineKeyboardButton('Русский', callback_data='LG_ru'),
            types.InlineKeyboardButton('English', callback_data='LG_en')
        ]])
    )


@bot.callback_query_handler(func=lambda call: call.data[:3] == 'LG_')
def language_choice(call: types.CallbackQuery):
    with open(RESPONSES_FOLDER+'/'+str(call.from_user.id)+'.json', 'r') as file:
        user_data = json.load(file)
    user_data['lang'] = call.data[3:]
    with open(RESPONSES_FOLDER+'/'+str(call.from_user.id)+'.json', 'w') as file:
        json.dump(user_data, file)
    bot.answer_callback_query(call.id, call.data[3:])
    bot.edit_message_text(
        service[call.data[3:]]['language'],
        call.message.chat.id,
        call.message.id
    )


@bot.message_handler(['report'], func=lambda m: m.chat.id == ADMIN)
def send_report(_):
    from report import make_report
    a = make_report(RESPONSES_FOLDER)
    with open(a, 'rb') as file:
        bot.send_document(ADMIN, file, caption='Report for '+timestamp())
    os.remove(a)
    return


def safe_send_message(chat_id, message):
    try:
        return bot.send_message(chat_id, message)
    except ConnectionError:
        time.sleep(3)
        return safe_send_message(chat_id, message)


@bot.message_handler(
        content_types=['text'],
        func=lambda message: message.from_user.id == message.chat.id and message.text[0] != '/')
@registered_only
def anon_message(message: types.Message):
    text = message.text
    hearts = ['❤️', '🧡', '💛', '💚', '💙', '💜', '❤️‍🩹']
    user = chat_users.get_user_by_id(message.from_user.id)
    if user is None:
        user = chat_users.new_user(message.from_user.id, message.from_user.first_name)
    with open(RESPONSES_FOLDER+'/'+str(message.from_user.id)+'.json') as file:
        data = json.load(file)
    user.last_personal_message = message.id
    if timestamp() in data['responses'].keys():
        status = hearts[data['responses'][timestamp()]]
    else:
        status = '❓'
    try:
        safe_send_message(
            CHAT,
            status + ' ' + user.pseudonym + '\n' + text
        )
    except telebot.apihelper.ApiTelegramException:
        print('Чат не найден:', CHAT)
    return


@bot.message_handler(
        content_types=['text'],
        func=lambda message: message.chat.id == CHAT and message.reply_to_message is not None)
def reply_to_anon_message(message: types.Message):
    if message.reply_to_message.from_user.id != bot.get_me().id:
        return
    reply = message.reply_to_message.text
    if reply[0] not in ('❤️', '🧡', '💛', '💚', '💙', '💜', '❤️‍🩹', '❓'):
        return
    pseudonym = reply.split('\n')[0][2:]
    user = chat_users.get_user_by_pseudonym(pseudonym)
    if user is None:
        bot.send_message(CHAT, 'Этого пользователя уже не существует.')
        return
    text = message.text.format(name=user.name)
    safe_send_message(user.id, text)
    return


@bot.message_handler(content_types=['new_chat_members'], func=lambda message: message.chat.id == CHAT)
def new_operator(message: types.Message):
    for user in message.new_chat_members:
        lang = get_lang(user)
        if add_achievement(user.id, 'operator', RESPONSES_FOLDER+'/'):
            bot.send_message(user.id, achievement_message('operator', lang))
        bot.send_message(CHAT, service[lang]['new_operator'])


@bot.my_chat_member_handler()
def banned(update: types.ChatMemberUpdated):
    user = update.from_user.id
    if update.new_chat_member.status == 'kicked':
        chat_users.delete_user(user)
        os.remove(RESPONSES_FOLDER+'/'+str(user)+'.json')
        dab_upd(STATUS_FILE, user, None)


def forced_polls():
    with open(STATUS_FILE) as file:
        users = json.load(file)
        users = {int(user_id): value for user_id, value in users.items()}
    for user_id in users:
        if users[user_id] is not None and user_id not in blkl.dab:
            try:
                with open(RESPONSES_FOLDER+'/'+str(user_id)+'.json') as file:
                    data = json.load(file)
            except FileNotFoundError:
                dab_upd(STATUS_FILE, user_id, None)
                continue
            if 'lang' in data.keys():
                lang = data['lang']
            else:
                lang = 'ru'
            if timestamp() not in data['responses'].keys():
                if is_late(users[user_id]):
                    poll(user_id, lang)
                    blkl.add(user_id)
    return


def set_commands(scope=types.BotCommandScopeDefault):
    for lang in ('ru', 'en'):
        bot.delete_my_commands(scope=scope, language_code=lang)
        bot.set_my_commands([
            types.BotCommand(name, commands[lang][name])
            for name
            in commands[lang]
        ], scope=scope, language_code=lang)
    return


if __name__ == '__main__':
    with open(STATUS_FILE) as file:
        users = json.load(file)
        users = {int(user_id): value for user_id, value in users.items()}
    for user in users:
        try:
            set_commands(types.BotCommandScopeChat(user))
        except telebot.apihelper.ApiTelegramException:
            print('There\'s no chat with user', user)
    for elem in TIMES:
        schedule.every().day.at(elem).do(send_poll, elem)
    threading.Thread(target=bot.infinity_polling, name='bot_infinity_polling', daemon=True).start()
    if timestamp() not in blkl.dab:
        blkl.clear()
        blkl.add(timestamp())
    forced_polls()
    set_commands(types.BotCommandScope())
    for lang in ('ru', 'en'):
        bot.set_my_description(description[lang], language_code=lang)
        bot.set_my_short_description(short_description[lang], language_code=lang)
    del description
    del short_description
    print('Начала работу')
    while S:
        schedule.run_pending()
        time.sleep(1)
