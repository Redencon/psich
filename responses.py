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
import json
from typing import Optional, Final
from gpt_users import User as GptUser, UserManager as GptUserManager
from dataclasses import dataclass, asdict, field
# import achievements as acv

MIN_POLL_DISTANCE: Final[int] = 60


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

    def to_dict(self): return asdict(self)


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

    def to_dict(self): return asdict(self)


@dataclass
class User:
    user_id: int
    username: Optional[str]
    first_name: Optional[str]
    polls: list[Poll]
    days: list[Day]
    achievements: list[Achievement]
    meta: dict
    manager: GptUserManager
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
                if key not in ('manager', 'achievements', 'days', 'polls')
            },
            days=[Day.from_dict(day) for day in d["days"]],
            achievements=[Achievement(**ach) for ach in d["achievements"]],
            polls=[Poll(**poll) for poll in d['polls']]
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

    def response(self, type: str, score: int):
        if not self.days or self.days[-1].date != time.strftime("%Y-%m-%d"):
            self.days.append(Day(time.strftime("%Y-%m-%d"), []))
        self.days[-1].responses.append(Response(time.strftime('%H:%M'), type, score))
        # tuple(time.strftime("%H:%M"), type, score))
        # TODO: add achievements parsing

    def add_poll(self, time: str, type: str):
        def far_enough(time1: str, time2: str) -> bool:
            h1, m1 = map(int, time1.split(':'))
            h2, m2 = map(int, time2.split(':'))
            mindiff = abs((h2-h1)*60 + m2-m1)
            return mindiff >= MIN_POLL_DISTANCE

        for poll in self.polls:
            if not far_enough(time, poll.time):
                return False
        self.polls.append(Poll(time, type))
        return True

    @property
    def calendar(self):
        ret = {}
        for day in self.days:
            valid = [response.score for response in day.responses if response.type == "mood"]
            ret[day.date] = round(sum(valid) / len(valid))
        return ret

    @staticmethod
    def parse_old_data(data: dict, user_id: int, manager: GptUserManager):
        demog = data["demog"]
        code = data["code"]
        lang = data["lang"]
        responses: dict[str, int] = data["responses"]
        achievements = data["achievements"]
        return User(
            polls=[Poll("12:10", "mood")],
            user_id=user_id,
            username=None,
            first_name=None,
            days=[
                Day(key, [Response("12:10", "mood", value)])
                for key, value in responses.items()
            ],
            achievements=[Achievement(a, "00:00", None) for a in achievements],
            manager=manager,
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
            if k not in ('manager', 'achievements', 'days', 'polls')
        }
        d['days'] = [day.to_dict() for day in self.days]
        d['achievements'] = [ach.to_dict() for ach in self.achievements]
        d['polls'] = [poll.to_dict() for poll in self.polls]
        return d

    def dump(self, folder):
        with open(
            os.path.join(folder, "{}.json".format(self.user_id)), "w", encoding="utf-8"
        ) as f:
            json.dump(self.dumps(), f, ensure_ascii=False, indent=4)

    @classmethod
    def load(cls, user_id: int, folder: str, manager: GptUserManager):
        with open(
            os.path.join(folder, "{}.json".format(str(user_id))), encoding="utf-8"
        ) as f:
            data = json.load(f)
        return User.from_dict(data, manager)


class UserManager:
    @dataclass
    class SignedPoll(Poll):
        user_id: int
    
    @dataclass
    class AggregatedData:
        pass

    def __init__(self, folder, manager: GptUserManager) -> None:
        self.users: dict[int, User] = {}
        self.manager = manager
        self.folder = folder
        for userfile in os.listdir(folder):
            with open(os.path.join(folder, userfile), encoding='utf-8') as file:
                d = json.load(file)
            user = User.from_dict(d, manager)
            self.users[user.user_id] = user
    
    def dump_user(self, user_id: int):
        self.users[user_id].dump(self.folder)
    
    def new_user(
            self,
            user_id: int,
            username: Optional[str] = None,
            firstname: Optional[str] = None,
            **kwargs
    ):
        if user_id in self.users: raise KeyError("User {} is already in manager".format(user_id))
        self.users[user_id] = User(
            user_id,
            username,
            firstname,
            polls=[],
            days=[],
            achievements=[],
            manager=self.manager,
            meta=kwargs
        )
        self.dump_user(user_id)
    
    def rm_user(self, user_id):
        if user_id not in self.users: raise KeyError("User {} is not in manager. Deletion failed.".format(user_id))
        del self.users(user_id)
        os.remove(os.path.join(self.folder, user_id))
