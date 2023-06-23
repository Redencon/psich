import json
import time
import yaml


def timestamp():
    """Returns current date in format used as a key"""
    return "/".join(
        [str(time.localtime()[0]), str(time.localtime()[1]), str(time.localtime()[2])]
    )


def add_achievement(user_id: int, name: str, DIRECTORY="responses/"):
    """
    Adds an achievement to a user's response.

    :param: user_id - The id of the user who will receive the achievement.
    :param: name - The name of the achievement.
    :param: DIRECTORY - The directory where the responses are stored.

    :return: True if the achievement was successfully added.
    """
    try:
        with open(DIRECTORY + str(user_id) + ".json", "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        return False
    if "achievements" not in data:
        data["achievements"] = []
    if name in data["achievements"]:
        return False
    data["achievements"].append(name)
    with open(DIRECTORY + str(user_id) + ".json", "w", encoding="utf-8") as f:
        json.dump(data, f)
    return True


def days_in_month(mon: int, year: int):
    """
    Return the number of days in the month

    :param: mon - The month to check. 1 - January.
    :param: year - The year to check.

    :return: The number of days in the month
    """
    if mon == 2:
        # Return 29 for a gap year.
        if year % 4 == 0:
            return 29
        return 28
    if mon in (4, 6, 9, 11):
        return 30
    return 31


def streak(user_id: int, DIRECTORY="responses/"):
    """
    Returns the current streak leangth for a user.

    :param: user_id - The user's id.
    :param: DIRECTORY - The directory where the data is stored.

    :return: The current streak size for this user
    """
    with open(DIRECTORY + str(user_id) + ".json", "r", encoding="utf-8") as f:
        data = json.load(f)
    curday = time.localtime().tm_mday
    curmonth = time.localtime().tm_mon
    curyear = time.localtime().tm_year

    def f(d, m, y):
        return f"{y}/{m}/{d}"

    i = 0
    while f(curday, curmonth, curyear) in data["responses"].keys():
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


def streak_achievement(user_id: int, streak_length: int, DIRECTORY="responses/"):
    """
    Check is user qualifies for streak achievement

    This is a function that takes a user_id and a streak_length
    and attempts to determine if they have a streak of
    at least that length in the responses directory.

    :param: user_id - The id of the user
    :param: streak_length - The length of the streak.
    :param: DIRECTORY - The directory to store the responses. Defaults to `responses/`.

    :return: if user qualifies for achievement
    """
    with open(DIRECTORY + str(user_id) + ".json", "r", encoding="utf-8") as f:
        data = json.load(f)
    # Adds achievements field to user file if there is none
    if "achievements" not in data.keys():
        data["achievements"] = []
        with open(DIRECTORY + str(user_id) + ".json", "w", encoding="utf-8") as f:
            json.dump(data, f)
    if "streak_" + str(streak_length) in data["achievements"]:
        return None
    if streak(user_id, DIRECTORY) >= streak_length:
        add_achievement(user_id, "streak_" + str(streak_length), DIRECTORY)
        return True
    return False


def average_consistency_achievement(user_id: int, amount: int, DIRECTORY="responses/"):
    """
    Check is user qualifies for Average consistency achievement

    This is done by counting the number of responses per month

    :param: user_id - ID of the user
    :param: amount - Amount of consistency to average for the user ( int )
    :param: DIRECTORY - Directory to store data ( str ) default'responses / '

    :return: if user qualifies for achievement
    """
    with open(DIRECTORY + str(user_id) + ".json", "r", encoding="utf-8") as f:
        data = json.load(f)
    # Adds achievements field to user file if there is none
    if "achievements" not in data.keys():
        data["achievements"] = []
        with open(DIRECTORY + str(user_id) + ".json", "w", encoding="utf-8") as f:
            json.dump(data, f)
    if "consistency_" + str(amount) in data["achievements"]:
        return None
    curyear = time.localtime()[0]
    curmonth = time.localtime()[1]
    month = [
        str(curyear) + "/" + str(curmonth) + "/" + str(i)
        for i in range(1, days_in_month(curmonth, curyear) + 1)
    ]
    this_month_consistency = sum([i in data["responses"].keys() for i in month])
    if this_month_consistency >= amount:
        add_achievement(user_id, "consistency_" + str(amount), DIRECTORY)
        return True
    return False


def achievement_message(name, lang="ru"):
    """
    Return a message to say that there is a new achievement

    It looks in `loc.yaml` for the information about the achievement

    :param: name - Name of the achievement to say
    :param: lang - Language of the text to look up. Defaults to ru

    :return: String with the message to say that there is a new achievement
    """
    with open("loc.yaml", "r", encoding="utf-8") as file:
        all_text = yaml.safe_load(file)
        achievements_d = {key: all_text[key]["achievements"] for key in all_text}
        service: dict[str, dict[str, str]] = {
            key: all_text[key]["service"] for key in all_text
        }
        del all_text
    return "{intro} {name}!\n\n{congrats}".format(
        intro=service[lang]["new_achievement"].strip(),
        name=achievements_d[lang][name]["name"],
        congrats=achievements_d[lang][name]["congrats"],
    )
