"""Handling of user responses

Goals:
- Store all responses of all users
- By request you can get by/user and aggregated response data
- Every day contains data about date, all responses (with timestamps),
the score, the type of score
- Every user has some metadata:
  - Username
  - UserID
  - Object for communication with MNVR
  - Achievements
  - Groups
  - Demography data
  - other?
"""

import os
import time
import json
from typing import Optional, Self
from gpt_users import User as GptUser, UserManager as GptUserManager
import achievements as acv


class User:
    class Day:
        def __init__(self, date: str, responses: list[tuple[str, str, int]]) -> None:
            self.date = date
            """date in format `yyyy-mm-dd`"""
            self.responses = responses
            """list of responses this day
            Each response is a tuple of time in `hh:mm`,
            response type and response score"""

        def to_dict(self):
            return list(self.date, [list(r) for r in self.responses])

    class Achievement:
        def __init__(
            self, name: str, timestamp: str, weight: Optional[int] = None
        ) -> None:
            self.name = name
            self.timestamp = timestamp
            self.weight = weight

        def to_dict(self):
            """`(name, timestamp, weight)`"""
            return list(self.name, self.timestamp, self.weight)

    def __init__(
        self,
        user_id: int,
        first_name: Optional[str],
        days: list,
        achievements: list,
        gptmanager: GptUserManager,
        meta: dict,
    ) -> None:
        self.days: list[User.Day] = days
        self.user_id = user_id
        self.first_name = first_name
        self.achievements = [User.Achievement(*a) for a in achievements]
        self.manager = gptmanager
        self.gptuser = self.set_gpt_user(gptmanager)
        self.meta = meta

    def set_gpt_user(self, manager: GptUserManager):
        """Add GptUser object to this Object instance

        Args:
            manager (GptUserManager): User Manager used by this bot

        Raises:
            AssertionError: no new user can be added after reaching the limit
        """
        user = manager.get_user_by_id(self.user_id)
        if user is None:
            user = manager.new_user(
                self.user_id,
                (self.first_name if self.first_name is not None else self.username),
            )
        assert (
            user is not None
        ), "Max user amount reached, can't add new user: {}!".format(self.username)
        self.gptuser = user

    def response(self, type: str, score: int):
        if not self.days or self.days[-1].date != time.strftime("%Y-%m-%d"):
            self.days.append(User.Day(time.strftime("%Y-%m-%d"), []))
        self.days[-1].responses.append(tuple(time.strftime("%H:%M"), type, score))
        # TODO: add achievements parsing

    @property
    def calendar(self):
        ret = {}
        for day in self.days:
            valid = [response[2] for response in day.responses if response[1] == "mood"]
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
            user_id=user_id,
            days=[
                User.Day(key, [("12:10", "mood", value)])
                for key, value in responses.items()
            ],
            achievements=[User.Achievement(a, "00:00") for a in achievements],
            gptmanager=manager,
            meta=dict(
                new=True,
                demog=demog,
                code=code,
                lang=lang,
                groups=["olds"],
            ),
        )

    def dump(self, folder):
        with open(
            os.path.join(folder, "{}.json".format(self.user_id)), "w", encoding="utf-8"
        ) as f:
            json.dump(
                dict(
                    user_id=self.user_id,
                    first_name=self.first_name,
                    days=[day.to_dict() for day in self.days],
                    achievements=[a.to_dict() for a in self.achievements],
                )
            )

    @classmethod
    def load(cls, user_id: int, folder: str, manager: GptUserManager):
        with open(
            os.path.join(folder, "{}.json".format(str(user_id))), encoding="utf-8"
        ) as f:
            data = json.load(f)
        if "meta" not in data:
            return cls.parse_old_data(data, user_id, manager)
