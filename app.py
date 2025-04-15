# app.py (Versão Fase 4 - Corrigido para nova estrutura da Z-API)
import os
import json
from flask import Flask, request, jsonify
from dotenv import load_dotenv

# --- Importa as funções dos utils ---
try:
    from utils.zapi_utils import send_zapi_message
except ImportError:
    print("!!! ERRO DE IMPORT ZAPI !!!")
    def send_zapi_message(*args, **kwargs): print("--- AVISO: send_zapi_message NÃO ESTÁ FUNCIONANDO (Import falhou) ---"); return False

try:
    from utils.openrouter_utils import gerar_resposta_openrouter
except ImportError:
    print("!!! ERRO DE IMPORT OPENROUTER !!!")
    def gerar_resposta_openrouter(mensagem, history=None): print("--- AVISO: gerar_resposta_openrouter NÃO ESTÁ FUNCIONANDO (Import falhou) ---"); return "Desculpe, não consigo gerar uma resposta agora."

try:
    from utils.db_utils import init_db, add_message_to_history, get_conversation_history
except ImportError:
    print("!!! ERRO DE IMPORT DB UTILS !!!")
    def init_db(): print("--- AVISO: init_db NÃO ESTÁ FUNCIONANDO (Import falhou) ---")
    def add_message_to_history(*args, **kwargs): print("--- AVISO: add_message_to_history NÃO ESTÁ FUNCIONANDO (Import falhou) ---")
    def get_conversation_history(*args, **kwargs): print("--- AVISO: get_conversation_history NÃO ESTÁ FUNCIONANDO (Import falhou) ---"); return []

load_dotenv()
app = Flask(__name__)

APP_PORT = int(os.getenv("PORT", 5001))
ZAPI_INSTANCE_ID = os.getenv("ZAPI_INSTANCE_ID")
ZAPI_TOKEN = os.getenv("ZAPI_TOKEN")
ZAPI_BASE_URL = os.getenv("ZAPI_BASE_URL", "https://api.z-api.io")

print("ℹ️ [App Startup] Inicializando banco de dados (se necessário)...")
init_db()
print("✅ [App Startup] Banco de dados pronto.")

@app.route('/webhook', methods=['POST'])
def webhook_handler():
    print("===================================")
    print(f"🔔 Webhook Recebido! ({request.method})")

    payload = request.get_json()

    if payload:
        print("--- Payload JSON Recebido ---")
        print(json.dumps(payload, indent=2))
        print("-----------------------------")

        try:
            # Compatível com nova estrutura da Z-API
            is_message = (
                payload.get('type') == 'message' or
                payload.get('tipo') == 'message' or
                'mensagem' in payload.get('texto', {})
            )

            user_message = None
            if 'mensagem' in payload.get('texto', {}):
                user_message = payload['texto']['mensagem']

            is_chat = user_message is not None
            from_me = payload.get('fromMe', False)

            print(f"   -> Verificando: É mensagem? {is_message}, É chat? {is_chat}, Enviado por mim? {from_me}")

            if is_message and is_chat and not from_me:
                print("   -> Payload parece ser uma mensagem de usuário recebida.")

                sender_phone = payload.get('telefone') or payload.get('from') or payload.get('author')
                if isinstance(sender_phone, str):
                    sender_phone = sender_phone.split('@')[0]

                print(f"   -> Extração: Remetente/SessionID={sender_phone}, Mensagem='{user_message}'")

                if sender_phone and user_message:
                    print(f"   -> Buscando histórico ANTES da msg atual para {sender_phone} no DB...")
                    conversation_history = get_conversation_history(sender_phone)

                    print(f"   -> Salvando mensagem ATUAL do usuário ({user_message[:20]}...) para {sender_phone} no DB...")
                    add_message_to_history(sender_phone, 'user', user_message)

                    print(f"   -> Solicitando resposta da IA para: '{user_message[:50]}...' (com histórico: {len(conversation_history)} msgs)")
                    ai_response = gerar_resposta_openrouter(user_message, conversation_history)

                    if ai_response:
                        print(f"   -> Resposta da IA recebida: '{ai_response[:80]}...'")
                        print(f"   -> Salvando resposta da IA para {sender_phone} no DB...")
                        add_message_to_history(sender_phone, 'assistant', ai_response)

                        print(f"   -> Enviando resposta da IA para {sender_phone} via Z-API...")
                        if not ZAPI_INSTANCE_ID or not ZAPI_TOKEN:
                            print("   -> Falha ao enviar: Credenciais Z-API (ID ou Token) não configuradas.")
                        else:
                            success = send_zapi_message(
                                phone=sender_phone,
                                message=ai_response,
                                instance_id=ZAPI_INSTANCE_ID,
                                token=ZAPI_TOKEN,
                                base_url=ZAPI_BASE_URL
                            )
                            if success:
                                print("   -> Resposta da IA enviada com sucesso.")
                            else:
                                print("   -> Falha ao enviar resposta da IA.")
                    else:
                        print("   -> Não foi possível gerar uma resposta da IA.")
                else:
                    print("   -> Não foi possível extrair remetente ou mensagem válidos do payload.")
            else:
                print("   -> Payload não parece ser uma mensagem de usuário recebida ou foi enviada pelo bot.")

        except Exception as e:
            print(f"❌ [Webhook] Erro GERAL ao tentar processar o payload JSON: {e}")
            import traceback
            traceback.print_exc()
    else:
        raw_data = request.get_data(as_text=True)
        print("--- Dados Brutos Recebidos (Não JSON?) ---")
        print(raw_data)
        print("-----------------------------")

    return jsonify({"status": "received"}), 200

@app.route('/', methods=['GET'])
def health_check():
    print("🩺 Health check solicitado!")
    return jsonify({"status": "ok", "message": "Servidor Dra. Ana rodando!"}), 200

if __name__ == '__main__':
    print(f"🚀 Iniciando servidor Flask local em http://0.0.0.0:{APP_PORT}")
    app.run(host='0.0.0.0', port=APP_PORT, debug=True)
