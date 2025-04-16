import os
import requests
from flask import Flask, request, jsonify
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)

ZAPI_INSTANCE_ID = os.getenv('ZAPI_INSTANCE_ID')
ZAPI_CLIENT_TOKEN = os.getenv('ZAPI_CLIENT_TOKEN')
OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')
OPENROUTER_MODEL = os.getenv('OPENROUTER_MODEL', 'openai/gpt-3.5-turbo')

ZAPI_BASE_URL = f"https://api.z-api.io/instances/{ZAPI_INSTANCE_ID}/client-token/{ZAPI_CLIENT_TOKEN}"
ZAPI_SEND_TEXT_URL = f"{ZAPI_BASE_URL}/send-text"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


def get_openrouter_response(message_text):
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": OPENROUTER_MODEL,
        "messages": [{"role": "user", "content": message_text}]
    }
    try:
        response = requests.post(OPENROUTER_URL, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        data = response.json()
        return data.get('choices', [{}])[0].get('message', {}).get('content', '')
    except Exception as e:
        print(f"[ERRO] OpenRouter: {e}")
        return None


def send_zapi_message(phone_number, message_text):
    headers = {
        "Content-Type": "application/json"
    }
    payload = {
        "phone": phone_number,
        "message": message_text
    }
    try:
        print(f"✅ Enviando para {phone_number}: {message_text[:60]}...")
        response = requests.post(ZAPI_SEND_TEXT_URL, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        return True
    except Exception as e:
        print(f"[ERRO] ao enviar resposta Z-API: {e}")
        return False


@app.route('/webhook', methods=['POST'])
def zapi_webhook():
    try:
        data = request.get_json(force=True)
        print("\n=== Webhook Recebido ===")
        print(data)

        from_me = data.get("fromMe", False)
        phone = data.get("phone")
        texto = data.get("texto")

        if not texto or not isinstance(texto, dict):
            print("⚠️ Campo 'texto' ausente ou malformado.")
            return jsonify({"status": "ignored"}), 200

        user_message = texto.get("mensagem")

        print(f"-> user_message: {user_message}, phone: {phone}, from_me: {from_me}")

        if from_me or not user_message or not phone:
            print("⚠️ Ignorado: mensagem vazia, enviada por mim ou sem telefone.")
            return jsonify({"status": "ignored"}), 200

        ai_response = get_openrouter_response(user_message)

        if ai_response:
            send_zapi_message(phone, ai_response)
        else:
            print("⚠️ Falha ao obter resposta da IA.")

    except Exception as e:
        print(f"[ERRO] Processando webhook: {e}")

    return jsonify({"status": "success"}), 200


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
