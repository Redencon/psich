# Бот ежедневных опросов настроения
В данном репозитории находится исходный код, который используют два бота ежедневных опросов настроения: [Настенька](https://t.me/MKI_psi_bot) и [Диана](https://t.me/Redencon_psi_bot).

Основная идея ботов:
> Опрашивать людей о их текущем настроении так, чтобы это хотелось делать

Для этого сама процедура опроса по дизайну была сведена к нажатию одной кнопки, соответствующей интуитивно понятному возможному настроению из шкалы. Также для повышения заинтересованности вводятся дополнительные функции бота, такие как:
- статистика по предыдущим заполнениям
- возможность сравнить свой результат с другими пользователями
- система достижений *(и в дальнейшем опыта)*
- возможность общения с ботом

## Файлы
`demo_bot.py` - Боты запускаются с этого скрипта. нечто вроде `__init__` репозитория

`start.bat` - batch-скрипт, отваетственный за скачивание обновлений бота с сервера и запуск скрипта бота

---

`false_bot.py` - скрипт для использования интерфейса бота для отправления разовых сообщений

`achievements.py` - хранит класс для работы с достижениями. Сохраняет, уведомляет и проверяет достижения для пользователей.

`demog.py` - скрипт по созданию файла с данными для демографического опроса при регистрации

`gmail_send_message.py` - скрипт для отправки верификационного сообщения на почту

`gpt_users.py` - скрипт, примерно наполовину написанный с помощью ChatGPT, организующий анонимное общение между пользователями и операторами

`report.py` - скрипт для созтавления и отправки данных по опросу Админу

`quickstart.py` - скрипт от Google, используемый для получения токена `token.json` для отправки сообщения через GMail.

*Другие `.py` файлы используются для разовой обработки текущих данных и не используются основным скриптом*

---

`secret.json` - файл с инициирущими данными для бота. Не находятся в репозитории, но есть на машине-исполнителе. Там в том числе есть токен, с помощью которого скрипт привязывается к конкретному ТГ-боту.

`loc.yaml` - файл с текстом для сообщений на английском и русском языках


