import telebot
import json
import os
from achievements import timestamp

class Blacklist:
    def __init__(self, filename) -> None:
        self.filename = filename
        if os.path.exists(self.filename):
            with open(self.filename) as file:
                self.dab = json.load(file)
        else:
            self.clear()
    
    def dump(self):
        with open(self.filename, 'w') as file:
            json.dump(self.dab, file)
        return
    
    def add(self, user):
        self.dab.append(user)
        self.dump()

    def clear(self):
        self.dab = []
        self.dump()

class Day:
    def __init__(self, answers = []) -> None:
        if type(answers) == int:
            self.answers = []

class GeneralData:
    def __init__(self, filename, bot: telebot.TeleBot, ADMIN: int):
        self.bot = bot
        self.ADMIN = ADMIN
        with open(filename) as file:
            self.data = json.load(file)
        self.filename = filename
        return
    
    def dump(self):
        with open(self.filename, 'w') as file:
            json.dump(self.data, file)
        return

    def new_day(self, key):
        self.data[key] = {'total': 0, 'sum': 0}
        adm_mess = self.bot.send_message(self.ADMIN, f'{timestamp()}\nСтатситика по опросу:\n0 ответов\nСредний результат: NaN')
        self.data[key]['admin'] = adm_mess.id
        self.data[key]['others'] = {}
        self.dump()
        return

    def add_response(self, key, answer):
        if key not in self.data:
            self.new_day(key)
        self.data[key]['total'] += 1
        self.data[key]['sum'] += answer
        self.update_admin(key)
        self.dump()
        return
    
    def update_admin(self, key):
        hearts = ['❤️','🧡','💛','💚','💙','💜','❤️‍🩹']
        text = f'{key}\nСтатситика по опросу:\n{self.data[key]["total"]} ответов\nСредний результат: {hearts[round(self.data[key]["sum"] / self.data[key]["total"])]}'
        self.bot.edit_message_text(text, self.ADMIN, self.data[key]['admin'])
        for user in self.data[key]['others']:
            try:
                self.bot.edit_message_text(
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
        if self.data[key]['total'] < 3:
            self.bot.send_message(user_id, 'Недостаточно ответов за сегодня для подсчёта среднего.')
            return
        mess = self.bot.send_message(
            user_id,
            f'Сегодня средний результат опроса: {hearts[round(self.data[key]["sum"] / self.data[key]["total"])]}'
        )
        self.data[key]['others'][user_id] = mess.id
        self.dump()
        return
        


class Pending_users():
    def __init__(self, filename):
        self.filename = filename
        with open(self.filename) as file:
            self.dab = set(json.load(file))
        return
    
    def dump(self):
        with open(self.filename, 'w') as file:
            json.dump(list(self.dab), file)
        return

    def add_pending(self, user_id):
        self.dab.add(user_id)
        self.dump()
    
    def check_pending(self, user_id):
        '''Is user in pending list?'''
        return user_id in self.dab
    
    def retreat_pending(self, user_id):
        self.dab.discard(user_id)
        self.dump()
        return