import os
import requests
from flask import Flask, request, jsonify
from dotenv import load_dotenv

# Carrega variáveis do .env
load_dotenv()

# Inicializa o app Flask
app = Flask(__name__)

# --- Configurações ---
ZAPI_INSTANCE_ID = os.getenv("ZAPI_INSTANCE_ID")
ZAPI_CLIENT_TOKEN = os.getenv("ZAPI_CLIENT_TOKEN")
ZAPI_BASE_URL = f"https://api.z-api.io/instances/{ZAPI_INSTANCE_ID}/token/{ZAPI_CLIENT_TOKEN}"
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "google/gemini-2.0-flash-001")

# --- Endpoint do OpenRouter ---
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


def get_openrouter_response(message_text):
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": OPENROUTER_MODEL,
        "messages": [
            {"role": "user", "content": message_text}
        ]
    }
    try:
        response = requests.post(OPENROUTER_URL, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        data = response.json()
        return data.get("choices", [{}])[0].get("message", {}).get("content", "")
    except Exception as e:
        print(f"❌ Erro ao chamar OpenRouter: {e}")
        return None


def send_zapi_message(phone, message):
    headers = {
        "Content-Type": "application/json",
        "Client-Token": ZAPI_CLIENT_TOKEN
    }
    payload = {
        "phone": phone,
        "message": message
    }
    try:
        print(f"📤 Enviando mensagem para {phone}: {message}")
        response = requests.post(f"{ZAPI_BASE_URL}/send-text", json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        print("✅ Mensagem enviada com sucesso pela Z-API")
        return True
    except Exception as e:
        print(f"❌ Erro ao enviar mensagem pela Z-API: {e}")
        return False


@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()
    print("\n🔔 Webhook Recebido! (POST)")
    print("📦 Payload:", data)

    # Novos nomes reais conforme Z-API (ajustado ao seu payload)
    user_message = data.get("texto", {}).get("mensagem")
    sender_phone = data.get("telefone")
    from_me = data.get("fromMe", True)

    print(f"   -> Verificando: user_message='{user_message}', sender_phone='{sender_phone}', from_me={from_me}")

    if not user_message or not sender_phone or from_me:
        print("⚠️ Payload ignorado: sem mensagem, sem telefone ou enviado por mim.")
        return jsonify({"status": "ignored"}), 200

    ai_response = get_openrouter_response(user_message)
    if ai_response:
        send_zapi_message(sender_phone, ai_response)
    else:
        print("⚠️ OpenRouter não respondeu adequadamente.")

    return jsonify({"status": "success"}), 200


@app.route("/", methods=["GET"])
def health():
    return jsonify({"status": "ok", "message": "Servidor online."})


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5001))
    app.run(host="0.0.0.0", port=port)
