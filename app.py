# app.py (Versão Final Corrigida – Blindado contra fromMe malformado)
import os
import json
from flask import Flask, request, jsonify
from dotenv import load_dotenv

# --- Importações seguras ---
try:
    from utils.zapi_utils import send_zapi_message
except ImportError:
    print("!!! ERRO DE IMPORT ZAPI !!!")
    def send_zapi_message(*args, **kwargs): print("--- AVISO: send_zapi_message NÃO FUNCIONA ---"); return False

try:
    from utils.openrouter_utils import gerar_resposta_openrouter
except ImportError:
    print("!!! ERRO DE IMPORT OPENROUTER !!!")
    def gerar_resposta_openrouter(msg, history=None): print("--- AVISO: gerar_resposta_openrouter NÃO FUNCIONA ---"); return "Desculpe, não consigo gerar uma resposta agora."

try:
    from utils.db_utils import init_db, add_message_to_history, get_conversation_history
except ImportError:
    print("!!! ERRO DE IMPORT DB UTILS !!!")
    def init_db(): print("--- AVISO: init_db NÃO FUNCIONA ---")
    def add_message_to_history(*args, **kwargs): print("--- AVISO: add_message_to_history NÃO FUNCIONA ---")
    def get_conversation_history(*args, **kwargs): print("--- AVISO: get_conversation_history NÃO FUNCIONA ---"); return []

# --- Setup Inicial ---
load_dotenv()
app = Flask(__name__)

APP_PORT = int(os.getenv("PORT", 5001))
ZAPI_INSTANCE_ID = os.getenv("ZAPI_INSTANCE_ID")
ZAPI_TOKEN = os.getenv("ZAPI_TOKEN")
ZAPI_BASE_URL = os.getenv("ZAPI_BASE_URL", "https://api.z-api.io")

print("ℹ️ [App Startup] Inicializando banco de dados...")
init_db()
print("✅ [App Startup] Banco de dados pronto.")

# --- Rota de Webhook ---
@app.route('/webhook', methods=['POST'])
def webhook_handler():
    print("===================================")
    print(f"🔔 Webhook Recebido! ({request.method})")
    payload = request.get_json()

    if payload:
        print("--- Payload JSON Recebido ---")
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        print("-----------------------------")

        try:
            user_message = payload.get("texto", {}).get("mensagem")
            sender_phone = payload.get("telefone")
            from_me = payload.get("fromMe")

            # ⚠️ Correção segura para fromMe malformado
            if isinstance(from_me, str):
                from_me = from_me.strip().lower() in ["true", "1", "sim", "yes"]
            if not isinstance(from_me, bool):
                from_me = False

            if not user_message or not sender_phone or from_me:
                print("⚠️ Payload ignorado: sem mensagem, sem telefone ou enviado por mim.")
                return jsonify({"status": "ignored"}), 200

            if isinstance(sender_phone, str):
                sender_phone = sender_phone.split("@")[0]

            print(f"   -> Extração: Remetente = {sender_phone}, Mensagem = '{user_message}'")

            # Recuperar histórico
            print(f"   -> Buscando histórico para {sender_phone}...")
            history = get_conversation_history(sender_phone)

            # Salvar mensagem do usuário
            add_message_to_history(sender_phone, "user", user_message)

            # Gerar resposta da IA
            print(f"   -> Gerando resposta via IA...")
            ai_response = gerar_resposta_openrouter(user_message, history)

            if ai_response:
                print(f"   -> Resposta da IA: {ai_response[:80]}...")
                add_message_to_history(sender_phone, "assistant", ai_response)

                print(f"   -> Enviando resposta via Z-API...")
                success = send_zapi_message(
                    phone=sender_phone,
                    message=ai_response,
                    instance_id=ZAPI_INSTANCE_ID,
                    token=ZAPI_TOKEN,
                    base_url=ZAPI_BASE_URL
                )
                print("✅ Mensagem enviada com sucesso." if success else "❌ Falha no envio via Z-API.")
            else:
                print("⚠️ IA não gerou resposta.")

        except Exception as e:
            print(f"❌ ERRO GERAL no processamento: {e}")
            import traceback
            traceback.print_exc()
    else:
        raw_data = request.get_data(as_text=True)
        print("--- Payload bruto recebido ---")
        print(raw_data)
        print("-----------------------------")

    return jsonify({"status": "received"}), 200

# --- Health Check ---
@app.route('/', methods=['GET'])
def health_check():
    print("🩺 Health check solicitado!")
    return jsonify({"status": "ok", "message": "Servidor Dra. Ana rodando!"}), 200

# --- Execução local ---
if __name__ == '__main__':
    print(f"🚀 Servidor local em http://0.0.0.0:{APP_PORT}")
    app.run(host='0.0.0.0', port=APP_PORT, debug=True)
