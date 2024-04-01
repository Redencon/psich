import json
from typing import Literal

from achievements import streak
from telebot import TeleBot


class Experience:
  def __init__(self, RESPONSES_FOLDER: str, bot: TeleBot) -> None:
    self.__responses_folder = RESPONSES_FOLDER
    pass

  def _add_experience(self, user_id: int, amount: int):
    '''Add experience to user and level up in process'''
    pass

  def _lvlup(self, user_id: int):
    '''Raise a level of a user by 1'''
    pass

  @staticmethod
  def lvl_scaling(level: int) -> int:
    '''Return the amount of exp needed to complete a level'''
