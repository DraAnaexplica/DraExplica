import express from 'express';
import bodyParser from 'body-parser';
import dotenv from 'dotenv';
import axios from 'axios';
import { pool } from './db.js'; // <-- Conexão PostgreSQL

dotenv.config();

// 🔍 Teste das variáveis do .env
console.log('\n🧪 VERIFICAÇÃO DE VARIÁVEIS .env');
console.log('OPENROUTER_API_KEY =>', process.env.OPENROUTER_API_KEY);
console.log('DATABASE_URL =>', process.env.DATABASE_URL);
console.log('ZAPI_INSTANCE_ID =>', process.env.ZAPI_INSTANCE_ID);
console.log('PORT =>', process.env.PORT);
console.log('------------------------------------\n');

const app = express();
app.use(bodyParser.json());

const PORT = process.env.PORT || 3000;

// --- PROMPT EMBUTIDO ---
const promptDraAna = `
Você é a Dra. Ana, uma médica brasileira carismática, empática e especializada em saúde da mulher de 30 a 55 anos. 
Atende de forma acolhedora, direta e emocionalmente envolvente, como uma conversa real no WhatsApp.

Comece sempre perguntando o nome e a idade da paciente com carinho.
Responda com explicações claras, sem parecer robô. Não use linguagem técnica.
Seu objetivo é gerar confiança, vínculo emocional e ajudar de verdade.

Use frases curtas, emojis leves (😊💬❤️) e toque humano realista.
Não diga que é uma IA. Você é a Dra. Ana e fala como tal.
Evite exageros e frases genéricas. Escreva como se estivesse digitando.

Não responda nada fora do contexto de saúde feminina, bem-estar e acolhimento emocional.
`;

// --- IA: OpenRouter ---
async function getAIResponse(message) {
  try {
    const response = await axios.post(
      'https://openrouter.ai/api/v1/chat/completions',
      {
        model: process.env.OPENROUTER_MODEL,
        messages: [
          { role: 'system', content: promptDraAna },
          { role: 'user', content: message }
        ]
      },
      {
        headers: {
          'Authorization': `Bearer ${process.env.OPENROUTER_API_KEY}`,
          'Content-Type': 'application/json'
        }
      }
    );

    const content = response.data?.choices?.[0]?.message?.content;
    return content || '[Sem resposta da IA]';
  } catch (error) {
    console.error('[ERRO OPENROUTER]', JSON.stringify(error.response?.data || error.message, null, 2));
    return '[Erro ao consultar a IA]';
  }
}

// --- Enviar mensagem via Z-API ---
async function sendZapiMessage(phone, message) {
  try {
    const response = await axios.post(
      `https://api.z-api.io/instances/${process.env.ZAPI_INSTANCE_ID}/token/${process.env.ZAPI_INSTANCE_TOKEN}/send-text`,
      { phone, message },
      {
        headers: {
          'Content-Type': 'application/json',
          'Client-Token': process.env.ZAPI_CLIENT_TOKEN
        }
      }
    );
    console.log(`✅ Mensagem enviada para ${phone}: ${message}`);
  } catch (error) {
    console.error("❌ ERRO AO ENVIAR Z-API:", JSON.stringify(error.response?.data || error.message, null, 2));
  }
}

// --- Webhook ---
app.post('/on-new-message', async (req, res) => {
  const body = req.body;
  console.log('[WEBHOOK RECEBIDO]', body);

  const userMessage = body?.text?.message;
  const phone = body?.phone;
  const fromMe = body?.fromMe;

  if (!userMessage || !phone || fromMe) {
    console.warn('⚠️ Ignorado: mensagem vazia, enviada por mim ou sem telefone.');
    return res.sendStatus(200);
  }

  console.log(`📩 ${phone}: ${userMessage}`);
  const aiReply = await getAIResponse(userMessage);
  console.log(`🤖 Dra. Ana: ${aiReply}`);

  // --- Salvar resposta da IA no PostgreSQL ---
  try {
    await pool.query(
      'INSERT INTO chat_history (phone, message, sender) VALUES ($1, $2, $3)',
      [phone, aiReply, 'bot']
    );
  } catch (err) {
    console.error('❌ ERRO ao salvar no PostgreSQL:', err.message);
  }

  await sendZapiMessage(phone, aiReply);
  res.sendStatus(200);
});

// --- Criar tabela no PostgreSQL ---
app.get('/criar-tabela', async (req, res) => {
  try {
    const query = `
      CREATE TABLE IF NOT EXISTS chat_history (
        id SERIAL PRIMARY KEY,
        phone VARCHAR(20),
        message TEXT,
        sender VARCHAR(10),
        timestamp TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
      );`;

    await pool.query(query);
    console.log('✅ Tabela chat_history criada ou já existia.');
    res.status(200).send('Tabela criada com sucesso.');
  } catch (err) {
    console.error('❌ ERRO ao criar tabela:', err);
    res.status(500).send('Erro ao criar tabela.');
  }
});

// --- Start ---
app.listen(PORT, () => {
  console.log(`✅ Servidor rodando em http://localhost:${PORT}`);
});
