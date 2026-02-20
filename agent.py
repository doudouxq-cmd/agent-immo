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

def creer_evenement_calendar(service, nom, telephone, date_str, bien):
    evenement = {
        'summary': f'Visite - {bien}',
        'description': f'Client : {nom}\nTéléphone : {telephone}\nBien : {bien}',
        'start': {
            'dateTime': datetime.strptime(date_str, '%d/%m/%Y %Hh%M').strftime('%Y-%m-%dT%H:%M:00'),
            'timeZone': 'Europe/Paris',
        },
        'end': {
            'dateTime': datetime.strptime(date_str, '%d/%m/%Y %Hh%M').replace(hour=datetime.strptime(date_str, '%d/%m/%Y %Hh%M').hour + 1).strftime('%Y-%m-%dT%H:%M:00'),
            'timeZone': 'Europe/Paris',
        },
    }
    event = service.events().insert(calendarId='primary', body=evenement).execute()
    return event.get('htmlLink')

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
calendar_service = connecter_google_calendar()
historique = []

system_prompt = """Tu es un agent immobilier virtuel professionnel et chaleureux. 
Tu aides les clients à trouver des biens et à prendre des rendez-vous de visite.
Tu réponds toujours en français.

Quand un client souhaite visiter un bien ou prendre rendez-vous, tu dois collecter :
1. Son prénom et nom
2. Son numéro de téléphone
3. La date et heure souhaitée (format JJ/MM/AAAA HHhMM, ex: 15/03/2026 14h00)
4. Le bien qu'il souhaite visiter

Une fois ces infos collectées, confirme en écrivant exactement sur une ligne :
RDV_CONFIRME|nom|telephone|date|bien"""

print("Agent immobilier virtuel - tapez 'quit' pour quitter\n")

while True:
    user_input = input("Vous : ")
    
    if user_input.lower() == "quit":
        break
    
    historique.append({"role": "user", "content": user_input})
    
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        system=system_prompt,
        messages=historique
    )
    
    reply = response.content[0].text
    historique.append({"role": "assistant", "content": reply})
    
    if "RDV_CONFIRME|" in reply:
        parties = reply.split("RDV_CONFIRME|")[1].split("|")
        if len(parties) == 4:
            lien = creer_evenement_calendar(calendar_service, parties[0], parties[1], parties[2], parties[3])
            print(f"\nAgent : Parfait ! Votre rendez-vous est confirmé et ajouté à notre agenda ✅")
            print(f"  👤 {parties[0]}")
            print(f"  📞 {parties[1]}")
            print(f"  📅 {parties[2]}")
            print(f"  🏠 {parties[3]}")
            print(f"  🔗 {lien}\n")
    else:
        print(f"\nAgent : {reply}\n")