import os
import json
from flask import Flask, request, jsonify
from dotenv import load_dotenv

# === IMPORTS COM TRATAMENTO DE FALHA ===
try:
    from utils.zapi_utils import send_zapi_message
except:
    def send_zapi_message(*args, **kwargs): return False

try:
    from utils.openrouter_utils import gerar_resposta_openrouter
except:
    def gerar_resposta_openrouter(mensagem, history=None): return "..."

try:
    from utils.db_utils import init_db, add_message_to_history, get_conversation_history
except:
    def init_db(): pass
    def add_message_to_history(*args, **kwargs): pass
    def get_conversation_history(*args, **kwargs): return []

# === CONFIGURAÇÕES ===
load_dotenv()
app = Flask(__name__)
APP_PORT = int(os.getenv("PORT", 5001))
ZAPI_INSTANCE_ID = os.getenv("ZAPI_INSTANCE_ID")
ZAPI_TOKEN = os.getenv("ZAPI_TOKEN")
ZAPI_BASE_URL = os.getenv("ZAPI_BASE_URL", "https://api.z-api.io")

print("ℹ️  Inicializando banco de dados...")
init_db()
print("✅ Banco de dados pronto.")

# === ROTA PRINCIPAL DE WEBHOOK ===
@app.route('/webhook', methods=['POST'])
def webhook_handler():
    print("===================================")
    print("🔔 Webhook Recebido! (POST)")

    try:
        raw_data = request.get_data(as_text=True)
        print("📦 Dados recebidos (brutos):", raw_data)
        payload = json.loads(raw_data)
    except Exception as e:
        print("❌ Erro ao parsear JSON:", e)
        return jsonify({"status": "error", "message": "invalid JSON"}), 400

    # === TRATAMENTO ROBUSTO DE MENSAGEM ===
    user_message = None

    if isinstance(payload.get("texto"), dict):
        user_message = payload.get("texto", {}).get("mensagem")

    if not user_message and isinstance(payload.get("message"), dict):
        user_message = payload.get("message", {}).get("body")

    if not user_message and isinstance(payload.get("message"), str):
        user_message = payload.get("message")

    if not user_message:
        print("⚠️ Nenhuma mensagem reconhecida no payload.")

    # === EXTRAÇÃO DE TELEFONE ===
    sender_phone = (
        payload.get("telefone") or
        payload.get("phone") or
        payload.get("author") or
        payload.get("from") or
        payload.get("sender", {}).get("id")
    )

    from_me = payload.get("fromMe", False)

    print(f"   -> Verificando: user_message='{user_message}', sender_phone='{sender_phone}', from_me={from_me}")
    print(f"   -> Avaliação: not user_message={not user_message}, not sender_phone={not sender_phone}, from_me={from_me}")

    if not user_message or not sender_phone or from_me:
        print("⚠️ Payload ignorado: sem mensagem, sem telefone ou enviado por mim.")
        return jsonify({"status": "ignored"}), 200

    sender_phone = str(sender_phone).split('@')[0]

    # === HISTÓRICO + GERAÇÃO DE RESPOSTA ===
    history = get_conversation_history(sender_phone)
    add_message_to_history(sender_phone, "user", user_message)

    ai_response = gerar_resposta_openrouter(user_message, history)
    if not ai_response:
        print("⚠️ IA não respondeu.")
        return jsonify({"status": "no response"}), 200

    print(f"🤖 Resposta da IA: {ai_response[:80]}")
    add_message_to_history(sender_phone, "assistant", ai_response)

    success = send_zapi_message(
        phone=sender_phone,
        message=ai_response,
        instance_id=ZAPI_INSTANCE_ID,
        token=ZAPI_TOKEN,
        base_url=ZAPI_BASE_URL
    )

    print("✅ Mensagem enviada com sucesso." if success else "❌ Falha no envio.")
    return jsonify({"status": "ok"}), 200

# === ROTA DE SAÚDE ===
@app.route('/', methods=['GET'])
def health_check():
    return jsonify({"status": "ok", "message": "Servidor Dra. Ana rodando!"}), 200

# === EXECUÇÃO LOCAL ===
if __name__ == '__main__':
    app.run(host="0.0.0.0", port=APP_PORT, debug=True)
