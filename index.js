import express from 'express';
import bodyParser from 'body-parser';
import dotenv from 'dotenv';
import axios from 'axios';
import { pool } from './db.js'; // ✅ Conexão PostgreSQL

dotenv.config();

const app = express();
app.use(bodyParser.json());

const PORT = process.env.PORT || 3000;

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

// === OpenRouter ===
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
    return response.data?.choices?.[0]?.message?.content || '[Sem resposta da IA]';
  } catch (error) {
    console.error('[ERRO OPENROUTER]', error.response?.data || error.message);
    return '[Erro ao consultar a IA]';
  }
}

// === Z-API ===
async function sendZapiMessage(phone, message) {
  try {
    await axios.post(
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
    console.error("❌ ERRO AO ENVIAR Z-API:", error.response?.data || error.message);
  }
}

// === Webhook ===
app.post('/on-new-message', async (req, res) => {
  const { text, phone, fromMe } = req.body;

  const userMessage = text?.message;

  if (!userMessage || !phone || fromMe) {
    console.warn('⚠️ Ignorado: mensagem vazia, enviada por mim ou sem telefone.');
    return res.sendStatus(200);
  }

  console.log(`📩 ${phone}: ${userMessage}`);
  const aiReply = await getAIResponse(userMessage);
  console.log(`🤖 Dra. Ana: ${aiReply}`);

  // ✅ Salvar no banco
  try {
    await pool.query(
      'INSERT INTO chat_history (phone, message, sender) VALUES ($1, $2, $3)',
      [phone, userMessage, 'user']
    );
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

app.listen(PORT, () => {
  console.log(`✅ Servidor rodando em http://localhost:${PORT}`);
});
