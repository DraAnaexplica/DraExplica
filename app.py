import os
import json
from flask import Flask, request, jsonify
from dotenv import load_dotenv

# --- Importações com fallback ---
try:
    from utils.zapi_utils import send_zapi_message
except ImportError:
    def send_zapi_message(*args, **kwargs):
        print("[WARN] Função send_zapi_message não disponível.")
        return False

try:
    from utils.openrouter_utils import gerar_resposta_openrouter
except ImportError:
    def gerar_resposta_openrouter(mensagem, history=None):
        print("[WARN] Função gerar_resposta_openrouter não disponível.")
        return "Desculpe, não consigo responder agora."

try:
    from utils.db_utils import init_db, add_message_to_history, get_conversation_history
except ImportError:
    def init_db():
        print("[WARN] init_db não disponível.")
    def add_message_to_history(*args, **kwargs):
        print("[WARN] add_message_to_history não disponível.")
    def get_conversation_history(*args, **kwargs):
        print("[WARN] get_conversation_history não disponível.")
        return []

# --- Inicialização ---
load_dotenv()
app = Flask(__name__)

APP_PORT = int(os.getenv("PORT", 5001))
ZAPI_INSTANCE_ID = os.getenv("ZAPI_INSTANCE_ID")
ZAPI_TOKEN = os.getenv("ZAPI_TOKEN")
ZAPI_BASE_URL = os.getenv("ZAPI_BASE_URL", "https://api.z-api.io")

print("ℹ️  Inicializando banco de dados...")
init_db()
print("✅ Banco de dados pronto.")


# --- Webhook ---
@app.route('/webhook', methods=['POST'])
def webhook():
    print("==================================")
    print("🔔 Webhook Recebido! (POST)")

    raw_data = request.get_data(as_text=True)
    print(f"📦 Dados recebidos (brutos): {raw_data}")

    try:
        payload = json.loads(raw_data)
    except Exception as e:
        print(f"❌ Erro ao decodificar JSON: {e}")
        return jsonify({"status": "erro", "detalhe": "json inválido"}), 400

    # --- Extração robusta da mensagem ---
    user_message = None
    texto = payload.get("texto")

    if isinstance(texto, dict):
        user_message = texto.get("mensagem")
    elif isinstance(texto, str):
        try:
            texto_dict = json.loads(texto)
            user_message = texto_dict.get("mensagem")
        except:
            print("⚠️ Campo 'texto' mal formatado.")

    # Alternativas adicionais (fallback)
    if not user_message and isinstance(payload.get("message"), dict):
        user_message = payload.get("message", {}).get("body")

    if not user_message and isinstance(payload.get("message"), str):
        user_message = payload.get("message")

    if not user_message:
        print("⚠️ Nenhuma mensagem reconhecida no payload.")

    # --- Identificação do remetente ---
    sender_phone = (
        payload.get("telefone") or
        payload.get("phone") or
        payload.get("author") or
        payload.get("from") or
        payload.get("sender", {}).get("id")
    )

    if isinstance(sender_phone, str):
        sender_phone = sender_phone.split("@")[0]

    from_me = payload.get("fromMe", False)

    print(f"   -> Verificando: user_message='{user_message}', sender_phone='{sender_phone}', from_me={from_me}")
    print(f"   -> Avaliação: not user_message={not user_message}, not sender_phone={not sender_phone}, from_me={from_me}")

    if not user_message or not sender_phone or from_me:
        print("⚠️ Payload ignorado: sem mensagem, sem telefone ou enviado por mim.")
        return jsonify({"status": "ignored"}), 200

    # --- Histórico + IA ---
    try:
        history = get_conversation_history(sender_phone)
        add_message_to_history(sender_phone, "user", user_message)

        print(f"🤖 Enviando para IA: '{user_message[:50]}' com histórico de {len(history)} mensagens.")
        resposta = gerar_resposta_openrouter(user_message, history)

        if resposta:
            add_message_to_history(sender_phone, "assistant", resposta)
            send_zapi_message(
                phone=sender_phone,
                message=resposta,
                instance_id=ZAPI_INSTANCE_ID,
                token=ZAPI_TOKEN,
                base_url=ZAPI_BASE_URL
            )
            print("✅ Resposta enviada com sucesso.")
        else:
            print("⚠️ IA não respondeu.")
    except Exception as e:
        print(f"❌ Erro geral no processamento do webhook: {e}")

    return jsonify({"status": "ok"}), 200


# --- Health Check ---
@app.route('/', methods=['GET'])
def health():
    print("🩺 Health check solicitado.")
    return jsonify({"status": "ok", "message": "Servidor Dra. Ana rodando!"}), 200


if __name__ == '__main__':
    print(f"🚀 Iniciando servidor Flask em http://0.0.0.0:{APP_PORT}")
    app.run(host='0.0.0.0', port=APP_PORT, debug=True)
