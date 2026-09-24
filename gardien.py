import os
import telebot
from flask import Flask
import threading

BOT_TOKEN = os.getenv("BOT_TOKEN")

bot = telebot.TeleBot(BOT_TOKEN)

@bot.message_handler(commands=['start', 'ping'])
def send_welcome(message):
    bot.reply_to(message, "Le nouveau Gardien est officiellement en ligne !")

@bot.message_handler(func=lambda message: True)
def echo_all(message):
    bot.reply_to(message, f"Test réussi ! Tu as écrit : {message.text}")

app = Flask(__name__)

@app.route('/')
def home():
    return "Gardien OK", 200

def run_bot():
    bot.infinity_polling()

if __name__ == "__main__":
    t = threading.Thread(target=run_bot)
    t.start()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
