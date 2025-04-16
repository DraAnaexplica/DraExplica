# app.py (Versão Corrigida com Detecção Inteligente de Mensagem Z-API)
import os
import json
from flask import Flask, request, jsonify
from dotenv import load_dotenv

# --- Importa as funções dos utils ---
try:
    from utils.zapi_utils import send_zapi_message
except ImportError:
    def send_zapi_message(*args, **kwargs): return False

try:
    from utils.openrouter_utils import gerar_resposta_openrouter
except ImportError:
    def gerar_resposta_openrouter(mensagem, history=None): return "Desculpe, estou indisponível no momento."

try:
    from utils.db_utils import init_db, add_message_to_history, get_conversation_history
except ImportError:
    def init_db(): pass
    def add_message_to_history(*args, **kwargs): pass
    def get_conversation_history(*args, **kwargs): return []

# Carrega variáveis do .env
load_dotenv()

app = Flask(__name__)

APP_PORT = int(os.getenv("PORT", 5001))
ZAPI_INSTANCE_ID = os.getenv("ZAPI_INSTANCE_ID")
ZAPI_TOKEN = os.getenv("ZAPI_TOKEN")
ZAPI_BASE_URL = os.getenv("ZAPI_BASE_URL", "https://api.z-api.io")

print("\nℹ️  Inicializando banco de dados...")
init_db()
print("✅  Banco de dados pronto.")

@app.route("/", methods=["GET"])
def health_check():
    return jsonify({"status": "ok", "message": "Servidor Dra. Ana rodando!"}), 200

@app.route("/webhook", methods=["POST"])
def webhook():
    print("\n==================================")
    print("🔔  Webhook Recebido! (POST)")
    payload = request.get_json(silent=True)

    if not payload:
        raw_data = request.get_data(as_text=True)
        print("⚠️  Payload bruto (sem JSON):", raw_data)
        return jsonify({"status": "ignored"}), 200

    print("📦  Dados recebidos (brutos):", json.dumps(payload, ensure_ascii=False))

    # --- Extração Inteligente ---
    sender_phone = (
        payload.get("phone") or
        payload.get("telefone") or
        payload.get("author") or
        payload.get("sender", {}).get("id") or
        payload.get("from")
    )

    user_message = None
    if isinstance(payload.get("message"), dict):
        user_message = payload.get("message", {}).get("body")
    elif isinstance(payload.get("message"), str):
        user_message = payload.get("message")
    elif isinstance(payload.get("texto"), dict):
        user_message = payload.get("texto", {}).get("mensagem")
    elif isinstance(payload.get("body"), str):
        user_message = payload.get("body")

    from_me = payload.get("fromMe", False)

    print(f"   -> Verificando: user_message='{user_message}', sender_phone='{sender_phone}', from_me={from_me}")
    print(f"   -> Avaliação: not user_message={not user_message}, not sender_phone={not sender_phone}, from_me={from_me}")

    if not user_message or not sender_phone or from_me:
        print("⚠️  Payload ignorado: sem mensagem, sem telefone ou enviado por mim.")
        return jsonify({"status": "ignored"}), 200

    conversation_history = get_conversation_history(sender_phone)
    add_message_to_history(sender_phone, 'user', user_message)

    print(f"   -> Solicitando resposta da IA para '{user_message[:50]}'...")
    ai_response = gerar_resposta_openrouter(user_message, conversation_history)

    if not ai_response:
        print("⚠️  Nenhuma resposta da IA gerada.")
        return jsonify({"status": "error", "reason": "no AI response"}), 200

    add_message_to_history(sender_phone, 'assistant', ai_response)

    if not ZAPI_INSTANCE_ID or not ZAPI_TOKEN:
        print("❌  Z-API não configurada corretamente (ID/TOKEN).")
    else:
        send_zapi_message(
            phone=sender_phone,
            message=ai_response,
            instance_id=ZAPI_INSTANCE_ID,
            token=ZAPI_TOKEN,
            base_url=ZAPI_BASE_URL
        )

    return jsonify({"status": "ok"}), 200

if __name__ == '__main__':
    print(f"\n🚀 Iniciando servidor Flask local em http://0.0.0.0:{APP_PORT}")
    app.run(host='0.0.0.0', port=APP_PORT, debug=True)
