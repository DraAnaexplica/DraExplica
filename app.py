import os
import requests
from flask import Flask, request, jsonify
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)

ZAPI_INSTANCE_ID = os.getenv('ZAPI_INSTANCE_ID')
ZAPI_INSTANCE_TOKEN = os.getenv('ZAPI_INSTANCE_TOKEN')
ZAPI_CLIENT_TOKEN = os.getenv('ZAPI_CLIENT_TOKEN')
OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')
OPENROUTER_MODEL = os.getenv('OPENROUTER_MODEL', 'openai/gpt-3.5-turbo')

ZAPI_SEND_TEXT_URL = f"https://api.z-api.io/instances/{ZAPI_INSTANCE_ID}/token/{ZAPI_INSTANCE_TOKEN}/send-text"
ZAPI_REGISTER_WEBHOOK_URL = f"https://api.z-api.io/instances/{ZAPI_INSTANCE_ID}/token/{ZAPI_INSTANCE_TOKEN}/update-webhook-received"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

def get_openrouter_response(message_text):
    try:
        response = requests.post(
            OPENROUTER_URL,
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": OPENROUTER_MODEL,
                "messages": [{"role": "user", "content": message_text}]
            },
            timeout=60
        )
        response.raise_for_status()
        return response.json()['choices'][0]['message']['content']
    except Exception as e:
        print(f"[ERRO IA] {e}")
        return None

def send_zapi_message(phone_number, message_text):
    try:
        response = requests.post(
            ZAPI_SEND_TEXT_URL,
            headers={
                "Content-Type": "application/json",
                "client-token": ZAPI_CLIENT_TOKEN
            },
            json={
                "phone": phone_number,
                "message": message_text
            },
            timeout=30
        )
        response.raise_for_status()
        return True
    except Exception as e:
        print(f"[ERRO ENVIO Z-API] {e}")
        return False

@app.route('/webhook', methods=['POST'])
def zapi_webhook():
    try:
        data = request.get_json(force=True)
        print("\n📩 Webhook recebido:")
        print(data)

        from_me = data.get("fromMe", False)
        phone = data.get("phone")
        message = data.get("texto", {}).get("mensagem")

        print(f"Mensagem: {message} | Telefone: {phone} | fromMe: {from_me}")

        if from_me or not phone or not message:
            print("⚠️ Ignorado: mensagem vazia, enviada por mim ou sem telefone.")
            return jsonify({"status": "ignored"}), 200

        resposta = get_openrouter_response(message)
        if resposta:
            send_zapi_message(phone, resposta)

    except Exception as e:
        print(f"[ERRO WEBHOOK] {e}")

    return jsonify({"status": "ok"}), 200

@app.route('/registrar-webhook', methods=['GET'])
def registrar_webhook():
    try:
        response = requests.put(
            ZAPI_REGISTER_WEBHOOK_URL,
            headers={
                "Content-Type": "application/json",
                "client-token": ZAPI_CLIENT_TOKEN
            },
            json={
                "value": "https://draana-whatsapp.onrender.com/webhook"
            },
            timeout=30
        )
        print(f"[REGISTRO] Status {response.status_code} - {response.text}")
        return jsonify({"status": "feito", "zapi_response": response.text})
    except Exception as e:
        return jsonify({"erro": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))
