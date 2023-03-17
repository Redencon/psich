from __future__ import print_function

import base64
from email.message import EmailMessage

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.oauth2.credentials import Credentials
import os
import random

def send_code(adress, domen='phystech.edu'):
    if domen is not None:
        lis = adress.split('@')
        if len(lis) != 2:
            return None
        if lis[1] != domen:
            return -1
    new_code = random.randint(100000, 999999)
    text = f'''
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
https://t.me/mki_mipt '''
    gmail_send_message(text, adress, 'Код подтверждения для бота МКИ')
    return new_code




def gmail_send_message(text, adress, subject = 'Служебное сообщение от бота МКИ'):
    """Create and send an email message
    Print the returned  message id
    Returns: Message object, including message id

    Load pre-authorized user credentials from the environment.
    TODO(developer) - See https://developers.google.com/identity
    for guides on implementing OAuth2 for the application.
    """
    SCOPES = ['https://www.googleapis.com/auth/gmail.send']

    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)

    try:
        service = build('gmail', 'v1', credentials=creds)
        message = EmailMessage()

        message.set_content(text)

        message['To'] = adress
        message['From'] = 'mkibotowner@gmail.com'
        message['Subject'] = subject

        # encoded message
        encoded_message = base64.urlsafe_b64encode(message.as_bytes()) \
            .decode()

        create_message = {
            'raw': encoded_message
        }
        # pylint: disable=E1101
        send_message = (service.users().messages().send
                        (userId="me", body=create_message).execute())
        print(F'Message Id: {send_message["id"]}')
    except HttpError as error:
        print(F'An error occurred: {error}')
        send_message = None
    return send_message


if __name__ == '__main__':
    print(send_code('pomogaev.dd@phystech.edu'))