# utils/db_utils.py

import os
import psycopg2 # A biblioteca para interagir com PostgreSQL
import psycopg2.extras # Para usar cursores que retornam dicionários
from dotenv import load_dotenv # Para carregar a DATABASE_URL do .env localmente

load_dotenv() # Carrega as variáveis do .env (importante para DATABASE_URL local)

DATABASE_URL = os.getenv("DATABASE_URL")

# --- Função para Conectar ao Banco ---
def get_db_connection():
    """Estabelece e retorna uma conexão com o banco de dados PostgreSQL."""
    if not DATABASE_URL:
        print("❌ [DB Util] Erro Crítico: DATABASE_URL não definida no ambiente!")
        return None
    try:
        # Tenta conectar usando a URL. sslmode=require é comum no Render.
        # Se a sua URL já incluir sslmode, ele será usado. Senão, adicionamos.
        conn = psycopg2.connect(DATABASE_URL, sslmode='require')
        print("✅ [DB Util] Conexão com PostgreSQL estabelecida com sucesso.")
        return conn
    except psycopg2.OperationalError as e:
        print(f"❌ [DB Util] Erro ao conectar ao PostgreSQL: {e}")
        print("   Verifique se a DATABASE_URL está correta e se o banco está acessível.")
        return None
    except Exception as e:
        print(f"❌ [DB Util] Erro inesperado ao conectar ao PostgreSQL: {e}")
        return None

# --- Função para Inicializar o Banco (Criar Tabela) ---
def init_db():
    """Cria a tabela 'conversation_history' se ela não existir."""
    conn = get_db_connection()
    if conn is None:
        print("❌ [DB Util] Não foi possível inicializar o banco: Falha na conexão.")
        return

    # Usamos try...finally para garantir que a conexão seja fechada
    try:
        # Cria um cursor para executar comandos SQL
        # Usamos 'with' para garantir que o cursor seja fechado automaticamente
        with conn.cursor() as cursor:
            # SQL para criar a tabela (só cria se não existir)
            create_table_query = """
            CREATE TABLE IF NOT EXISTS conversation_history (
                id SERIAL PRIMARY KEY,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp TIMESTAMPTZ DEFAULT NOW()
            );
            """
            cursor.execute(create_table_query)

            # SQL para criar um índice para otimizar a busca por histórico (opcional, mas recomendado)
            create_index_query = """
            CREATE INDEX IF NOT EXISTS idx_session_timestamp
            ON conversation_history (session_id, timestamp DESC);
            """
            cursor.execute(create_index_query)

            # Confirma as alterações no banco de dados
            conn.commit()
            print("✅ [DB Util] Tabela 'conversation_history' verificada/criada com sucesso.")

    except (Exception, psycopg2.DatabaseError) as error:
        print(f"❌ [DB Util] Erro durante a inicialização do banco: {error}")
        # Desfaz alterações em caso de erro
        conn.rollback()
    finally:
        # Fecha a conexão, independentemente de sucesso ou erro
        if conn:
            conn.close()
            print("ℹ️ [DB Util] Conexão com PostgreSQL fechada (após init_db).")

# --- Função para Adicionar Mensagem ao Histórico ---
def add_message_to_history(session_id, role, content):
    """Insere uma nova mensagem no histórico da conversa."""
    conn = get_db_connection()
    if conn is None:
        print("❌ [DB Util] Não foi possível adicionar mensagem: Falha na conexão.")
        return

    sql = """INSERT INTO conversation_history (session_id, role, content)
             VALUES (%s, %s, %s);"""
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql, (str(session_id), str(role), str(content)))
            conn.commit()
            print(f"✅ [DB Util] Mensagem salva no histórico: session_id={session_id}, role={role}")
    except (Exception, psycopg2.DatabaseError) as error:
        print(f"❌ [DB Util] Erro ao salvar mensagem no histórico: {error}")
        conn.rollback()
    finally:
        if conn:
            conn.close()

# --- Função para Recuperar Histórico da Conversa ---
def get_conversation_history(session_id, limit=10):
    """Recupera as últimas 'limit' mensagens de uma sessão específica."""
    conn = get_db_connection()
    if conn is None:
        print("❌ [DB Util] Não foi possível buscar histórico: Falha na conexão.")
        return [] # Retorna lista vazia em caso de falha

    # Ordena por timestamp DESC para pegar as mais recentes, depois inverte no Python
    sql = """SELECT role, content FROM conversation_history
             WHERE session_id = %s
             ORDER BY timestamp DESC
             LIMIT %s;"""
    history = []
    try:
        # Usamos DictCursor para acessar colunas pelo nome (ex: row['role'])
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
            cursor.execute(sql, (str(session_id), limit))
            results = cursor.fetchall()
            # Invertemos a ordem para ter do mais antigo para o mais novo
            # e convertemos para dicionários simples
            history = [{'role': row['role'], 'content': row['content']} for row in reversed(results)]
            print(f"✅ [DB Util] Histórico recuperado para session_id={session_id} (limit={limit}): {len(history)} mensagens.")
            print(f"   Histórico: {history}") # Log para debug
    except (Exception, psycopg2.DatabaseError) as error:
        print(f"❌ [DB Util] Erro ao buscar histórico: {error}")
    finally:
        if conn:
            conn.close()
    return history

# --- Teste Simples (opcional, pode rodar com 'python -m utils.db_utils') ---
if __name__ == '__main__':
    print("--- Testando Funções do DB Util ---")
    # 1. Tenta inicializar (criar tabela)
    init_db()
    # 2. Adiciona mensagens de teste
    print("\n--- Adicionando mensagens de teste ---")
    test_session = "teste_123"
    add_message_to_history(test_session, "user", "Olá, como vai?")
    add_message_to_history(test_session, "assistant", "Vou bem, e você?")
    add_message_to_history(test_session, "user", "Estou bem também.")
    # 3. Recupera histórico
    print("\n--- Recuperando histórico ---")
    retrieved_history = get_conversation_history(test_session, 5)
    print(f"\nHistórico recuperado para {test_session}:")
    for msg in retrieved_history:
        print(f"  {msg['role']}: {msg['content']}")