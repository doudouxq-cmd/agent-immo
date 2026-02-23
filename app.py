from flask import Flask, render_template, request, jsonify
import anthropic
import os
import json
from datetime import datetime
from dotenv import load_dotenv
from twilio.rest import Client as TwilioClient

load_dotenv()

def charger_biens():
    with open("biens.json", "r") as f:
        return json.load(f)

def biens_en_texte():
    biens = charger_biens()
    texte = "Voici les biens disponibles dans notre agence :\n\n"
    for b in biens:
        if b["disponible"]:
            texte += f"- {b['type']} {b['pieces']} pièces, {b['surface']}m², {b['prix']}€, {b['quartier']} {b['ville']}. {b['description']}\n"
    return texte

def envoyer_sms(to, message):
    try:
        twilio_client = TwilioClient(
            os.getenv("TWILIO_ACCOUNT_SID"),
            os.getenv("TWILIO_AUTH_TOKEN")
        )
        twilio_client.messages.create(
            body=message,
            from_=os.getenv("TWILIO_NUMBER"),
            to=to
        )
        print(f"SMS envoyé à {to}")
    except Exception as e:
        print(f"Erreur SMS : {e}")

app = Flask(__name__)
client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
conversations = {}

@app.route('/')
def index():
    return render_template('index.html', agent_id=os.getenv("ELEVENLABS_AGENT_ID"))

@app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    session_id = data.get('session_id', 'default')
    user_message = data.get('message', '')

    if session_id not in conversations:
        conversations[session_id] = []

    conversations[session_id].append({"role": "user", "content": user_message})

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        system=f"""Tu es un agent immobilier virtuel professionnel et chaleureux.
Tu aides les clients à trouver des biens et à prendre des rendez-vous de visite.
Tu réponds toujours en français de manière concise et professionnelle.

{biens_en_texte()}

Quand un client veut visiter un bien, collecte son nom, téléphone, date souhaitée (format JJ/MM/AAAA HHhMM).
Une fois toutes les infos collectées, écris exactement sur une ligne :
RDV_CONFIRME|nom|telephone|date|bien""",
        messages=conversations[session_id]
    )

    reply = response.content[0].text
    conversations[session_id].append({"role": "assistant", "content": reply})

    if "RDV_CONFIRME|" in reply:
        parties = reply.split("RDV_CONFIRME|")[1].split("|")
        if len(parties) == 4:
            nom, telephone, date, bien = parties

            if telephone.startswith("06") or telephone.startswith("07"):
                telephone = "+33" + telephone[1:]

            envoyer_sms(
                telephone,
                f"Bonjour {nom}, votre visite pour {bien} est confirmée le {date}. À bientôt !"
            )

            envoyer_sms(
                os.getenv("AGENT_NUMBER"),
                f"Nouveau RDV : {nom} - {telephone} - {bien} - {date}"
            )

            reply = f"Parfait ! Votre rendez-vous est confirmé ✅\n👤 {nom}\n📞 {telephone}\n📅 {date}\n🏠 {bien}\n\nVous recevrez un SMS de confirmation."

    return jsonify({"response": reply})

if __name__ == '__main__':
    app.run(debug=True)