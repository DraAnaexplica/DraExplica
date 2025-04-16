import dotenv from 'dotenv';
dotenv.config(); // <- carrega o .env primeiro!

import pkg from 'pg';
const { Pool } = pkg;

// Lê a URL e corrige se vier com 'postgresql://'
let connectionString = process.env.DATABASE_URL;
console.log('\n🔍 ANTES DA CORREÇÃO');
console.log(connectionString);

if (connectionString?.startsWith('postgresql://')) {
  connectionString = connectionString.replace('postgresql://', 'postgres://');
}

console.log('✅ DEPOIS DA CORREÇÃO');
console.log(connectionString);

// Conecta com SSL ativo
export const pool = new Pool({
  connectionString,
  ssl: {
    rejectUnauthorized: false
  }
});
