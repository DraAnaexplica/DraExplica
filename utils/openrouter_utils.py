# utils/openrouter_utils.py (Versão com Histórico)
import os
import requests

# --- Função para Carregar o Prompt do Sistema (sem alterações) ---
def carregar_prompt():
    caminho_prompt = os.path.join("prompt", "system_prompt.txt")
    prompt_padrao = "Você é um assistente médico virtual chamado Dra. Ana. Responda dúvidas de forma clara, informativa e empática, mas sempre lembre ao paciente que suas respostas não substituem uma consulta médica real e que ele deve procurar um profissional de saúde para diagnósticos e tratamentos."
    if not os.path.exists(caminho_prompt):
        print(f"⚠️ [OpenRouter Util] Arquivo de prompt não encontrado em: {caminho_prompt}. Usando prompt padrão.")
        return prompt_padrao
    try:
        with open(caminho_prompt, "r", encoding="utf-8") as arquivo:
            prompt_lido = arquivo.read()
            print("✅ [OpenRouter Util] Prompt do sistema carregado com sucesso.")
            return prompt_lido
    except Exception as e:
        print(f"❌ [OpenRouter Util] Erro ao ler o arquivo de prompt '{caminho_prompt}': {e}. Usando prompt padrão.")
        return prompt_padrao

# --- Função Principal para Gerar Resposta (MODIFICADA) ---
def gerar_resposta_openrouter(mensagem_usuario, history=None): # <--- Aceita 'history' como argumento opcional
    """
    Envia a mensagem do usuário, o histórico da conversa e o prompt do sistema
    para a API OpenRouter e retorna a resposta gerada pela IA.
    """
    print("ℹ️ [OpenRouter Util] Iniciando geração de resposta...")
    api_key = os.getenv("OPENROUTER_API_KEY")
    prompt_sistema = carregar_prompt()

    if not api_key:
        print("❌ [OpenRouter Util] Erro Crítico: OPENROUTER_API_KEY não definida!")
        return None

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": os.getenv("SITE_REFERER", "http://localhost"),
        "X-Title": os.getenv("APP_TITLE", "DraAnaWhatsApp")
    }
    model_name = os.getenv("OPENROUTER_MODEL", "google/gemini-flash-1.5")

    # --- CONSTRUÇÃO DA LISTA DE MENSAGENS (MODIFICADO) ---
    # Começa sempre com o prompt do sistema
    messages = [{"role": "system", "content": prompt_sistema}]

    # Adiciona o histórico se ele foi fornecido e é uma lista válida
    if history and isinstance(history, list):
        print(f"   -> [OpenRouter Util] Adicionando {len(history)} mensagens do histórico.")
        messages.extend(history) # Adiciona todas as mensagens do histórico recuperado
    else:
        print("   -> [OpenRouter Util] Sem histórico fornecido ou inválido.")

    # Adiciona a mensagem atual do usuário no final
    messages.append({"role": "user", "content": str(mensagem_usuario)})
    # --- FIM DA CONSTRUÇÃO ---

    # Log para ver o início e fim da conversa enviada (sem expor todo o histórico no log)
    print(f"   -> [OpenRouter Util] Enviando {len(messages)} mensagens para IA (Início: '{messages[0]['content'][:30]}...', Fim: '{messages[-1]['content'][:50]}...')")


    body = {
        "model": model_name,
        "messages": messages, # <--- Usa a lista construída com sistema + histórico + usuário
        "max_tokens": 500
    }

    print(f"ℹ️ [OpenRouter Util] Enviando para OpenRouter (Modelo: {model_name}).") # Mensagem removida daqui para evitar duplicidade

    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=body,
            timeout=60
        )
        response.raise_for_status()
        response_data = response.json()

        if response_data.get('choices') and len(response_data['choices']) > 0:
             generated_content = response_data['choices'][0]['message']['content']
             print(f"✅ [OpenRouter Util] Resposta recebida: '{generated_content[:80]}...'")
             return generated_content.strip()
        else:
            print(f"⚠️ [OpenRouter Util] Resposta do OpenRouter sem 'choices' válidos: {response_data}")
            return None
    except requests.exceptions.Timeout:
        print("❌ [OpenRouter Util] Erro: Timeout ao conectar com OpenRouter.")
        return None
    except requests.exceptions.HTTPError as http_err:
        print(f"❌ [OpenRouter Util] Erro HTTP do OpenRouter: {http_err}")
        print(f"   Resposta: {http_err.response.text}")
        return None
    except requests.exceptions.RequestException as req_err:
        print(f"❌ [OpenRouter Util] Erro de Requisição (rede?) ao conectar com OpenRouter: {req_err}")
        return None
    except Exception as e:
        print(f"❌ [OpenRouter Util] Erro inesperado na função gerar_resposta_openrouter: {e}")
        import traceback
        traceback.print_exc()
        return None