import os
import requests
from flask import Flask, request, jsonify
from dotenv import load_dotenv

# Carregar variáveis do .env
load_dotenv()
app = Flask(__name__)

# --- Configurações ---
ZAPI_INSTANCE_ID = os.getenv('ZAPI_INSTANCE_ID')
ZAPI_CLIENT_TOKEN = os.getenv('ZAPI_CLIENT_TOKEN')
OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')
OPENROUTER_MODEL = os.getenv('OPENROUTER_MODEL', 'openai/gpt-3.5-turbo')

ZAPI_SEND_TEXT_URL = f"https://api.z-api.io/instances/{ZAPI_INSTANCE_ID}/token/{ZAPI_CLIENT_TOKEN}/send-text"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# --- Função IA ---
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

# --- Enviar mensagem via Z-API ---
def send_zapi_message(phone_number, message_text):
    headers = {
        "Content-Type": "application/json",
        "client-token": ZAPI_CLIENT_TOKEN  # Cabeçalho obrigatório
    }
    payload = {
        "phone": phone_number,
        "message": message_text
    }
    try:
        print(f"📤 Enviando para {phone_number}: {message_text[:60]}...")
        response = requests.post(ZAPI_SEND_TEXT_URL, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        return True
    except Exception as e:
        print(f"[ERRO] ao enviar resposta Z-API: {e}")
        return False

# --- Webhook principal ---
@app.route('/webhook', methods=['POST'])
def zapi_webhook():
    try:
        data = request.get_json(force=True)
        print("\n=== Webhook Recebido ===")
        print(data)

        from_me = data.get("fromMe", False)
        sender_phone = data.get("phone")
        texto = data.get("texto", {})

        user_message = texto.get("mensagem") if isinstance(texto, dict) else None

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

# --- ROTA PARA REGISTRAR O WEBHOOK AUTOMATICAMENTE ---
@app.route('/registrar-webhook', methods=['GET'])
def registrar_webhook():
    try:
        instance_id = ZAPI_INSTANCE_ID
        instance_token = ZAPI_CLIENT_TOKEN
        webhook_url = f"https://api.z-api.io/instances/{instance_id}/token/{instance_token}/update-webhook-received"

        payload = {
            "value": "https://draana-whatsapp.onrender.com/webhook"  # seu domínio no Render
        }

        headers = {
            "Content-Type": "application/json",
            "client-token": instance_token
        }

        response = requests.put(webhook_url, headers=headers, json=payload)
        print(f"[WEBHOOK] Status: {response.status_code} - {response.text}")

        return jsonify({
            "status": "Webhook registrado com sucesso",
            "zapi_response": response.text
        })

    except Exception as e:
        print(f"[ERRO] Registro do webhook: {e}")
        return jsonify({"erro": str(e)}), 500

# --- Execução local ---
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)
