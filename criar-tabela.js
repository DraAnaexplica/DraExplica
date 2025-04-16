import { pool } from './db.js';

async function criarTabela() {
  console.log('🔄 Executando query de criação...');

  try {
    const query = `
      CREATE TABLE IF NOT EXISTS chat_history (
        id SERIAL PRIMARY KEY,
        phone VARCHAR(20),
        message TEXT,
        sender VARCHAR(10),
        timestamp TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
      );
    `;

    await pool.query(query);
    console.log('✅ Tabela criada ou já existia.');
  } catch (err) {
    console.error('❌ ERRO ao criar tabela:', err);
  } finally {
    await pool.end();
    console.log('🔵 Pool de conexões encerrado.');
  }
}

criarTabela();
