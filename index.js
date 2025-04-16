// index.js

import express from 'express';
import bodyParser from 'body-parser';
import dotenv from 'dotenv';
import axios from 'axios';

dotenv.config();

const app = express();
app.use(bodyParser.json());

const PORT = process.env.PORT || 3000;

// --- IA: OpenRouter ---
async function getAIResponse(message) {
  try {
    const response = await axios.post(
      'https://openrouter.ai/api/v1/chat/completions',
      {
        model: process.env.OPENROUTER_MODEL,
        messages: [
          {
            role: 'user',
            content: message
          }
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
    console.error('[ERRO OPENROUTER]', error.response?.data || error.message);
    return '[Erro ao consultar a IA]';
  }
}

// --- Enviar mensagem via Z-API ---
async function sendZapiMessage(phone, message) {
  try {
    const response = await axios.post(
      `https://api.z-api.io/instances/${process.env.ZAPI_INSTANCE_ID}/token/${process.env.ZAPI_INSTANCE_TOKEN}/send-text`,
      {
        phone: phone,
        message: message
      },
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

  await sendZapiMessage(phone, aiReply);
  res.sendStatus(200);
});

// --- Start ---
app.listen(PORT, () => {
  console.log(`✅ Servidor rodando em http://localhost:${PORT}`);
});
