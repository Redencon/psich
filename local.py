import yaml
from typing import Any, Literal
from telebot import TeleBot, types


TextPack = dict[str, dict[str, Any]]


class UsefulStrings:
    def __init__(self) -> None:
        raise NotImplementedError("No object of this class should be created")

    colorcoding = ["🟥", "🟧", "🟨", "🟩", "🟦", "🟪", "🟫", "⬜"]
    hearts = {
        "mood": ["❤️", "🧡", "💛", "💚", "💙", "💜", "❤️‍🩹"],
        "health": ["🔴", "🟠", "🟡", "🟢", "🔵", "🟣", "🟤"],
    }
    poll_types = {"mood": "🌠", "health": "💊", "FINCHY": "🐺"}
    poll_list = ["mood", "health"]

class LocalizedStrings:
    def __init__(self, loc_file = "loc.yaml") -> None:
        with open(loc_file, "r", encoding="utf-8") as file:
            all_text = yaml.safe_load(file)
            assert all_text is not None
        self.service: TextPack = {key: all_text[key]["service"] for key in all_text}
        self.commands: TextPack = {key: all_text[key]["commands"] for key in all_text}
        self.respons_texts: dict[str, dict[int, list[str]]] = {
            key: all_text[key]["responses"] for key in all_text
        }
        self.achievements: TextPack = {key: all_text[key]["achievements"] for key in all_text}
        self.help: TextPack = {key: all_text[key]["help"] for key in all_text}

    def setup_bot(self, bot: TeleBot, scope: types.BotCommandScope = types.BotCommandScopeDefault()):
        for lang in ("ru", "en"):
            bot.delete_my_commands(scope=scope, language_code=lang)
            bot.set_my_commands(
                [
                    types.BotCommand(command, self.commands[lang][command])
                    for command in self.commands[lang]
                ],
                scope=scope,
                language_code=lang,
            )

    def get_help(self, lang: Literal["ru", "en"], key: str) -> str:
        return self.help[lang][key]

    def is_in_help(self, key):
        return key in self.help["ru"]