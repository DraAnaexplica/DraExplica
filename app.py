# app.py
import os
import json
from flask import Flask, request, jsonify
from dotenv import load_dotenv

# --- Importa os utilitários ---
from utils.zapi_utils import send_zapi_message
from utils.openrouter_utils import gerar_resposta_openrouter
from utils.db_utils import init_db, add_message_to_history, get_conversation_history

# Carrega variáveis de ambiente
load_dotenv()

# Flask App
app = Flask(__name__)

# Configurações
APP_PORT = int(os.getenv("PORT", 5001))
ZAPI_INSTANCE_ID = os.getenv("ZAPI_INSTANCE_ID")
ZAPI_TOKEN = os.getenv("ZAPI_TOKEN")
ZAPI_BASE_URL = os.getenv("ZAPI_BASE_URL", "https://api.z-api.io")

# Inicializa DB
print("ℹ️  Inicializando banco de dados...")
init_db()
print("✅ Banco de dados pronto.")

# Webhook principal
@app.route("/webhook", methods=["POST"])
def webhook():
    print("==================================")
    print("🔔 Webhook Recebido! (POST)")
    payload = request.get_json()

    if not payload:
        print("❌ Nenhum JSON recebido.")
        return jsonify({"erro": "sem conteúdo"}), 400

    print("📦 Dados recebidos (brutos):", json.dumps(payload, indent=2))

    # --- NOVA ESTRUTURA DA Z-API ---
    sender_phone = payload.get("phone")
    from_me = payload.get("fromMe", False)
    user_message = None

    if "texto" in payload and isinstance(payload["texto"], dict):
        user_message = payload["texto"].get("mensagem")

    print(f"   -> Verificando: user_message='{user_message}', sender_phone='{sender_phone}', from_me={from_me}")
    print(f"   -> Avaliação: not user_message={not user_message}, not sender_phone={not sender_phone}, from_me={from_me}")

    if not user_message or not sender_phone or from_me:
        print("⚠️ Payload ignorado: sem mensagem, sem telefone ou enviado por mim.")
        return jsonify({"status": "ignored"}), 200

    # Recupera histórico
    conversation_history = get_conversation_history(sender_phone)
    add_message_to_history(sender_phone, "user", user_message)

    # Gera resposta
    ai_response = gerar_resposta_openrouter(user_message, conversation_history)
    if ai_response:
        add_message_to_history(sender_phone, "assistant", ai_response)
        success = send_zapi_message(
            phone=sender_phone,
            message=ai_response,
            instance_id=ZAPI_INSTANCE_ID,
            token=ZAPI_TOKEN,
            base_url=ZAPI_BASE_URL
        )
        print("✅ Resposta enviada com sucesso" if success else "❌ Falha ao enviar resposta")
    else:
        print("⚠️ Falha ao gerar resposta da IA.")

    return jsonify({"status": "ok"}), 200

# Health check
@app.route("/", methods=["GET"])
def check():
    return jsonify({"status": "ok", "message": "Servidor Dra. Ana rodando!"})

if __name__ == "__main__":
    print(f"🚀 Servidor rodando em http://0.0.0.0:{APP_PORT}")
    app.run(host="0.0.0.0", port=APP_PORT, debug=True)
