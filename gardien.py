import os
import json
import logging
import threading
from flask import Flask
import telebot
from groq import Groq

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Chargement des variables d'environnement
BOT_TOKEN = os.getenv("BOT_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
ADMIN_ID = os.getenv("ADMIN_ID")
GROUP_CHAT_ID = os.getenv("GROUP_CHAT_ID")
BOT_USERNAME = os.getenv("BOT_USERNAME", "").strip()

bot = telebot.TeleBot(BOT_TOKEN)

app = Flask(__name__)

DATA_FILE = "user_data.json"

def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logging.error(f"Erreur de lecture du fichier data: {e}")
    return {}

def save_data(data):
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logging.error(f"Erreur d'écriture du fichier data: {e}")

user_data = load_data()

SYSTEM_PROMPT = """Tu es 'Le Gardien du Repaire', une IA protectrice, intelligente, amicale et passionnée de pop-culture/manga.
Tes rôles :
1. Accueillir chaleureusement les membres.
2. Répondre de manière précise, vive et amusante aux questions des membres du groupe.
3. Garder un ton courtois mais ferme si nécessaire."""

@bot.message_handler(commands=['start', 'help', 'aide'])
def send_welcome(message):
    welcome_text = (
        "⚔️ **Salutations ! Je suis Le Gardien du Repaire.** ⚔️\n\n"
        "Je suis là pour veiller sur le groupe et discuter avec vous.\n"
        "Pose-moi tes questions ou mentionne-moi dans un groupe !"
    )
    bot.reply_to(message, welcome_text, parse_mode="Markdown")

@bot.message_handler(commands=['points'])
def show_points(message):
    user_id = str(message.from_user.id)
    pts = user_data.get(user_id, {}).get("points", 0)
    bot.reply_to(message, f"🏆 Tu possèdes **{pts} points** du Repaire !")

@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    # Attribution de points basique
    user_id = str(message.from_user.id)
    if user_id not in user_data:
        user_data[user_id] = {"points": 0}
    user_data[user_id]["points"] += 1
    save_data(user_data)

    # Vérification si le bot doit répondre (Message privé OU Mention/Réponse dans un groupe)
    is_private = message.chat.type == "private"
    is_reply_to_bot = (message.reply_to_message and 
                       message.reply_to_message.from_user and 
                       message.reply_to_message.from_user.id == bot.get_me().id)
    is_mentioned = False
    if message.text:
        is_mentioned = (f"@{BOT_USERNAME}".lower() in message.text.lower()) if BOT_USERNAME else False

    if is_private or is_reply_to_bot or is_mentioned:
        if not GROQ_API_KEY:
            bot.reply_to(message, "L'IA n'est pas configurée (clé GROQ_API_KEY manquante sur Render).")
            return

        clean_text = message.text
        if BOT_USERNAME:
            clean_text = clean_text.replace(f"@{BOT_USERNAME}", "").strip()

        try:
            bot.send_chat_action(message.chat.id, 'typing')
            
            client = Groq(api_key=GROQ_API_KEY)
            response = client.chat.completions.create(
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": clean_text}
                ],
                model="llama-3.1-8b-instant",
                temperature=0.7,
                max_tokens=800
            )
            reply = response.choices[0].message.content
            bot.reply_to(message, reply)
        except Exception as e:
            logging.error(f"Erreur Groq: {e}")
            bot.reply_to(message, f"Erreur de réponse IA : {str(e)}")

@app.route('/')
def home():
    return "Gardien AI OK", 200

def run_bot():
    bot.infinity_polling()

if __name__ == "__main__":
    t = threading.Thread(target=run_bot)
    t.start()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
