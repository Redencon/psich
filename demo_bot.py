'''
Настенька
v. 0.0.17
'''

import os
import telebot
import json
import threading
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

with open('secret2.json', 'r', encoding='utf-8') as f:
    secret = json.load(f)

TOKEN = secret['TOKEN']
ADMIN = secret['ADMIN']
ARBITRARY_THRESHOLD = secret['ARBITRARY_THRESHOLD']
CHAT = secret['CHAT']
S = True

bot = telebot.TeleBot(TOKEN)

TIMES = ('08:15', '12:10', '15:20', '20:00')

chat_users = gpt_users.UserManager()

class Blacklist:
    def __init__(self) -> None:
        if os.path.exists('blacklist2.json'):
            with open('blacklist2.json') as file:
                self.dab = json.load(file)
        else:
            self.clear()
    
    def dump(self):
        with open('blacklist2.json', 'w') as file:
            json.dump(self.dab, file)
        return
    
    def add(self, user):
        self.dab.append(user)
        self.dump()

    def clear(self):
        self.dab = []
        self.dump()

class GeneralData:
    def __init__(self):
        with open('general.json') as file:
            self.data = json.load(file)
        return
    
    def dump(self):
        with open('general.json', 'w') as file:
            json.dump(self.data, file)
        return

    def new_day(self, key):
        self.data[key] = {'total': 0, 'sum': 0}
        adm_mess = bot.send_message(ADMIN, f'{timestamp()}\nСтатситика по опросу:\n0 ответов\nСредний результат: NaN')
        self.data[key]['admin'] = adm_mess.id
        self.data[key]['others'] = {}
        self.dump()
        return

    def add_response(self, key, answer):
        self.data[key]['total'] += 1
        self.data[key]['sum'] += answer
        self.update_admin(key)
        self.dump()
        return
    
    def update_admin(self, key):
        hearts = ['❤️','🧡','💛','💚','💙','💜','❤️‍🩹']
        text = f'{key}\nСтатситика по опросу:\n{self.data[key]["total"]} ответов\nСредний результат: {hearts[round(self.data[key]["sum"] / self.data[key]["total"])]}'
        bot.edit_message_text(text, ADMIN, self.data[key]['admin'])
        for user in self.data[key]['others']:
            try:
                bot.edit_message_text(
                    f'Сегодня средний результат опроса: {hearts[round(self.data[key]["sum"] / self.data[key]["total"])]}',
                    user,
                    self.data[key]['others'][user]
                )
            except telebot.apihelper.ApiTelegramException:
                print('It failed. Again :<')
        return
    
    def today(self, user_id):
        hearts = ['❤️','🧡','💛','💚','💙','💜','❤️‍🩹']
        key = timestamp()
        if self.data[key]['total'] < ARBITRARY_THRESHOLD:
            bot.send_message(user_id, 'Недостаточно ответов за сегодня для подсчёта среднего.')
            return
        mess = bot.send_message(
            user_id,
            f'Сегодня средний результат опроса: {hearts[round(self.data[key]["sum"] / self.data[key]["total"])]}'
        )
        self.data[key]['others'][user_id] = mess.id
        self.dump()
        return
        


class Pending_users():
    def __init__(self):
        with open('pending2.json') as file:
            self.dab = set(json.load(file))
        return
    
    def dump(self):
        with open('pending2.json', 'w') as file:
            json.dump(list(self.dab), file)
        return

    def add_pending(self, user_id):
        self.dab.add(user_id)
        self.dump()
    
    def check_pending(self, user_id):
        return user_id in self.dab
    
    def retreat_pending(self, user_id):
        self.dab.discard(user_id)
        self.dump()
        return


gens = GeneralData()
pend = Pending_users()
blkl = Blacklist()

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

def dab_upd(filename, user_id, argument = None, **kwargs):
    '''Open the specified dab file and change it'''
    with open(filename) as file:
        dab = {int(key): val for key, val in json.load(file).items()}
    if user_id not in dab.keys() and kwargs:
        dab[user_id] = {}
    if argument is not None:
        dab[user_id] = argument
    else:
        for key in kwargs:
            dab[user_id][key] = kwargs[key]
    with open(filename, 'w') as file:
        json.dump(dab, file)
    return

def new_response(user_id, key, answer):
    with open('responses2/'+str(user_id)+'.json') as file:
        user_db = json.load(file)
    if key in user_db['responses'].keys():
        return False
    user_db['responses'][key] = answer
    with open('responses2/'+str(user_id)+'.json', 'w') as file:
        json.dump(user_db, file)
    return True

def dem_response(user_id, key, answer):
    with open('responses2/'+str(user_id)+'.json') as file:
        user_db = json.load(file)
    user_db['demog'][key] = answer
    with open('responses2/'+str(user_id)+'.json', 'w') as file:
        json.dump(user_db, file)
    return

def poll(user_id):
    hearts = ['❤️','🧡','💛','💚','💙','💜','❤️‍🩹']
    text = f'''{timestamp()}
Время для ежедневного опроса!
Как ты оцениваешь своё настроение?
❤️ - Замечательно!
🧡 - Отлично!
💛 - Хорошо!
💚 - Нормально.
💙 - Не очень.
💜 - Мне тяжело.
❤️‍🩹 - У меня большие трудности.'''
    markup = types.InlineKeyboardMarkup([[types.InlineKeyboardButton(hearts[i], callback_data='DS_'+str(i)) for i in range(7)]])
    bot.send_message(user_id, text, reply_markup=markup)

def send_poll(time):
    with open('status2.json') as file:
        users = json.load(file)
        users = {int(user_id):value for user_id, value in users.items()}
    last_today = time == TIMES[-1]
    if time == TIMES[0]:
        gens.new_day(timestamp())
        blkl.clear()
        blkl.add(timestamp())
    for user_id in users:
        if users[user_id] is not None:
            if users[user_id] == time and user_id not in blkl.dab:
                poll(user_id)
                blkl.add(user_id)
            if last_today and users[user_id] != time:
                with open('responses2/'+str(user_id)+'.json', 'r', encoding='utf-8') as f:
                    user_data = json.load(f)
                if timestamp() not in user_data['responses'].keys():
                    bot.send_message(user_id, 'Я заметила, что ты ещё не заполнил(а) опрос. Пройди его, пожалуйста!')
    return

def wanna_get(message):
    bot.send_message(
            message.chat.id,
            'Вы согласны получать ежедневные опросы о вашем настроении?',
            reply_markup=types.InlineKeyboardMarkup([[
                types.InlineKeyboardButton('Да', callback_data='ST_y'),
                types.InlineKeyboardButton('Нет', callback_data='ST_n')
            ]])
        )
    return


@bot.message_handler(commands=['setchat'], func=lambda message: message.from_user.id == ADMIN)
def setchat(message: types.Message):
    CHAT = message.chat.id
    secret['CHAT'] = CHAT
    with open('secret.json', 'w', encoding='utf-8') as f:
        json.dump(secret, f, ensure_ascii=False, indent=4)
    bot.send_message(CHAT, 'Использую этот чат как чат операторов.')
    return

@bot.message_handler(commands=['update'], func=lambda message: message.from_user.id == ADMIN)
def update(message: types.Message):
    import sys
    import subprocess
    subprocess.Popen('start.bat', creationflags=subprocess.CREATE_NEW_CONSOLE)
    global S
    S = False
    sys.exit()


@bot.message_handler(commands=['start'])
def start(message):
    with open('status2.json') as file:
        users = json.load(file)
    if str(message.from_user.id) not in users.keys():
        bot.send_message(message.chat.id, 'Для использования бота надо пройти верификацию, используя электронную почту. Адрес будет удалён после верификации.\nВведите свой адрес:')
        with open('responses2/' + str(message.from_user.id) + '.json', 'w') as file:
            json.dump({'demog': {}, 'responses': {}, 'code': None}, file)
        pend.add_pending(message.from_user.id)
    else:
        bot.reply_to(message, get_help()['help'])
    return

@bot.message_handler(['help'])
def help(message):
    help_db = get_help()
    argv = message.text.split()
    if len(argv) == 1:
        cmd = 'help'
    else:
        cmd = argv[1]
    if cmd not in help_db.keys():
        bot.reply_to(message, 'Такой команды нет.')
        return
    bot.reply_to(message, help_db[cmd])
    return
    

@bot.callback_query_handler(lambda call: call.data[:3] == 'ST_')
def start_response(call: types.CallbackQuery):
    bot.answer_callback_query(call.id, 'Спасибо.')
    bot.edit_message_text('Спасибо.', call.message.chat.id, call.message.id)
    with open('responses2/'+str(call.from_user.id)+'.json') as file:
        user_db = json.load(file)
    if call.data[-1] == 'n':
        if 'lgbt' in user_db['demog'].keys():
            dab_upd('status2.json', call.from_user.id, None)
        return
    if 'lgbt' in user_db['demog'].keys():
        with open('status2.json') as file:
            statuses = json.load(file)
        if statuses[str(call.from_user.id)] is None:
            time_present(call.message)
        return
    with open('pool.json') as file:
        questions = json.load(file)
    options = questions[0][2]
    bot.edit_message_text(
        'Перед началом использования бота, ответьте на несколько коротких вопросов.\n---\n'+questions[0][1],
        call.message.chat.id,
        call.message.id,
        reply_markup=types.InlineKeyboardMarkup([[types.InlineKeyboardButton(text, callback_data='DG_0'+str(i)) for i, text in enumerate(options)]])
    )
    return

@bot.callback_query_handler(lambda call: call.data[:3] == 'DS_')
def parse_survey(call: types.CallbackQuery):
    hearts = ['❤️','🧡','💛','💚','💙','💜','❤️‍🩹']
    answer = int(call.data[-1])
    text = call.message.text.split('\n')
    if text[0] != timestamp():
        bot.answer_callback_query(call.id, 'Опрос устарел.')
        bot.edit_message_reply_markup(call.message.chat.id, call.message.id)
        return
    bot.answer_callback_query(call.id, f'Вы ответили {hearts[answer]}')
    if new_response(call.from_user.id, text[0], answer):
        gens.add_response(text[0], answer)
    bot.edit_message_text('\n'.join(text) + f'\nВы ответили: {hearts[answer]}', call.message.chat.id, call.message.id, reply_markup=None)
    with open('responses.yaml', 'r', encoding='utf-8') as f:
        responses = yaml.safe_load(f)
    bot.send_message(
        call.message.chat.id,
        random.choice(responses[answer])
    )
    for i in (3, 7, 14, 30, 61, 150):
        a = streak_achievement(call.from_user.id, i, 'responses2/')
        if a is not None:
            if a:
                bot.send_message(call.message.chat.id, achievement_message('streak_'+str(i)))
            else:
                break
    for i in (15, 30):
        a = average_consistency_achievement(call.from_user.id, i)
        if a:
            bot.send_message(call.message.chat.id, achievement_message('consistency_'+str(i)))
    return

@bot.message_handler(commands=['unsub', 'sub'])
def unsub(message):
    wanna_get(message)
    return

@bot.callback_query_handler(lambda call: call.data[:3] == 'US_')
def unsub_check(call):
    if call.data[-1] == 'y':
        bot.answer_callback_query(call.id, 'Ну и замечательно.')
        dab_upd('status2.json', call.from_user.id, TIMES[1])
        bot.edit_message_text('Да будет так.', call.message.chat.id, call.message.id)
    else:
        dab_upd('status2.json', call.from_user.id, None)
        bot.answer_callback_query(call.id, 'Да будет так.')
        bot.edit_message_text('Да будет так.', call.message.chat.id, call.message.id)
    return

@bot.callback_query_handler(lambda call: call.data[:3] == 'DG_')
def demogr(call: types.CallbackQuery):
    bot.answer_callback_query(call.id)
    with open('pool2.json') as file:
        questions = json.load(file)
    cur = int(call.data[3])
    ans = int(call.data[4:])
    dem_response(call.from_user.id, questions[cur][0], questions[cur][2][ans])
    cur += 1
    if cur >= len(questions):
        bot.edit_message_text('Спасибо за участие в опросе', call.message.chat.id, call.message.id)
        time_present(call.message)
        # dab_upd('status2.json', call.from_user.id, TIMES[1])
        bot.send_message(ADMIN, f'Новый пользователь: {call.from_user.full_name}')
        if time.localtime()[3] > 12 or (time.localtime()[3] == 12 and time.localtime()[4] > 10):
            poll(call.from_user.id)
        return
    else:
        bot.edit_message_text(
            'Перед началом использования бота, ответьте на несколько коротких вопросов.\n---\n'+questions[cur][1],
            call.message.chat.id,
            call.message.id,
            reply_markup=types.InlineKeyboardMarkup(convivnient_slicer([types.InlineKeyboardButton(text, callback_data='DG_'+str(cur)+str(i)) for i, text in enumerate(questions[cur][2])]), row_width=5)
        )
        return

def calendar(user_id, month, year):
    with open('responses2/'+str(user_id)+'.json') as file:
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
def stats(message: types.Message):
    curyear = time.localtime()[0]
    curmonth = time.localtime()[1]
    argv = message.text.split()[1:]
    if len(argv) > 0:
        if argv[0].isdigit():
            curmonth = int(argv[0])
            if curmonth > time.localtime()[1]:
                curyear -= 1
    user = message.from_user.id
    if add_achievement(message.from_user.id, 'stats', 'responses2/'):
        bot.send_message(message.chat.id, achievement_message('stats'))
    bot.send_message(
        message.chat.id,
        'Твой текущий успех за месяц '+ str(curmonth) + '/' + str(curyear) +':\n'+calendar(user, curmonth, curyear),
        reply_markup=types.InlineKeyboardMarkup([[
            types.InlineKeyboardButton('◀️', callback_data='SS_-'),
            types.InlineKeyboardButton('▶️', callback_data='SS_+')
        ]])
    )
    return

@bot.callback_query_handler(lambda call: call.data[:3] == 'SS_')
def switch_calendar(call: types.CallbackQuery):
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
        'Твой текущий успех за месяц '+ str(month) + '/' + str(year) +':\n'+calendar(call.from_user.id, month, year),
        call.message.chat.id,
        call.message.id,
        reply_markup=call.message.reply_markup
    )
    bot.answer_callback_query(call.id, 'Другой месяц...')



@bot.message_handler(commands=['delete'])
def delete(message):
    bot.send_message(message.chat.id, 'Вы уверены, что хотите удалить все свои данные?\nДЕЙСТВИЕ НЕОБРАТИМО', reply_markup=types.InlineKeyboardMarkup([[
        types.InlineKeyboardButton('Да', callback_data='CL_y'),
        types.InlineKeyboardButton('Нет', callback_data='CL_n')
    ]]))
    return

@bot.message_handler(commands=['today'])
def today(message):
    if add_achievement(message.from_user.id, 'today', 'responses2/'):
        bot.send_message(message.chat.id, achievement_message('today'))
    gens.today(message.from_user.id)
    return

@bot.callback_query_handler(lambda call: call.data[:3] == 'CL_')
def wipe(call: types.CallbackQuery):
    bot.answer_callback_query(call.id, 'Ок.')
    if call.data[-1] == 'n':
        bot.delete_message(call.message.chat.id, call.message.id)
        bot.delete_message(call.message.chat.id, call.message.id-1)
        return
    os.remove('responses2/'+str(call.from_user.id)+'.json')
    dab_upd('status2.json', call.from_user.id, None)
    chat_users.delete_user(call.from_user.id)
    bot.delete_message(call.message.chat.id, call.message.id)
    return

@bot.message_handler(func=lambda message: pend.check_pending(message.from_user.id) and message.text[0] != '/')
def email(message: types.Message):
    response = message.text
    with open('responses2/'+str(message.from_user.id)+'.json') as file:
        user_db = json.load(file)
    if response.isdigit():
        if user_db['code'] is not None:
            if int(response) == user_db['code']:
                bot.send_message(message.chat.id, 'Успех!')
                pend.retreat_pending(message.from_user.id)
                dab_upd('status2.json', message.from_user.id, None)
                wanna_get(message)
                return
            else:
                bot.send_message(message.chat.id, 'Неверный код. Попробуй ещё раз.')
                return
        return
    else:
        code = send_code(response, None)
        if code is None:
            bot.send_message(message.chat.id, 'Неверный формат электронной почты. Попробуй ещё раз: напиши в сообщении только свою электронную почту')
            return
        if code == -1:
            bot.send_message(message.chat.id, 'Поддерживаются только почтовые адреса домена @phystech.edu. Попробуй ещё раз...')
            return
        print(code)
        user_db['code'] = code
        with open('responses2/'+str(message.from_user.id)+'.json', 'w') as file:
            json.dump(user_db, file)
        bot.send_message(message.chat.id, 'На указанную почту было отправлено письмо с кодом подтверждения.\nОтправь мне полученный код.')
        return

@bot.message_handler(commands=['time'])
def time_present(message):
    markup = [[]]
    linewidth = len(TIMES) // 2 if len(TIMES) // 2 < 4 else 4
    for i, elem in enumerate(TIMES):
        if len(markup[-1]) == linewidth:
            markup.append([])
        markup[-1].append(types.InlineKeyboardButton(elem, callback_data='TM_'+str(i)))
    markup = types.InlineKeyboardMarkup(markup)
    bot.send_message(
        message.chat.id,
        'Выберите время, в которое я буду отправлять ежедневный опрос:',
        reply_markup=markup
    )
    return

@bot.callback_query_handler(lambda call: call.data[:3] == 'TM_')
def time_choose(call: types.CallbackQuery):
    user_id = call.from_user.id
    choice = int(call.data[3:])
    bot.answer_callback_query(call.id, f'Вы выбрали время {TIMES[choice]}')
    dab_upd('status2.json', call.from_user.id, TIMES[choice])
    if is_late(TIMES[choice]):
        with open('responses2/'+str(user_id)+'.json') as file:
            data = json.load(file)
        if timestamp() not in data['responses'].keys():
            poll(user_id)
    bot.edit_message_text(
        f'Вы выбрали: *{TIMES[choice]}*',
        call.message.chat.id,
        call.message.id,
        parse_mode='Markdown'
    )
    return

@bot.message_handler(commands=['achievements'])
def achievements(message: types.Message):
    with open('achievements.json', 'r', encoding='utf-8') as f:
        gen_data = json.load(f)
    with open('responses2/'+str(message.from_user.id)+'.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    if 'achievements' not in data.keys():
        data['achievements'] = []
        with open('responses2/'+str(message.from_user.id)+'.json', 'w', encoding='utf-8') as f:
            json.dump(data, f)
    bot.send_message(
        message.chat.id,
        '🏆Твои достижения🏅:\n'+'\n\n'.join(['✨'+gen_data[name]['name']+':\n'+gen_data[name]['description'] for name in data['achievements']])
    )

@bot.message_handler(commands = ['thanks'], func=lambda message: message.chat.id==CHAT and message.reply_to_message is not None)
def thanks(message: types.Message):
    pseudonym = message.reply_to_message.text.split('\n')[0][2:]
    if add_achievement(
        chat_users.get_user_by_pseudonym(pseudonym).id,
        'good_conversation',
        'responses2/'
    ):
        bot.send_message(chat_users.get_user_by_pseudonym(pseudonym).id, achievement_message('good_conversation'))


@bot.message_handler(commands = ['grant'], func = lambda message: message.chat.id == ADMIN)
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
    if add_achievement(user, text[1], 'responses2/'):
        bot.send_message(user, achievement_message(text[1]))
        bot.send_message(ADMIN, 'Добавил достижение.')


@bot.message_handler(['checkuser'], func = lambda message: message.from_user.id == ADMIN)
def checkuser(message):
    entities = message.entities
    buffer = ''
    for entity in entities:
        buffer += entity.type
        buffer += ' ' + str(entity.user.id) if entity.user is not None else 'None'
        buffer += '\n'
    bot.reply_to(message, buffer)


@bot.message_handler(['run'], func = lambda message: message.from_user.id == ADMIN)
def run(message):
    forced_polls()
    bot.reply_to(message, 'Отправила опросы.')
    return

def safe_send_message(chat_id, message):
    try:
        return bot.send_message(chat_id, message)
    except ConnectionError:
        time.sleep(3)
        return safe_send_message(chat_id, message)

@bot.message_handler(content_types=['text'], func= lambda message: message.from_user.id == message.chat.id and message.text[0] != '/')
def anon_message(message: types.Message):
    text = message.text
    hearts = ['❤️','🧡','💛','💚','💙','💜','❤️‍🩹']
    user = chat_users.get_user_by_id(message.from_user.id)
    if user is None:
        user = chat_users.new_user(message.from_user.id, message.from_user.first_name)
    with open('responses2/'+str(message.from_user.id)+'.json') as file:
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


@bot.message_handler(content_types=['text'], func=lambda message: message.chat.id == CHAT and message.reply_to_message is not None)
def reply_to_anon_message(message: types.Message):
    if message.reply_to_message.from_user.id != bot.get_me().id:
        return
    reply = message.reply_to_message.text
    if reply[0] not in ('❤️','🧡','💛','💚','💙','💜','❤️‍🩹', '❓'):
        return
    pseudonym = reply.split('\n')[0][2:]
    user = chat_users.get_user_by_pseudonym(pseudonym)
    if user is None:
        bot.send_message(CHAT, 'Этого пользователя уже не существует.')
        return
    text = message.text.format(name = user.name)
    safe_send_message(user.id, text)
    return


@bot.message_handler(content_types=['new_chat_members'], func=lambda message: message.chat.id == CHAT)
def new_operator(message: types.Message):
    for user in message.new_chat_members:
        if add_achievement(user.id, 'operator', 'responses2/'):
            bot.send_message(user.id, achievement_message('operator'))
    bot.send_message(CHAT, 'Добро пожаловать в чат операторов Настеньки! Здесь можно отвечать на сообщения, которые пользователи пишут боту. Для этого надо использовать reply на сообщение, на которое хочется ответить. Наверху каждого сообщения есть уникальный псевдоним пользователя, по которому его можно опознать. Удачи!')


@bot.my_chat_member_handler()
def banned(update: types.ChatMemberUpdated):
    user = update.from_user.id
    if update.new_chat_member.status == 'kicked':
        chat_users.delete_user(user)
        os.remove('responses2/'+str(user)+'.json')
        dab_upd('status2.json', user, None)


def forced_polls():
    with open('status2.json') as file:
        users = json.load(file)
        users = {int(user_id):value for user_id, value in users.items()}
    for user_id in users:
        with open('responses2/'+str(user_id)+'.json') as file:
            data = json.load(file)
        if users[user_id] is not None and user_id not in blkl.dab:
            if timestamp() not in data['responses'].keys():
                if is_late(users[user_id]):
                    poll(user_id)
                    blkl.add(user_id)
    return



def set_commands(scope=types.BotCommandScopeDefault()):
    bot.delete_my_commands(scope=scope)
    bot.set_my_commands([
        types.BotCommand('start', 'Начать работу с ботом'),
        types.BotCommand('help', 'Получить помощь'),
        types.BotCommand('today', 'Статистика за сегодня'),
        types.BotCommand('time', 'Выбрать время для опроса'),
        types.BotCommand('sub', 'Вкл/Откл ежедневные опросы'),
        types.BotCommand('stats', 'Статистика по опросу за месяц'),
        types.BotCommand('achievements', 'Мои текущие достижения'),
        types.BotCommand('delete', 'Удалить данные')
    ], scope=scope)
    return



if __name__ == '__main__':
    with open('status2.json') as file:
        users = json.load(file)
        users = {int(user_id):value for user_id, value in users.items()}
    for user in users:
        try:
            set_commands(types.BotCommandScopeChat(user))
        except telebot.apihelper.ApiTelegramException:
            print('There\'s np chat with user', user)
    for elem in TIMES:
        schedule.every().day.at(elem).do(send_poll, elem)
    threading.Thread(target=bot.infinity_polling, name='bot_infinity_polling', daemon=True).start()
    if timestamp() not in blkl.dab:
        blkl.clear()
        blkl.add(timestamp())
    forced_polls()
    set_commands()
    print('Начала работу')
    while S:
        schedule.run_pending()
        time.sleep(1)