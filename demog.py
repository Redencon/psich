import json

pool = {'ru': [
    ['sex', 'Ваш гендер?', ['Мужской', 'Женский', 'Другой']],
    ['ps', 'Физтех-школа?', ["ФПМИ", "ЛФИ", "ФАКТ", "ИАЛТ", "ФРКТ", "ФБМФ", "ФЭФМ", "ИНБИКСТ", "ФБВТ", "ВШПИ"]],
    ['year', 'С какого ты курса?', ['1', '2', '3', '4', '5', '6', '7+']],
    ['lgbt', 'Ваша сексуальная ориентация?', ['Гетеро', 'Гомо', 'Би', 'Ace', 'Пропустить']]
],
'en': [
    ['sex', 'Your gender?', ['Male', 'Female', 'Another']],
    ['ps', 'Where are you from?', ["Moscow", "Russia", "USA", "Canada", "Australia", "EU", "Another"]],
    ['year', 'Your age?', ['<18', '18-21', '22-28', '29-35', '35-45', '45-62', '>63']],
    ['lgbt', 'Your sexual orientation?', ['Hetero', 'Homo', 'Bi', 'Ace', 'Skip']]
]
}

with open('pool.json', 'w') as file:
    json.dump(pool, file, indent=2)
