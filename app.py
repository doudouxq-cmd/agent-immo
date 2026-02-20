from flask import Flask, render_template, request, jsonify
import anthropic
import os
import json
from datetime import datetime
from dotenv import load_dotenv

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

app = Flask(__name__)
client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
conversations = {}

@app.route('/')
def index():
    return render_template('index.html')

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
Une fois toutes les infos collectées, confirme le rendez-vous clairement au client.""",
        messages=conversations[session_id]
    )

    reply = response.content[0].text
    conversations[session_id].append({"role": "assistant", "content": reply})

    return jsonify({"response": reply})

if __name__ == '__main__':
    app.run(debug=True)