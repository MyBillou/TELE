import os
import json
import logging
from dotenv import load_dotenv
import openai
from telegram import Update, InputFile
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
import requests
import random
import asyncio  # pour le délai aléatoire

# Fichiers de persistence et médias
COUNTS_FILE = "tg_message_counts.json"
PHOTO_BASENAME = "special_photo"
AUDIO_BASENAME = "vocal_audio"

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Charger et positionner le working directory
load_dotenv()
script_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(script_dir)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not TELEGRAM_TOKEN or not OPENAI_API_KEY:
    logger.error("Variables TELEGRAM_TOKEN ou OPENAI_API_KEY manquantes.")
    raise ValueError("Veuillez définir TELEGRAM_TOKEN et OPENAI_API_KEY dans .env")

openai.api_key = OPENAI_API_KEY

# Prompts système
SYSTEM_PROMPT = (
    "Tu incarnes Irina, une jeune femme de 19 ans originaire de Bordeaux. "
    "Irina est sensuelle, coquine, mystérieuse et assume pleinement son charme. "
    "Elle écrit avec des phrases courtes, directes et sans utiliser d'emojis. "
    "Son style est séducteur, espiègle, parfois un peu provocant, mais jamais vulgaire. "
    "Elle prend le contrôle de la conversation : quand on lui demande 'ça va ?', elle ne retourne pas la question."
)
ALT_SYSTEM_PROMPT = (
    SYSTEM_PROMPT + " "
    
    "Si on te demande 'ou est ma plateforme' ou 'ou est ton mym', tu réponds : 'rejoins-moi sur mym.fans/elise_arjh avec le code promo 80% : ELISE80 😘 Bisousss 🥰'. "
    "Mini-Module de Réactions Avancées : "
    "➔ Je suis pas trop active ici... Si tu veux vraiment en profiter, rejoins-moi sur mym.fans/elise_arjh avec le code promo 80% : ELISE80 😘 Bisousss 🥰 "
)

# Fonctions de gestion des compteurs

def load_counts(path):
    if os.path.exists(path):
        try:
            return json.load(open(path, 'r', encoding='utf-8'))
        except:
            logger.warning(f"Impossible de lire {path}, initialisation vide.")
    return {}

def save_counts(path, data):
    try:
        json.dump(data, open(path, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Erreur sauvegarde compteurs: {e}")

# Génération de la réponse ChatGPT
def generate_reply(text, alt=False):
    prompt = ALT_SYSTEM_PROMPT if alt else SYSTEM_PROMPT
    try:
        resp = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role":"system","content":prompt},{"role":"user","content":text}],
            temperature=0.7, max_tokens=256
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"Erreur OpenAI: {e}")
        return f"Bonjour ! Merci pour votre message : \"{text}\""

# Détecter un fichier média par basename

def find_media(basename):
    for f in os.listdir(script_dir):
        name, ext = os.path.splitext(f)
        if name == basename and ext.lower() in ['.jpg','.jpeg','.png','.gif','.mp3','.ogg','.wav']:
            return os.path.join(script_dir, f)
    return None

# Handler des messages privés
async def handle_private(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = update.message.text or ''
    key = user.username or str(user.id)
    logger.info(f"Reçu de {key}: {text}")

    counts = context.bot_data.setdefault('counts', load_counts(COUNTS_FILE))
    now = counts.get(key, 0) + 1
    alt = now >= 8

        # Délai aléatoire entre 30 et 180 secondes avant de répondre
    delay = random.randint(30, 180)
    logger.info(f"Attente de {delay} secondes avant de répondre à {key}")
    await asyncio.sleep(delay)

    # Réponse textuelle
    reply = generate_reply(text, alt)
    await update.message.reply_text(reply)
    logger.info(f"Envoyé text à {key}")

    # 6ème message -> envoyer photo
    if now == 6:
        path = find_media(PHOTO_BASENAME)
        logger.info(f"DEBUG photo path={path}")
        if path:
            try:
                await update.message.reply_photo(photo=open(path,'rb'), caption="Une petite surprise pour toi...")
                logger.info(f"Photo envoyée à {key}")
            except Exception as e:
                logger.error(f"Echec envoi photo: {e}")
    # 7ème message -> envoyer audio
    if now == 7:
        path = find_media(AUDIO_BASENAME)
        logger.info(f"DEBUG audio path={path}")
        if path:
            try:
                await update.message.reply_audio(audio=open(path,'rb'), caption="mym.fans/elise_arjh Je viens de te faire un code promo 80%: CLA80 Bisousss")
                logger.info(f"Audio envoyé à {key}")
            except Exception as e:
                logger.error(f"Echec envoi audio: {e}")

    counts[key] = now
    save_counts(COUNTS_FILE, counts)

# Démarrage du bot

def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & filters.ChatType.PRIVATE, handle_private))
    logger.info("Bot Telegram démarré...")
    app.run_polling()

if __name__ == '__main__':
    main()

# Dépendances: pip install python-telegram-bot python-dotenv openai requests
