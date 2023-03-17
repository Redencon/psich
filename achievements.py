import json
import time



def timestamp():
    '''Returns current date in format used as a key'''
    return '/'.join([str(time.localtime()[0]), str(time.localtime()[1]), str(time.localtime()[2])])

def add_achievement(user_id: int, name: str, DIRECTORY = 'responses/'):
    try:
        with open(DIRECTORY+str(user_id)+'.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        return False
    if 'achievements' not in data:
        data['achievements'] = []
    if name in data['achievements']:
        return False
    data['achievements'].append(name)
    with open(DIRECTORY+str(user_id)+'.json', 'w', encoding='utf-8') as f:
        json.dump(data, f)
    return True

def days_in_month(mon: int, year: int):
    if mon == 2:
        if year % 4 == 0:
            return 29
        return 28
    if mon in (4, 6, 9, 11):
        return 30
    return 31


def streak(user_id, DIRECTORY = 'responses/'):
    with open(DIRECTORY+str(user_id)+'.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    curday = time.localtime().tm_mday
    curmonth = time.localtime().tm_mon
    curyear = time.localtime().tm_year
    f = lambda d, m, y: str(y)+'/'+str(m)+'/'+str(d)
    i = 0
    while f(curday, curmonth, curyear) in data['responses'].keys():
        i += 1
        if curday == 1:
            curmonth -= 1
            if curmonth == 0:
                curmonth = 12
                curyear -= 1
                curday = 31
            else:
                curday = days_in_month(curmonth, curyear)
        else:
            curday -= 1
    return i


def streak_achievement(user_id: int, streak_length: int, DIRECTORY = 'responses/'):
    with open(DIRECTORY+str(user_id)+'.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    if 'achievements' not in data.keys():
        data['achievements'] = []
        with open(DIRECTORY+str(user_id)+'.json', 'w', encoding='utf-8') as f:
            json.dump(data, f)
    if 'streak_'+str(streak_length) in data['achievements']:
        return None
    if streak(user_id, DIRECTORY) >= streak_length:
        add_achievement(user_id, 'streak_'+str(streak_length), DIRECTORY)
        return True
    return False


def average_consistency_achievement(user_id:int, amount: int, DIRECTORY = 'responses/'):
    with open(DIRECTORY+str(user_id)+'.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    if 'achievements' not in data.keys():
        data['achievements'] = []
        with open(DIRECTORY+str(user_id)+'.json', 'w', encoding='utf-8') as f:
            json.dump(data, f)
    if 'consistency_'+str(amount) in data['achievements']:
        return None
    curyear = time.localtime()[0]
    curmonth = time.localtime()[1]
    month = [str(curyear)+'/'+str(curmonth)+'/'+str(i) for i in range(1, days_in_month(curmonth, curyear)+1)]
    this_month_consistency = sum([i in data['responses'].keys() for i in month])
    if this_month_consistency >= amount:
        add_achievement(user_id, 'consistency_'+str(amount), DIRECTORY)
        return True
    return False


def achievement_message(name):
    with open('achievements.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    return '🎉Новое достижение🎉: '+data[name]['name']+'!\n\n'+data[name]['congrats']