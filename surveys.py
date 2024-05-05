import os
import sys
import re
import json
import time
from dataclasses import dataclass
from typing import Any, TypedDict, Optional
from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup
import pickle


class QuestionInFile(TypedDict):
  question: str
  answers: list[str]
  meta: dict[str, Any]


class ConfigFile(TypedDict):
  code: str
  init: str
  questions: list[QuestionInFile]
  participants: list[int]
  final: Optional[str]


def convivnient_slicer(li, row_width=3):
  ret = [[]]
  for elem in li:
    if len(ret[-1]) == row_width:
      ret.append([])
    ret[-1].append(elem)
  return ret


@dataclass
class Question:
  question: str
  answers: list[str]
  meta: dict[str, Any]


class MessageArguments(TypedDict):
  text: str
  reply_markup: InlineKeyboardMarkup|None


class Survey:
  def __init__(self, config: dict) -> None:
    self.code: str = config["code"]
    self.questions: list[Question] = [Question(**q) for q in config["questions"]]
    self.answers: dict[int, list[str]] = dict()
    self.filename: str = config.get(
      "filename",
      "surveys/answers/{}_{}.json".format(self.code, time.strftime("%Y_%m_%d")),
    )
    self.init: str = config["init"]
    self.final: str = config.get("final", "END POLL\nThanks for participation!")
    self.participants: set[int] = set(config["participants"])
    self.load()

  def get_question(self, i: int) -> MessageArguments:
    if i == len(self.questions):
      return {"text": self.final, "reply_markup": None}
    return {
      "text": "Вопрос {} из {}:\n{}".format(
        i+1, len(self.questions), self.questions[i].question
      ),
      "reply_markup": InlineKeyboardMarkup(
        convivnient_slicer(
          [
            InlineKeyboardButton(
              text=answer,
              callback_data="SA_{}_{}_{}".format(self.code, i, j),
            )
            for j, answer in enumerate(self.questions[i].answers)
          ],
          (self.questions[i].meta["row_width"] if "row_width" in self.questions[i].meta else 3)
        )
      ),
    }

  def parse_response(self, uid: int, data: str) -> int:
    m = re.match(r"SA_([A-Za-z0-9]+)_([0-9]+)_([0-9]+)", data)
    if m is None:
      return -1
    code, qid, aid = m.groups()
    qid = int(qid)
    aid = int(aid)
    if qid >= len(self.questions):
      raise KeyError(
        "There is no such question! Tried to get question {} in survey {}".format(
          qid, code
        )
      )
    if aid >= len(self.questions[qid].answers):
      raise KeyError(
        "Answer index out of range! Tried to get answer {} for question {} in survey {}".format(
          aid, qid, code
        )
      )
    if uid not in self.answers:
      self.answers[uid] = ["None" for _ in range(len(self.questions))]
    self.answers[uid][qid] = self.questions[qid].answers[aid]
    self.dump()
    return 1

  def is_complete(self) -> bool:
    for uid in self.participants:
      if uid not in self.answers:
        return False
      if self.answers[uid][0] == "Declined":
        continue
      if any([ans == "None" for ans in self.answers[uid]]):
        return False
    return True

  def load(self):
    if not os.path.exists(self.filename):
      print("CREATED NEW FILE!")
      self.answers = {}
      return
    with open(self.filename) as file:
      self.answers = json.load(file)

  def dump(self):
    with open(self.filename, "w", encoding='utf-8') as file:
      json.dump(self.answers, file, indent=2, ensure_ascii=False)


class SurveyPool:
  def __init__(self, surveys_folder="surveys", data_file="data.bin") -> None:
    self.survey_folder = surveys_folder
    self.__data_path = os.path.join(self.survey_folder, data_file)
    if os.path.exists(self.__data_path):
      with open(self.__data_path, 'rb') as file:
        self.active_surveys: dict[str, Survey] = pickle.load(file)
      return
    self.active_surveys: dict[str, Survey] = {}

  def dump_surveys(self):
    for survey in self.active_surveys.values():
      survey.dump()
    if not self.active_surveys:
      if os.path.exists(self.__data_path):
        os.remove(self.__data_path)
      return
    with open(self.__data_path, 'wb') as file:
      pickle.dump(self.active_surveys, file)

  def spawn_survey(self, *, code: Optional[str] = None, config_filename: Optional[str] = None, **kwargs):
    if code is None:
      if config_filename is None:
        raise ValueError("No code for survey provided")
      filename = config_filename
    else:
      filename = "{}.json".format(code)
    if not os.path.exists(os.path.join(self.survey_folder, filename)):
      raise FileNotFoundError(f"There is no {os.path.join(self.survey_folder, filename)}")
      return None
    with open(os.path.join(self.survey_folder, filename)) as file:
      config: dict = json.load(file)
    config.update(kwargs)
    try:
      survey = Survey(config)
    except KeyError:
      print("Wrong config file", file=sys.stderr)
      return None
    if survey.code in self.active_surveys:
      print("Survey already active. Kill it before starting again", file=sys.stderr)
      return None
    self.active_surveys[survey.code] = survey
    self.dump_surveys()
    return survey
  
  def kill_survey(self, code):
    if code not in self.active_surveys:
      return False
    self.active_surveys[code].dump()
    self.active_surveys.pop(code)
    self.dump_surveys()
    return True
  
  def answer(self, uid: int, data: str):
    code = data.split("_")[1]
    if code not in self.active_surveys:
      return False
    self.active_surveys[code].parse_response(uid, data)
    self.dump_surveys()
    return True

  def user_declined(self, code, uid):
    self.active_surveys[code].answers[uid] = ["Declined"]
    self.active_surveys[code].dump()
    self.dump_surveys()
  
  def get_question(self, code, qid):
    ret = self.active_surveys[code].get_question(qid)
    if self.active_surveys[code].is_complete():
      self.kill_survey(code)
    self.dump_surveys()
    return ret
