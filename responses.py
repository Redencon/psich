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

from gpt_users import User as GptUser
from typing import Optional


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
            return list(self.name, self.timestamp, self.weight)

    def __init__(
        self,
        user_id: int,
        username: str,
        days: list,
        achievements: list,
        gptuser: GptUser,
        meta: dict,
    ) -> None:
        self.days = days
        self.user_id = user_id
        self.username = username
        self.achievements = achievements
        self.gptuser = gptuser
        self.meta = meta
