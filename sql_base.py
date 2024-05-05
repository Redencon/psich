from sql_classes import *
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.exc import NoResultFound
from sqlalchemy import func
import time
from typing import Final
from local import UsefulStrings, LocalizedStrings
from telebot import types
from telebot import TeleBot as Telebot
from telebot.apihelper import ApiException, ApiTelegramException


DATE_FORMAT = "%Y-%m-%d"
MIN_POLL_DISTANCE: Final[int] = 60


class DatabaseManager:
  """SQLA database management"""

  def __init__(self, url="", debug=False) -> None:
    self.engine = create_engine(f"sqlite:///{url}", echo=debug)
    Base.metadata.create_all(self.engine)

  def _get_user_by_uid(self, session: Session, uid: int) -> User:
    user = session.scalars(
        select(User)
        .where(User.uid == uid)
      ).one()
    return user

  def add_response(self, uid: int, _type: str, score: int):
    with Session(self.engine) as session:
      user = self._get_user_by_uid(session, uid)
      
      # Record the score
      response = Response(
        user=user,
        date=time.strftime(DATE_FORMAT),
        time=time.strftime("%H:%M"),
        tpe=_type,
        score=score
      )
      session.add(response)
      session.commit()

  def get_today_status(self, uid):
    today = time.strftime(DATE_FORMAT)
    with Session(self.engine) as session:
      user = self._get_user_by_uid(session, uid)
      responses = session.scalars(
        select(Response)
        .where(Response.user == user)
        .where(Response.date == today)
      ).all()
      if not responses:
        return None
      c, s  = 0, 0
      for response in responses:
        c += 1
        s += response.score
      return round(s/c)
    

  def add_poll(self, uid: int, time: str, _type: str):
    def far_enough(time1: str, time2: str) -> bool:
      h1, m1 = map(int, time1.split(":"))
      h2, m2 = map(int, time2.split(":"))
      mindiff = abs((h2 - h1) * 60 + m2 - m1)
      return mindiff >= MIN_POLL_DISTANCE
    with Session(self.engine) as session:
      user = self._get_user_by_uid(session, uid)
      poll_times = session.scalars(
        select(Poll.time)
        .where(Poll.user == user)
        .where(Poll.tpe == _type)
      ).all()
      for time2 in poll_times:
        if not far_enough(time, time2):
          return False
      poll = Poll(user = user, time = time, tpe = _type)
      session.add(poll)
      session.commit()

  def rm_poll(self, uid, time, tpe):
    with Session(self.engine) as session:
      user = self._get_user_by_uid(session, uid)
      poll = session.scalars(
        select(Poll)
        .where(Poll.user == user)
        .where(Poll.time == time)
        .where(Poll.tpe == tpe)
      ).one()
      session.delete(poll)
      session.commit()

  def get_active_users(self):
    with Session(self.engine) as session:
      return session.scalars(
        select(Poll.uid)
        .distinct()
      ).all()

  def get_pending_polls(self, uid: int):
    def was_before(poll_time: str):
      poll_h, poll_m = map(int, poll_time.split(":"))
      now = time.localtime()
      now_h = now.tm_hour
      now_m = now.tm_min
      del now
      return now_h > poll_h or (now_h == poll_h and now_m >= poll_m)

    today = time.strftime(DATE_FORMAT)
    
    with Session(self.engine) as session:
      user = self._get_user_by_uid(session, uid)
      poll_types = session.scalars(
        select(Poll.tpe)
        .where(Poll.user == user)
        .distinct()
      ).all()
      needed_types: list[str] = []
      for tpe in poll_types:
        try:
          last_day = session.scalars(
            select(LastDay)
            .where(LastDay.tpe == tpe)
            .where(LastDay.user == user)
          ).one()
        except NoResultFound:
          last_day = LastDay(user=user, tpe=tpe, date=today)
          session.add(last_day)
        poll_times = session.scalars(
          select(Poll.time)
          .where(Poll.tpe == tpe)
          .where(Poll.user == user)
        ).all()
        polls_needed_for_today_count = 0
        for poll_time in poll_times:
          if was_before(poll_time):
            polls_needed_for_today_count += 1

        if last_day.date != today:
          # Date bump
          last_day.count = 0
          last_day.date = today
        session.commit()
        if last_day.count < polls_needed_for_today_count:
          needed_types.append(tpe)
    return needed_types

  def get_user_polls(self, uid):
    with Session(self.engine) as session:
      user = self._get_user_by_uid(session, uid)
      return session.scalars(
        select(Poll)
        .where(Poll.user == user)
      ).all()

  def get_user_timezone(self, uid):
    with Session(self.engine) as session:
      try:
        meta = session.scalars(
          select(Meta.value)
          .where(Meta.uid == uid)
          .where(Meta.key == "demog.place")
        ).one()
      except NoResultFound:
        return 0
    if meta is None:
      return 0
    if meta == "Australia":
      return 7
    if meta == "East coast America":
      return -11
    if meta == "West coast America":
      return -8
    if meta == "East Europe":
      return -1
    if meta == "West Europe":
      return -2
    if meta == "UK":
      return -3
    if meta == "Australia":
      return 7
    if meta in ("Moscow", "Russia"):
      return 0
    return 0
      
  def get_meta(self, uid: int, key: str) -> "str|None":
    with Session(self.engine) as session:
      try:
        return session.scalars(
          select(Meta.value)
          .where(Meta.uid == uid)
          .where(Meta.key == key)
        ).one()
      except NoResultFound:
        return None

  def set_meta(self, uid: int, key: str, value: str):
    with Session(self.engine) as session:
      try:
        meta = session.scalars(
          select(Meta)
          .where(Meta.uid == uid)
          .where(Meta.key == key)
        ).one()
        meta.value = value
      except NoResultFound:
        meta = Meta(uid=uid, key=key, value=value)
        session.add(meta)
      session.commit()

  def get_user_calendar(self, uid: int, tpe: str):
    with Session(self.engine) as session:
      user = self._get_user_by_uid(session, uid)
      scores = (
        session
        .query(func.avg(Response.score), Response.date)
        .where(Response.user == user)
        .where(Response.tpe == tpe)
        .group_by(Response.date)
      ).all()
    return {date: round(avg_score) for avg_score, date in scores}

  def get_user_calendar_string(self, uid, month, year, default=False):
    def days_in_month(month, year):
      if month == 2:
        if year % 4 == 0:
          return 29
        return 28
      if month in (1, 3, 5, 7, 8, 10, 12):
        return 31
      return 30
    user_calendar = self.get_user_calendar(uid, "mood")
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
      with Session(self.engine) as session:
        hearts = self._get_user_by_uid(session, uid).hearts.split("|")
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

  def get_user_hearts(self, uid: int) -> list[str]:
    with Session(self.engine) as session:
      return self._get_user_by_uid(session, uid).hearts.split("|")

  def set_user_hearts(self, uid: int, hearts: list[str]):
    with Session(self.engine) as session:
      user = self._get_user_by_uid(session, uid)
      user.hearts = "|".join(hearts)
      session.commit()

  def add_user_to_group(self, uid: int, tag: str):
    with Session(self.engine) as session:
      user = self._get_user_by_uid(session, uid)
      group = session.scalars(
        select(Group)
        .where(Group.tag == tag)
      ).one()
      group.users.append(user)
      session.commit()

  def rm_user_to_group(self, uid: int, tag: str):
    with Session(self.engine) as session:
      user = self._get_user_by_uid(session, uid)
      group = session.scalars(
        select(Group)
        .where(Group.tag == tag)
      ).one()
      group.users.remove(user)
      session.commit()

  def is_user_verified(self, uid: int):
    with Session(self.engine) as session:
      try:
        ver = session.scalars(
          select(Meta.value)
          .where(Meta.key == "verified")
          .where(Meta.uid == uid)
        )
      except NoResultFound:
        return False
      return ver == "True"

  def needed_polls_stack(self):
    polls: list[tuple[int, str]] = []
    with Session(self.engine) as session:
      users = session.scalars(select(User)).all()
    for user in users:
      for poll in self.get_pending_polls(user.uid):
        polls.append((user.uid, poll))
    return polls

  def get_lang(self, tb_user: types.User):
    with Session(self.engine) as session:
      tlc = tb_user.language_code
      try:
        user = self._get_user_by_uid(session, tb_user.id)
      except NoResultFound:
        if tlc in ("ru", "en"):
          return tlc
        else:
          return "en"
      try:
        lang = session.scalars(
          select(Meta)
          .where(Meta.uid == user.uid)
          .where(Meta.key == "lang")
        ).one()
      except NoResultFound:
        lang = Meta(
          uid=user.uid, key="lang",
          value=(
            "en"
            if tlc not in ("ru", "en")
            else tlc
          )
        )
        session.add(lang)
        session.commit()
      return lang.value

  def send_poll(
    self,
    bot: Telebot, uid: int,
    tpe: str = "mood", lang="ru", manual=False
  ):
    service = LocalizedStrings().service
    today = time.strftime(DATE_FORMAT)
    with Session(self.engine) as session:
      user = self._get_user_by_uid(session, uid)
      hearts = user.hearts.split("|")
    if tpe == "health":
      hearts = UsefulStrings.hearts[tpe]  # Update to retrieve from user_settings
    if lang is None:
      lang = "en"
    scale: str = service[lang]["poll"][tpe]
    if tpe == "mood":
      scale = scale.format(*hearts)
    text = f'{today}\n{scale}'
    markup = types.InlineKeyboardMarkup([[
      types.InlineKeyboardButton(
        hearts[i], callback_data=f"DS_{tpe[0]}_{i}"
      )
      for i in range(7)
    ]])
    try:
      bot.send_message(uid, text, reply_markup=markup)
      if not manual:
        with Session(self.engine) as session:
          user = self._get_user_by_uid(session, uid)
          try:
            last = session.scalars(
              select(LastDay)
              .where(LastDay.user == user)
              .where(LastDay.tpe == tpe)
            ).one()
          except NoResultFound:
            last = LastDay(user=user, tpe=tpe, date=today)
            session.add(last)
          if last.date != today:
            last.date = today
            last.count = 0
          last.count += 1
          session.commit()
    except ApiException:
      with Session(self.engine) as session:
        user = self._get_user_by_uid(session, uid)
        for poll in session.scalars(
          select(Poll)
          .where(Poll.user == user)
        ).all():
          session.delete(poll)
        session.commit()

  def send_polls(self, bot: Telebot):
    if time.localtime().tm_min % 5 != 0:
      return
    for user_id, tpe in self.needed_polls_stack():
      with Session(self.engine) as session:
        try:
          lang = session.scalars(
            select(Meta.value)
            .where(Meta.key == "lang")
            .where(Meta.uid == user_id)
          ).one()
        except NoResultFound:
          lang = "ru"
      self.send_poll(bot, user_id, tpe, lang)

  def update_admin(self, bot: Telebot, tpe, ADMIN: int):
    today = time.strftime(DATE_FORMAT)
    with Session(self.engine) as session:
      tpe_data = (
        session
        .query(
          Response.tpe,
          func.count(Response.score),
          func.sum(Response.score))
        .where(Response.date == today)
        .group_by(Response.tpe)
      ).all()
      text = "{}\n{}".format(
        today,
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
      try:
        adm_tracker = session.scalars(
          select(Tracker)
          .where(Tracker.tpe == "ADMIN")
        ).one()
      except NoResultFound:
        message = bot.send_message(ADMIN, text)
        assert message.text is not None
        adm_tracker = Tracker(
          tpe="ADMIN", chat_id=ADMIN,
          message_id=message.id, current_text=message.text)
        session.add(adm_tracker)
        session.commit()
      if adm_tracker.current_text == text:
        return
      try:
        bot.edit_message_text(text, ADMIN, adm_tracker.message_id)
      except ApiTelegramException:
        message = bot.send_message(ADMIN, text)
        assert message.text is not None
        adm_tracker.message_id = message.id
        adm_tracker.current_text = message.text
        session.commit()
      user_trackers = session.scalars(
        select(Tracker)
        .where(Tracker.tpe == tpe)
      ).all()
      # for tracker in user_trackers:
      #   try:
      #     a = session.scalars(
      #       select(Meta.value)
      #       .where(Meta.uid == tracker.chat_id)
      #       .where(Meta.key == "lang")
      #     ).one()
      #   except NoResultFound:
      #     a = "en"
      #   text = self.tracker_text(tpe, a)
      #   if text == tracker.current_text:
      #     continue
      #   try:
      #     bot.edit_message_text(
      #       text,
      #       tracker.chat_id,
      #       tracker.message_id,
      #     )
      #   except ApiTelegramException:
      #     print("It failed. Again :<")

  def tracker_text(self, tpe, lang):
    service = LocalizedStrings().service
    hearts = UsefulStrings.hearts
    today = time.strftime(DATE_FORMAT)
    with Session(self.engine) as session:
      tpe_data = (
        session
        .query(
          Response.tpe, func.count(Response.score),
          func.sum(Response.score))
        .where(Response.date == today)
        .group_by(Response.tpe)
      ).all()
    count, total = 0, 0
    for _tpe, cnt, ttl in tpe_data:
      if tpe == _tpe:
        count = cnt
        total = ttl
    if count == 0:
      avg = 0
    else:
      avg = round(total / count)
    return service[lang]["today_text"].format(
      tpe,
      hearts[tpe][avg],
    )

  def dem_response(self, uid, key, answer):
    with Session(self.engine) as session:
      dkey = f"demog.{key}"
      try:
        meta = session.scalars(
          select(Meta)
          .where(Meta.key == dkey)
          .where(Meta.uid == uid)
        ).one()
        meta.value = answer
      except NoResultFound:
        meta = Meta(uid=uid, key=dkey, value=answer)
        session.add(meta)
      session.commit()

  def dem_finished(self, uid):
    with Session(self.engine) as session:
      try:
        session.scalars(
          select(Meta)
          .where(Meta.uid == uid)
          .where(Meta.key == "demog.year")
        ).one()
        return True
      except NoResultFound:
        return False

  def dem_wipe(self, uid):
    with Session(self.engine) as session:
      meta = session.scalars(
        select(Meta)
        .where(Meta.uid == uid)
        .where(Meta.key.contains("demog"))
      ).all()
      for met in meta:
        session.delete(met)
      session.commit()

  def new_user(self, uid, username, firstname):
    with Session(self.engine) as session:
      try:
        user = self._get_user_by_uid(session, uid)
        return None
      except NoResultFound:
        user = User(
          uid=uid, username=username, firstname=firstname,
          hearts="|".join(UsefulStrings.hearts["mood"])
        )
        session.add(user)
        session.commit()
      session.expunge(user)
    return user

  def user_exists(self, uid: int):
    with Session(self.engine) as session:
      try:
        self._get_user_by_uid(session, uid)
        return True
      except NoResultFound:
        return False

  def add_tracker(self, cid: int, mid: int, tpe: str, txt: str):
    with Session(self.engine) as session:
      tracker = Tracker(
        chat_id=cid, message_id=mid, tpe=tpe, current_text=txt)
      session.add(tracker)
      session.commit()

  def rm_user(self, uid):
    with Session(self.engine) as session:
      try:
        user = self._get_user_by_uid(session, uid)
      except NoResultFound:
        return
      session.delete(user)
      session.commit()
