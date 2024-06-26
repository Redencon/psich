"""Handling of user responses

Goals:
- Store all responses of all users
- By request you can get by/user and aggregated response data
- Every day contains data about date, all responses (with timestamps),
the score, the type of score
- Every user has some metadata:
  - Username
  - UserID
  - Poll times
  - Object for communication with MNVR
  - Achievements
  - Groups
  - Demography data
  - other?
"""

import os
import time
from datetime import datetime as dtt
from datetime import timedelta as td
import json
from typing import Optional, Final
from gpt_users import User as GptUser, UserManager as GptUserManager
from dataclasses import dataclass, asdict, field, InitVar
from telebot import types
from telebot import TeleBot as Telebot
from telebot.apihelper import ApiException, ApiTelegramException
import warnings

from local import LocalizedStrings, UsefulStrings

# import achievements as acv

MIN_POLL_DISTANCE: Final[int] = 60
DATE_FORMAT = "%Y-%m-%d"
ARBITRARY_THRESHOLD = 4

service = LocalizedStrings().service
"""TextPack with all service text messages on ru and en"""


@dataclass
class Response:
  time: str
  type: str
  score: int

  def to_dict(self):
    return asdict(self)


@dataclass
class Poll:
  time: str
  type: str

  def to_dict(self):
    return asdict(self)


@dataclass
class Day:
  date: str
  responses: list[Response]

  @classmethod
  def from_dict(cls, d):
    return cls(date=d["date"], responses=[Response(**v) for v in d["responses"]])

  def to_dict(self):
    return dict(date=self.date, responses=[r.to_dict() for r in self.responses])


@dataclass
class Achievement:
  name: str
  timestamp: str
  weight: Optional[int]

  def to_dict(self):
    return asdict(self)


@dataclass
class LastDay:
  date: str
  poll_count: dict[str, int]

  def register_poll(self, tpe: str):
    """Mark poll of given type as sent

    Args:
      tpe (str): poll type
    """
    today = time.strftime(DATE_FORMAT)
    if self.date != today:
      self.date = today
      self.poll_count = {}
    if tpe not in self.poll_count:
      self.poll_count[tpe] = 1
    else:
      self.poll_count[tpe] += 1

  def poll_needed(self, tpe: str, polls_needed: int) -> bool:
    today = time.strftime(DATE_FORMAT)
    if self.date != today:
      self.date = today
      self.poll_count = {}
      return polls_needed > 0
    if tpe not in self.poll_count:
      return polls_needed > 0
    if self.poll_count[tpe] < polls_needed:
      return True
    return False

  @classmethod
  def denovo(cls):
    return cls(time.strftime(DATE_FORMAT), {})

  def to_dict(self):
    return dict(date=self.date, poll_count=self.poll_count)


@dataclass
class User:
  user_id: int
  username: Optional[str]
  first_name: Optional[str]
  polls: list[Poll]
  days: list[Day]
  achievements: list[Achievement]
  hearts: list[str]
  meta: dict
  manager: GptUserManager
  groups: set[str] = field(default_factory=set)
  lastday: LastDay = field(default_factory=LastDay.denovo)
  gptuser: GptUser = field(init=False)

  def __post_init__(
    self,
  ) -> None:
    self.set_gpt_user()

  @classmethod
  def from_dict(cls, d: dict, manager: GptUserManager):
    return cls(
      **{
        key: value
        for key, value in d.items()
        if key
        not in ("manager", "achievements", "days", "polls", "lastday", "groups", "hearts")
      },
      days=[Day.from_dict(day) for day in d["days"]],
      achievements=[Achievement(**ach) for ach in d["achievements"]],
      polls=[Poll(**poll) for poll in d["polls"]],
      lastday=LastDay(**d["lastday"]),
      manager=manager,
      hearts=d.get("hearts", UsefulStrings.hearts["mood"]),
      groups=set(d["groups"])
    )

  def set_gpt_user(self):
    """Add GptUser object to this Object instance

    Args:
      manager (GptUserManager): User Manager used by this bot

    Raises:
      AssertionError: no new user can be added after reaching the limit
    """
    user = self.manager.get_user_by_id(self.user_id)
    if user is None:
      user = self.manager.new_user(
        self.user_id,
        (self.first_name if self.first_name is not None else self.username),
      )
    assert (
      user is not None
    ), "Max user amount reached, can't add new user: {}!".format(self.username)
    self.gptuser = user

  def last_response_was_long_ago(self):
    return False
    if not self.polls:
      return True
    today = dtt.today()
    if not self.days:
      return False
    last_response = dtt.strptime(self.days[-1].date, DATE_FORMAT)
    return (today - last_response).days >= 5

  def response(self, type: str, score: int):
    if not self.days or self.days[-1].date != time.strftime(DATE_FORMAT):
      self.days.append(Day(time.strftime(DATE_FORMAT), []))
    self.days[-1].responses.append(Response(time.strftime("%H:%M"), type, score))
    # tuple(time.strftime("%H:%M"), type, score))
    # TODO: add achievements parsing

  def add_poll(self, time: str, type: str):
    def far_enough(time1: str, time2: str) -> bool:
      h1, m1 = map(int, time1.split(":"))
      h2, m2 = map(int, time2.split(":"))
      mindiff = abs((h2 - h1) * 60 + m2 - m1)
      return mindiff >= MIN_POLL_DISTANCE

    for poll in self.polls:
      if not far_enough(time, poll.time):
        return False
    self.polls.append(Poll(time, type))
    return True

  def is_poll_needed(self, tpe: str) -> bool:
    def was_before(poll_time: str):
      poll_h, poll_m = map(int, poll_time.split(":"))
      now = time.localtime()
      now_h = now.tm_hour
      now_m = now.tm_min
      del now
      return now_h > poll_h or (now_h == poll_h and now_m >= poll_m)

    polls_needed_for_today_count = 0
    for poll in self.polls:
      if poll.type == tpe and was_before(poll.time):
        polls_needed_for_today_count += 1
    return self.lastday.poll_needed(tpe, polls_needed_for_today_count)

  def timezone(self) -> int:
    where = self.meta["demog"].get("place", None)
    if where is None:
      return 0
    if where == "Australia":
      return 7
    if where == "East coast America":
      return -11
    if where == "West coast America":
      return -8
    if where == "East Europe":
      return -1
    if where == "West Europe":
      return -2
    if where == "UK":
      return -3
    if where == "Australia":
      return 7
    if where in ("Moscow", "Russia"):
      return 0
    return 0

  def reminder_needed(self):
    # TODO: write reminder logic
    if any([val > 0 for val in self.lastday.poll_count.values()]):  # no answers
      return False
    if not self.polls:
      return False
    now = dtt.now()
    today = (now.year, now.month, now.day)
    latest = dtt(*today, 0, 0)
    for poll in self.polls:
      h, m = map(int, poll.time.split(":"))
      if dtt(*today, h, m) > latest:
        latest = dtt(*today, h, m)
    if dtt.now() - latest > td(hours=1, minutes=30) and dtt.now() > dtt(
      *today, 20, 0
    ):
      return True

    return False

  def polls_pending(self):
    poll_types = set(poll.type for poll in self.polls)
    for tpe in poll_types:
      if self.is_poll_needed(tpe):
        yield tpe

  def calendar(self, tpe):
    ret = {}
    for day in self.days:
      valid = [
        response.score for response in day.responses if response.type == tpe
      ]
      if not valid:
        continue
      ret[day.date] = round(sum(valid) / len(valid))
    return ret

  def calendar_str(self, month, year, default=False):
    def days_in_month(month, year):
      if month == 2:
        if year % 4 == 0:
          return 29
        return 28
      if month in (1, 3, 5, 7, 8, 10, 12):
        return 31
      return 30
    user_calendar = self.calendar("mood")
    stamp = time.mktime((year, month, 1, 0, 0, 0, 0, 0, -1))
    time_struct = time.localtime(stamp)
    grey = (time_struct.tm_wday - 1 + 1) % 7
    month = [
      time.strftime(
        DATE_FORMAT, time.strptime(f"{year}-{month}-{i}", "%Y-%m-%d")
      )
      for i in range(1, days_in_month(month, year) + 1)
    ]
    if default:
      hearts = UsefulStrings.colorcoding
    else:
      hearts = self.hearts.copy()
      hearts.append("⬜")
    stat = [user_calendar[i] if i in user_calendar else 7 for i in month]
    text = [["⚫"] * grey]
    for s in stat:
      if len(text[-1]) == 7:
        text.append([])
      text[-1].append(hearts[s])
    text[-1] += ["⚫"] * (7 - len(text[-1]))
    text = "\n".join(["".join(a) for a in text])
    return text

  @staticmethod
  def parse_old_data(data: dict, user_id: int, manager: GptUserManager):
    demog = data["demog"]
    code = data.get("code", None)
    lang = data.get("lang", "ru")
    responses: dict[str, int] = data["responses"]

    def breakdown_date(date: str):
      try:
        return time.strftime(DATE_FORMAT, time.strptime(date, "%Y/%m/%d"))
      except TypeError as e:
        print(time.strftime(DATE_FORMAT))
        raise KeyboardInterrupt

    achievements = data.get("achievements", [])
    return User(
      polls=[Poll("12:10", "mood")],
      user_id=user_id,
      username=None,
      first_name=None,
      days=[
        Day(breakdown_date(key), [Response("12:10", "mood", value)])
        for key, value in responses.items()
      ],
      achievements=[Achievement(a, "00:00", None) for a in achievements],
      manager=manager,
      hearts=UsefulStrings.hearts["mood"],
      meta=dict(
        # new=True,
        demog=demog,
        code=code,
        lang=lang,
        groups=["olds"],
      ),
    )

  def dumps(self):
    d = {
      k: v
      for k, v in asdict(self).items()
      if k
      not in ("manager", "achievements", "days", "polls", "gptuser", "groups")
    }
    d["days"] = [day.to_dict() for day in self.days]
    d["achievements"] = [ach.to_dict() for ach in self.achievements]
    d["polls"] = [poll.to_dict() for poll in self.polls]
    d["lastday"] = self.lastday.to_dict()
    d["groups"] = list(self.groups)
    return d

  def dump(self, folder):
    with open(os.path.join(folder, "{}.json".format(self.user_id)), "w") as f:
      json.dump(self.dumps(), f, indent=4)

  @classmethod
  def load(cls, user_id: int, folder: str, manager: GptUserManager):
    with open(os.path.join(folder, "{}.json".format(str(user_id)))) as f:
      data = json.load(f)
    return User.from_dict(data, manager)


@dataclass
class AggregatedData:
  total: int
  count: int

  def to_dict(self):
    return dict(total=self.total, count=self.count)

  def average(self):
    if self.count < ARBITRARY_THRESHOLD:
      return None
    return round(self.total / self.count)

  def add(self, score):
    self.total += score
    self.count += 1


@dataclass
class TrackingMessage:
  chat_id: int
  message_id: int
  tpe: str
  current_txt: str

  def to_dict(self):
    return asdict(self)


@dataclass
class Tracker:
  date: str
  types_data: dict[str, AggregatedData] = field(default_factory=dict)
  tr_messages: list[TrackingMessage] = field(default_factory=list)

  def dump(self, path):
    with open(path, "w") as file:
      json.dump(
        {
          "date": self.date,
          "types_data": {
            tpe: agg.to_dict() for tpe, agg in self.types_data.items()
          },
          "tr_messages": [tm.to_dict() for tm in self.tr_messages],
        },
        file,
      )

  @classmethod
  def load(cls, path):
    if not os.path.exists(path):
      return cls(time.strftime(DATE_FORMAT))
    with open(path) as file:
      data = json.load(file)
    return cls(
      date=data["date"],
      types_data={
        tpe: AggregatedData(**agg) for tpe, agg in data["types_data"].items()
      },
      tr_messages=[TrackingMessage(**tr) for tr in data["tr_messages"]],
    )


@dataclass
class Group:
  name: str
  description: str
  user_list: InitVar[list[int]]
  users: set[int] = field(init=False)

  def __post_init__(self, user_list: list[int]):
    self.users = set(user_list)

  def to_dict(self):
    return dict(
      name=self.name, description=self.description, user_list=list(self.users)
    )


class UserManager:
  @dataclass
  class SignedPoll(Poll):
    user_id: int

  @property
  def __today(self):
    return time.strftime(DATE_FORMAT)

  def __init__(self, secret: dict[str, str], manager: GptUserManager) -> None:
    self.users: dict[int, User] = {}
    self.manager = manager
    self.folder = secret["RESPONSES_FOLDER"]
    self.__track_file = secret["TRACK_FILE"]
    self.tracker = Tracker.load(self.__track_file)
    self.__groups_file = secret["GROUPS_FILE"]
    for userfile in os.listdir(self.folder):
      with open(os.path.join(self.folder, userfile), encoding="utf-8") as file:
        d = json.load(file)
      user = User.from_dict(d, manager)
      self.users[user.user_id] = user
    with open(self.__groups_file, encoding="utf-8") as file:
      self.groups: dict[str, Group] = {
        gid: Group(**group) for gid, group in json.load(file).items()
      }

  def dump_groups(self):
    with open(self.__groups_file, "w", encoding="utf-8") as file:
      json.dump(
        {gid: group.to_dict() for gid, group in self.groups.items()},
        file,
        indent=4,
        ensure_ascii=False,
      )

  def add_user_to_group(self, uid, gid):
    assert uid in self.users, "User {} not in users!".format(uid)
    assert gid in self.groups, "Group {} not in groups!".format(gid)
    groups = self.users[uid].groups
    group = self.groups[gid]
    group.users.add(uid)
    groups.add(gid)
    self.dump_user(uid)
    self.dump_groups()

  def rm_user_from_group(self, uid, gid):
    assert uid in self.users, "User {} not in users!".format(uid)
    assert gid in self.groups, "Group {} not in groups!".format(gid)
    groups = self.users[uid].groups
    group = self.groups[gid]
    if uid in group.users:
      group.users.remove(uid)
    if gid in groups:
      groups.remove(gid)
    self.dump_user(uid)
    self.dump_groups()

  def is_user_verified(self, user_id):
    if user_id not in self.users:
      return False
    if "verified" not in self.users[user_id].meta:
      self.users[user_id].meta["verified"] = False
      self.dump_user(user_id)
    return self.users[user_id].meta["verified"]

  def needed_polls_stack(self):
    for user_id in self.users:
      if self.users[user_id].meta.get("disabled"):
        continue
      if self.users[user_id].last_response_was_long_ago():
        self.users[user_id].meta["disabled"] = True
      else:
        for poll_type in self.users[user_id].polls_pending():
          yield (user_id, poll_type)
      self.dump_user(user_id)

  def needed_reminds_stack(self):
    for user_id in self.users:
      if self.users[user_id].meta.get("disabled"):
        continue
      if self.users[user_id].reminder_needed():
        yield user_id

  def get_lang(self, user: types.User):
    """Get the language code for chosen User instance"""
    if user.id not in self.users:
      if user.language_code in ("ru", "en"):
        return user.language_code
      else:
        return "en"
    poll_user = self.users[user.id]
    if "lang" not in poll_user.meta:
      if user.language_code in ("ru", "en"):
        poll_user.meta["lang"] = user.language_code
      else:
        poll_user.meta["lang"] = "en"
      self.dump_user(user.id)
    return poll_user.meta["lang"]

  def send_polls(self, bot: Telebot):
    if time.localtime().tm_min % 5 != 0:
      return
    for user_id, tpe in self.needed_polls_stack():
      self.send_poll(bot, user_id, tpe, self.users[user_id].meta.get("lang", "ru"))
    for user_id in self.needed_reminds_stack():
      lang = self.users[user_id].meta.get("lang", "ru")
      bot.send_message(user_id, service[lang]["reminder"])

  def track(self, tpe, score):
    if self.tracker.date != self.__today:
      self.tracker = Tracker(self.__today)
    if tpe not in self.tracker.types_data:
      self.tracker.types_data[tpe] = AggregatedData(score, 1)
    else:
      self.tracker.types_data[tpe].add(score)
    self.dump_tracker()

  def send_poll(self, bot: Telebot, user_id, tpe: str = "mood", lang="ru", manual=False):
    if tpe == "mood":
      hearts = self.users[user_id].hearts
    else:
      hearts = UsefulStrings.hearts[tpe]  # Update to retrieve from user_settings
    if lang is None:
      lang = "en"
    scale: str = service[lang]["poll"][tpe]
    if tpe == "mood":
      scale = scale.format(*hearts)
    text = f'{self.__today}\n{scale}'
    markup = types.InlineKeyboardMarkup([[
      types.InlineKeyboardButton(
        hearts[i], callback_data=f"DS_{tpe[0]}_{i}"
      )
      for i in range(7)
    ]])
    try:
      bot.send_message(user_id, text, reply_markup=markup)
      if not manual:
        self.users[user_id].lastday.register_poll(tpe)
    except ApiException:
      self.users[user_id].polls = []
      # dab_upd(STATUS_FILE, user_id, None)

  def forced_polls(self, bot):
    for uid, tpe in self.needed_polls_stack():
      self.send_poll(bot, uid, tpe, self.users[uid].meta.get("lang", "ru"))

  def dump_tracker(self):
    self.tracker.dump(self.__track_file)

  # def agg_today(self, tpe, nums=None):
  #   if self.agg['date'] != self.__today:
  #     return None
  #   return self.agg[tpe].average(nums)
    
  def dem_response(self, user_id, key, answer):
    user = self.users[user_id]
    if "demog" not in user.meta:
      user.meta["demog"] = {}
    user.meta["demog"].update({key: answer})
    self.dump_user(user_id)

  def new_response(self, user_id: int, tpe: str, score: int):
    self.users[user_id].response(tpe, score)
    self.track(tpe, score)
    self.dump_user(user_id)

  def dump_user(self, user_id: int):
    self.users[user_id].dump(self.folder)

  def new_user(
    self,
    user_id: int,
    username: Optional[str] = None,
    firstname: Optional[str] = None,
    **kwargs
  ):
    if user_id in self.users:
      raise KeyError("User {} is already in manager".format(user_id))
    self.users[user_id] = User(
      user_id,
      username,
      firstname,
      polls=[],
      days=[],
      achievements=[],
      manager=self.manager,
      lastday=LastDay.denovo(),
      hearts=UsefulStrings.hearts["mood"],
      meta=kwargs,
    )
    self.dump_user(user_id)
    return self.users[user_id]

  def rm_user(self, user_id):
    if user_id not in self.users:
      warnings.warn(
        "User {} is not in manager. Deletion failed.".format(user_id)
      )
    del self.users[user_id]
    os.remove(os.path.join(self.folder, "{}.json".format(user_id)))

  def update_admin(self, bot: Telebot, tpe, ADMIN: int):
    hearts = UsefulStrings.hearts
    tpe_data = [
      (
        tpe,
        self.tracker.types_data[tpe].count,
        self.tracker.types_data[tpe].total,
      )
      for tpe in self.tracker.types_data
    ]
    text = "{}\n{}".format(
      time.strftime(DATE_FORMAT),
      "\n".join([
        "\n".join((
          "Статистика по {}:".format(tpe),
          "Ответов: {}, Среднее: {}".format(
            cnt, UsefulStrings.hearts[tpe][round(ttl / cnt)]
          ),
        ))
        for tpe, cnt, ttl in tpe_data
      ]),
    )
    if (
      not self.tracker.tr_messages
      or self.tracker.tr_messages[0].chat_id != ADMIN
    ):
      message = bot.send_message(ADMIN, text)
      assert message.text is not None
      self.tracker.tr_messages.insert(
        0, TrackingMessage(ADMIN, message.id, "ADMIN", message.text)
      )
      self.dump_tracker()
      return
    if self.tracker.tr_messages[0].current_txt == text:
      return
    try:
      bot.edit_message_text(text, ADMIN, self.tracker.tr_messages[0].message_id)
    except ApiTelegramException:
      message = bot.send_message(ADMIN, text)
      assert message.text is not None
      self.tracker.tr_messages.insert(
        0, TrackingMessage(ADMIN, message.id, "ADMIN", message.text)
      )
      self.dump_tracker()
    for tracker in self.tracker.tr_messages:
      if tracker.tpe != tpe:
        continue
      if text == tracker.current_txt:
        continue
      a = self.users.get(tracker.chat_id, None)
      if a is None:
        lang = "en"
      else:
        lang = a.meta.get("lang", "en")
      try:
        avg = self.tracker.types_data[tpe].average()
        if avg is None:
          avg = 0
        if type(avg) == float:
          avg = int(avg)
        bot.edit_message_text(
          service[lang]["today_text"].format(
            tpe,
            hearts[tpe][avg],
          ),
          tracker.chat_id,
          tracker.message_id,
        )
      except ApiTelegramException:
        print("It failed. Again :<")
    return
