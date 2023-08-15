import json
import responses
import time


def make_report(manager: responses.UserManager, filename=None):
    if filename is None:
        filename = time.strftime("Report_%Y_%m_%d.json")
    final = {}
    for uid, user in manager.users.items():
        final[uid] = {day.date: day.to_dict() for day in user.days}
    with open(filename, "w", encoding="utf-8") as file:
        json.dump(final, file, indent=4, ensure_ascii=False)
    return filename
