# utils/zapi_utils.py (Versão Completa Corrigida)

import os       # <--- IMPORTANTE: Adicionado/Garantido aqui
import requests # <--- IMPORTANTE: Adicionado/Garantido aqui

def send_zapi_message(phone, message, instance_id, token, base_url):
    """
    Envia uma mensagem de texto usando a API da Z-API.
    Inclui Client-Token e print de debug.
    """
    client_token = os.getenv("ZAPI_CLIENT_TOKEN")
    # Linha de Debug (mantida):
    print(f"DEBUG [ZAPI Util]: Client Token lido do ambiente = '{client_token}'")

    if not all([phone, message, instance_id, token, base_url, client_token]):
        print("❌ [ZAPI Util] Erro: Faltando informações para enviar mensagem (Telefone, Mensagem, ID Instancia, Token, URL Base ou Client-Token).")
        if not client_token: print("   -> Causa Provável: ZAPI_CLIENT_TOKEN não definido no .env ou ambiente.")
        return False

    api_url = f"{base_url}/instances/{instance_id}/token/{token}/send-text"

    payload = {
        "phone": str(phone),
        "message": str(message)
    }

    headers = {
        "Content-Type": "application/json",
        "Client-Token": client_token
    }

    print(f"ℹ️ [ZAPI Util] Preparando para enviar para {phone} via {api_url}")
    print(f"   Payload: {payload}")

    try:
        response = requests.post(
            api_url,
            json=payload,
            headers=headers,
            timeout=30
        )
        response.raise_for_status()

        print(f"✅ [ZAPI Util] Mensagem enviada (ou aceita para envio) para {phone}.")
        print(f"   Resposta da Z-API: {response.text}")
        return True

    except requests.exceptions.Timeout:
        print(f"❌ [ZAPI Util] Erro: Timeout ao tentar enviar mensagem para {phone}.")
        return False
    except requests.exceptions.HTTPError as http_err:
        print(f"❌ [ZAPI Util] Erro HTTP da Z-API ao enviar para {phone}: {http_err}")
        try:
            error_details = http_err.response.json()
            print(f"   Resposta da Z-API (JSON): {error_details}")
        except ValueError:
            print(f"   Resposta da Z-API (Texto): {http_err.response.text}")
        return False
    except requests.exceptions.RequestException as req_err:
        print(f"❌ [ZAPI Util] Erro de Requisição (rede?) ao enviar para {phone}: {req_err}")
        return False
    except Exception as e:
        print(f"❌ [ZAPI Util] Erro inesperado na função send_zapi_message: {e}")
        import traceback
        traceback.print_exc()
        return False