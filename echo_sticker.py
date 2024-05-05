import telebot

# Replace 'YOUR_BOT_TOKEN' with your actual bot token
bot = telebot.TeleBot('6212049117:AAF47POmcEQbCjrVCCpaNn_qg-dWUvLXx4Y')

# Replace 'ADMIN_ID' with the ID of the admin user
ADMIN = 510206060

@bot.message_handler(content_types=['sticker'], func=lambda message: message.from_user.id == ADMIN)
def handle_sticker(message: telebot.types.Message):
    sticker = message.sticker
    assert isinstance(sticker, telebot.types.Sticker)
    sticker_info = f"Sticker ID: {sticker.file_id}\n"
    sticker_info += f"Sticker Emoji: {sticker.emoji}\n"
    sticker_info += f"Sticker File Size: {sticker.file_size} bytes\n"
    sticker_info += f"Sticker Set Name: {sticker.set_name}\n"
    
    bot.send_message(ADMIN, sticker_info)

bot.polling()

"""The result of this code for Australian Fairy Bread sticker:
Sticker ID: CAACAgIAAxkBAAIC6GY3fDOjGotqJyJQmcWDjGq93-g3AAIjJAAC8ZSZSUD6sScQHLfnNQQ
Sticker Emoji: 🇦🇺
Sticker File Size: 48264 bytes
Sticker Set Name: reden_trash
"""