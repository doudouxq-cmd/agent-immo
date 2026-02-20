from flask import Flask, render_template, request, jsonify
import anthropic
import os
from dotenv import load_dotenv

load_dotenv()

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
    
    conversations[session_id].append({
        "role": "user",
        "content": user_message
    })
    
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        system="""Tu es un agent immobilier virtuel professionnel et chaleureux pour une agence immobilière. 
        Tu aides les clients à trouver des biens et à prendre des rendez-vous de visite.
        Tu réponds toujours en français de manière concise et professionnelle.""",
        messages=conversations[session_id]
    )
    
    reply = response.content[0].text
    conversations[session_id].append({
        "role": "assistant",
        "content": reply
    })
    
    return jsonify({"response": reply})

if __name__ == '__main__':
    app.run(debug=True)