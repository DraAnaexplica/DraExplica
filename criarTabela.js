// criarTabela.js

import pg from 'pg';
import dotenv from 'dotenv';

dotenv.config();

const { Client } = pg;

const client = new Client({
  connectionString: process.env.DATABASE_URL,
  ssl: {
    rejectUnauthorized: false,
  },
});

async function criarTabelaTokens() {
  try {
    await client.connect();
    console.log('✅ Conectado ao PostgreSQL');

    const query = `
      CREATE TABLE IF NOT EXISTS chat_history (
        id SERIAL PRIMARY KEY,
        phone VARCHAR(20) NOT NULL,
        role VARCHAR(10) NOT NULL,
        content TEXT NOT NULL,
        timestamp TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
      );
    `;

    await client.query(query);
    console.log('✅ Tabela "chat_history" criada ou já existente');
  } catch (err) {
    console.error('❌ Erro ao criar tabela:', err); // <-- Aqui mostra erro completo
  } finally {
    await client.end();
    console.log('🔌 Conexão encerrada');
  }
}

criarTabelaTokens();
