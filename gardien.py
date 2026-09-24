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

@bot.message_handler(commands=['titre'])
def titre(message):
    p = get_points(message.from_user.id)
    bot.reply_to(message, f"Ton titre actuel est : {get_title(p)} ({p} points).")

@bot.message_handler(commands=['classement'])
def classement(message):
    rows = top_points()
    if not rows: bot.reply_to(message, "Le classement est encore vide.")
    else:
        txt = "Classement du Repaire :\n"
        for i, (username, pts) in enumerate(rows, start=1): txt += f"{i}. {username or 'Anonyme'} — {pts} pts\n"
        bot.reply_to(message, txt)

pending_votes = {}

@bot.message_handler(commands=['vote'])
def vote(message):
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "Seul l'administrateur peut lancer un vote.")
        return
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2 or "|" not in parts[1]:
        bot.reply_to(message, "Usage : /vote <question> | <option1> | <option2> ...")
        return
    content = parts[1]
    question = content.split("|")[0].strip()
    options = [o.strip() for o in content.split("|")[1:] if o.strip()]
    if len(options) < 2:
        bot.reply_to(message, "Il faut au moins 2 options.")
        return
    markup = InlineKeyboardMarkup()
    for i, opt in enumerate(options): markup.add(InlineKeyboardButton(opt, callback_data=f"vote_{i}"))
    msg = bot.send_message(message.chat.id, f"Vote du Repaire : {question}\n\nOptions :", reply_markup=markup)
    pending_votes[msg.message_id] = {"question": question, "options": options, "counts": [0] * len(options)}

@bot.callback_query_handler(func=lambda call: call.data.startswith("vote_"))
def handle_vote(call):
    msg_id = call.message.message_id
    if msg_id not in pending_votes:
        bot.answer_callback_query(call.id, "Ce vote est terminé.")
        return
    idx = int(call.data.split("_")[1])
    pending_votes[msg_id]["counts"][idx] += 1
    bot.answer_callback_query(call.id, "Vote enregistré !")

@bot.message_handler(commands=['resultats'])
def resultats(message):
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "Seul l'admin peut clôturer.")
        return
    if not pending_votes:
        bot.reply_to(message, "Aucun vote en cours.")
        return
    txt = "Résultats du vote :\n"
    for msg_id, data in pending_votes.items():
        txt += f"\nQuestion : {data['question']}\n"
        for opt, count in zip(data['options'], data['counts']): txt += f"  • {opt} : {count} voix\n"
        winner_idx = data['counts'].index(max(data['counts']))
        txt += f"Gagnant : {data['options'][winner_idx]}\n"
    bot.send_message(message.chat.id, txt)
    pending_votes.clear()

def samedi_otaku():
    bot.send_message(GROUP_CHAT_ID, "C'est le Samedi Otaku, héros !\nAu programme : quiz anime, débats manga et défis du Repaire.\nQui est prêt ?")

scheduler = BackgroundScheduler()
scheduler.add_job(samedi_otaku, 'cron', day_of_week='sat', hour=18, minute=0)
scheduler.start()

@bot.message_handler(commands=['samedi'])
def next_samedi(message):
    bot.reply_to(message, "Le prochain Samedi Otaku aura lieu samedi à 18h00.\nPrépare tes arguments, Otaku.")

@bot.message_handler(commands=['admin'])
def call_admin(message):
    if message.from_user.id == ADMIN_ID:
        bot.reply_to(message, "Tu es déjà l'administrateur.")
        return
    bot.send_message(ADMIN_ID, f"Appel de {message.from_user.first_name} (ID: {message.from_user.id}) :\n{message.text.replace('/admin', '').strip()}")
    bot.reply_to(message, "Ton message a été transmis à l'administrateur, Otaku.")

@bot.message_handler(commands=['addpoints'])
def addpoints(message):
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "Seul l'admin peut faire cela.")
        return
    parts = message.text.split()
    if len(parts) != 3:
        bot.reply_to(message, "Usage : /addpoints <user_id> <points>")
        return
    try:
        uid = int(parts[1]); n = int(parts[2])
        add_points(uid, None, n)
        bot.reply_to(message, f"{n} points ajoutés à l'utilisateur {uid}.")
    except ValueError:
        bot.reply_to(message, "ID et points doivent être des nombres.")

@bot.message_handler(commands=['annonce'])
def annonce(message):
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "Seul l'admin peut faire une annonce.")
        return
    texte = message.text.replace("/annonce", "").strip()
    if not texte:
        bot.reply_to(message, "Usage : /annonce <message>")
        return
    bot.send_message(GROUP_CHAT_ID, f"Annonce du Gardien :\n{texte}")
    bot.reply_to(message, "Annonce publiée.")

BAD_WORDS = ["insulte1", "insulte2", "spam"]

@bot.message_handler(func=lambda m: True, content_types=['text'])
def chat(message):
    text = message.text or ""
    if text.startswith("/"): return

    if message.chat.type in ['group', 'supergroup']:
        text_lower = text.lower()
        for word in BAD_WORDS:
            if word in text_lower:
                try:
                    bot.delete_message(message.chat.id, message.message_id)
                    bot.send_message(message.chat.id, f"{message.from_user.first_name}, ce langage n'est pas digne du Repaire.")
                except Exception: pass
                return

    is_private = message.chat.type == 'private'
    mentioned = f"@{BOT_USERNAME}".lower() in text.lower()
    reply_to_bot = (message.reply_to_message and message.reply_to_message.from_user.id == bot.get_me().id)
    
    if not (is_private or mentioned or reply_to_bot): 
        return

    prompt = text.replace(f"@{BOT_USERNAME}", "").strip()
    
    try:
        completion = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT}, 
                {"role": "user", "content": f"Message de {message.from_user.first_name} : {prompt}"}
            ],
            temperature=0.8, 
            max_tokens=500
        )
        answer = completion.choices[0].message.content
    except Exception as e:
        logging.exception(e)
        answer = "Le Gardien est momentanément perturbé. Réessaie plus tard."

    bot.reply_to(message, answer)

app = Flask(__name__)

@app.route('/')
def health_check():
    return "Gardien en ligne", 200

def run_bot():
    bot.infinity_polling()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    init_db()
    print("Gardien en ligne.")
    bot_thread = threading.Thread(target=run_bot)
    bot_thread.start()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
