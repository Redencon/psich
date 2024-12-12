from __future__ import print_function

import base64
from email.message import EmailMessage

from smtplib import SMTP
import os
import random


def send_code(
    adress,
    smtp_s, smtp_p, smtp_u, smpt_w,
    domen="phystech.edu",
):
  if domen is not None:
    lis = adress.split("@")
    if len(lis) != 2:
      return None
    if lis[1] != domen:
      return -1
  new_code = random.randint(100000, 999999)
  text = f"""
Код подтверждения для бота МКИ:

{new_code}

Отправь этот код в виде ответа на сообщение бота, чтобы подтвердить свою личность.

Бот не хранит информацию о твоём почтовом ящике и использует её только для подтверждения личности.
После аутентификации информация о почтовом адресе будет удалена.

Если вы получили это сообщение по ошибке, можете смело удалять его.

---
МКИ — главная студенческая организция МФТИ.
Защищаем права студентов, реализуем проекты, направленные на развитие МФТИ и сообщества Физтеха. Мы — рупор студенческого комьюнити МФТИ.

Подписывайтесь на нас в ВК и Телеграме :)
https://vk.com/mki_mipt
https://t.me/mki_mipt """
  smtp_send_message(smtp_s, smtp_p, smtp_u, smpt_w, text, adress, "Код подтверждения для бота МКИ")
  return new_code


def smtp_send_message(smtp_s, smtp_p, smtp_u, smpt_w, text, adress, subject="Служебное сообщение от бота МКИ"):
  """Create and send an email message
  Print the returned  message id
  Returns: Message object, including message id

  Load pre-authorized user credentials from the environment.
  TODO(developer) - See https://developers.google.com/identity
  for guides on implementing OAuth2 for the application.
  """
  message = EmailMessage()

  message.set_content(text)

  message["To"] = adress
  message["From"] = smtp_u
  message["Subject"] = subject

  # encoded message
  encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()

  create_message = {"raw": encoded_message}
  # pylint: disable=E1101
  with SMTP(smtp_s, smtp_p) as server:
    server.starttls()
    server.login(smtp_u, smpt_w)
    server.sendmail(smtp_u, adress, message.as_string())

if __name__ == "__main__":
  import json
  with open("secret.json") as f:
    data = json.load(f)
  print(send_code(
    "pomogaev.dd@phystech.edu",
    data["SMTP_SERVER"],
    data["SMTP_PORT"],
    data["SMTP_USERNAME"],
    data["SMTP_PASSWORD"],
  ))
