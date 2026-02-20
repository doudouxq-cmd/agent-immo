from flask import Flask, render_template, request, jsonify
import anthropic
import os
import json
from datetime import datetime
from dotenv import load_dotenv
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

load_dotenv()

SCOPES = ['https://www.googleapis.com/auth/calendar']

def connecter_google_calendar():
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    return build('calendar', 'v3', credentials=creds)

def creer_rdv_calendar(service, nom, telephone, date_str, bien):
    try:
        date_str = date_str.strip()
        # Ajoute l'année si manquante
        if len(date_str.split('/')) == 2:
            date_str = date_str.replace('/', '/2026/', 1) if 'h' not in date_str.split('/')[1] else date_str
        # Essaie plusieurs formats
        for fmt in ['%d/%m/%Y %Hh%M', '%d/%m %Hh%M', '%d/%m/%Y %Hh', '%d/%m %Hh']:
            try:
                dt = datetime.strptime(date_str, fmt)
                if dt.year == 1900:
                    dt = dt.replace(year=2026)
                break
            except:
                continue
        evenement = {
            'summary': f'Visite - {bien}',
            'description': f'Client : {nom}\nTéléphone : {telephone}',
            'start': {'dateTime': dt.strftime('%Y-%m-%dT%H:%M:00'), 'timeZone': 'Europe/Paris'},
            'end': {'dateTime': dt.replace(hour=dt.hour+1).strftime('%Y-%m-%dT%H:%M:00'), 'timeZone': 'Europe/Paris'},
        }
        event = service.events().insert(calendarId='primary', body=evenement).execute()
        return event.get('htmlLink')
    except Exception as e:
        print(f"Erreur Calendar : {e}")
        return None

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
calendar_service = connecter_google_calendar()
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
Une fois toutes les infos collectées, écris exactement sur une ligne :
RDV_CONFIRME|nom|telephone|date|bien""",
        messages=conversations[session_id]
    )

    reply = response.content[0].text
    conversations[session_id].append({"role": "assistant", "content": reply})

    lien_calendar = None
    if "RDV_CONFIRME|" in reply:
        parties = reply.split("RDV_CONFIRME|")[1].split("|")
        if len(parties) == 4:
            lien_calendar = creer_rdv_calendar(calendar_service, parties[0], parties[1], parties[2], parties[3])
            reply = f"Parfait ! Votre rendez-vous est confirmé ✅\n👤 {parties[0]}\n📞 {parties[1]}\n📅 {parties[2]}\n🏠 {parties[3]}"

    return jsonify({"response": reply, "calendar_link": lien_calendar})

if __name__ == '__main__':
    app.run(debug=True)