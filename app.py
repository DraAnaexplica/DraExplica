import os
import requests
from flask import Flask, request, jsonify
from dotenv import load_dotenv

# Carregar .env
load_dotenv()
app = Flask(__name__)

# Configurações
ZAPI_INSTANCE_ID = os.getenv('ZAPI_INSTANCE_ID')
ZAPI_CLIENT_TOKEN = os.getenv('ZAPI_CLIENT_TOKEN')
OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')
OPENROUTER_MODEL = os.getenv('OPENROUTER_MODEL', 'openai/gpt-3.5-turbo')

ZAPI_SEND_TEXT_URL = f"https://api.z-api.io/instances/{ZAPI_INSTANCE_ID}/client-token/{ZAPI_CLIENT_TOKEN}/send-text"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# Função IA
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
        return response.json()['choices'][0]['message']['content']
    except Exception as e:
        print(f"[ERRO] OpenRouter: {e}")
        return None

# Enviar resposta via Z-API
def send_zapi_message(phone_number, message_text):
    headers = {"Content-Type": "application/json"}
    payload = {"phone": phone_number, "message": message_text}
    try:
        print(f"📤 Enviando resposta para {phone_number}: {message_text[:60]}...")
        response = requests.post(ZAPI_SEND_TEXT_URL, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        return True
    except Exception as e:
        print(f"[ERRO] Envio Z-API: {e}")
        return False

# Webhook
@app.route('/webhook', methods=['POST'])
def zapi_webhook():
    try:
        data = request.get_json(force=True)
        print("\n=== Webhook Recebido ===")
        print(data)

        from_me = data.get("fromMe", False)
        sender_phone = data.get("phone")
        user_message = data.get("texto", {}).get("mensagem")

        print(f"-> user_message: {user_message}, sender_phone: {sender_phone}, from_me: {from_me}")

        if from_me or not user_message or not sender_phone:
            print("⚠️ Ignorado: mensagem vazia, enviada por mim ou sem telefone.")
            return jsonify({"status": "ignored"}), 200

        ai_response = get_openrouter_response(user_message)

        if ai_response:
            send_zapi_message(sender_phone, ai_response)
        else:
            print("⚠️ Falha ao obter resposta da IA.")

    except Exception as e:
        print(f"[ERRO] Webhook: {e}")
        return jsonify({"status": "erro"}), 500

    return jsonify({"status": "success"}), 200

# Execução local
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)
