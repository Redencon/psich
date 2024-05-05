import json

pool = {
  "ru": [
    ["sex", "Ваш гендер?", ["Мужской", "Женский", "Другой"]],
    [
      "loc",
      "Откуда ты?",
      [
        "Москва",
        "Санкт-Петербург",
        "Краснодар",
        "Другое (Россия)",
        "Не из России",
      ],
    ],
    ["year", "Сколько теб лет?", ["<18", "18-21", "22-28", "29-35", "35-45", "45-62", ">63"],],
    [
      "lgbt",
      "Ваша сексуальная ориентация?",
      ["Гетеро", "Гомо", "Би", "Ace", "Пропустить"],
    ],
  ],
  "en": [
    ["sex", "Your gender?", ["Male", "Female", "Another"]],
    [
      "ps",
      "Where are you from?",
      ["Moscow", "Russia", "USA", "Canada", "Australia", "EU", "Another"],
    ],
    [
      "year",
      "Your age?",
      ["<18", "18-21", "22-28", "29-35", "35-45", "45-62", ">63"],
    ],
    ["lgbt", "Your sexual orientation?", ["Hetero", "Homo", "Bi", "Ace", "Skip"]],
  ],
}

with open("pool2.json", "w") as file:
  json.dump(pool, file, indent=2)
