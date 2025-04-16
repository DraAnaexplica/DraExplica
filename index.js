require('dotenv').config();
const express = require('express');
const axios = require('axios');
const bodyParser = require('body-parser');

const app = express();
app.use(bodyParser.json());

const memoriaCurta = new Map();

const promptSistema = `
Você é a Dra. Ana, uma médica carismática e empática que atende mulheres entre 30 e 55 anos via WhatsApp.
Sua missão é ajudar a identificar causas hormonais e emocionais de sintomas íntimos, explicar com clareza e orientar o que a paciente deve cobrar dos médicos.
Responda sempre com acolhimento, realismo e tom humano, como uma amiga com conhecimento médico profundo. Não mencione que é IA.
`;

app.post('/on-new-message', async (req, res) => {
  const body = req.body;
  console.log('[WEBHOOK RECEBIDO]', JSON.stringify(body, null, 2));

  try {
    const fromMe = body.fromMe;
    const senderPhone = body.phone;
    const userMessage = body?.text?.message;

    if (!userMessage || !senderPhone || fromMe) {
      console.warn('⚠️ Ignorado: mensagem vazia, enviada por mim ou sem telefone.');
      return res.status(400).send({ status: 'ignored' });
    }

    console.log(`📩 ${senderPhone}: ${userMessage}`);

    const historico = memoriaCurta.get(senderPhone) || [];
    historico.push({ role: 'user', content: userMessage });

    const mensagens = [
      { role: 'system', content: promptSistema },
      ...(historico.length > 4 ? historico.slice(-4) : historico)
    ];

    const respostaIA = await axios.post('https://openrouter.ai/api/v1/chat/completions', {
      model: process.env.OPENROUTER_MODEL || 'google/gemini-1.5-flash',
      messages: mensagens
    }, {
      headers: {
        'Authorization': `Bearer ${process.env.OPENROUTER_API_KEY}`,
        'Content-Type': 'application/json'
      }
    });

    const respostaTexto = respostaIA.data.choices[0].message.content;
    console.log(`🤖 Dra. Ana: ${respostaTexto}`);

    memoriaCurta.set(senderPhone, [...mensagens, { role: 'assistant', content: respostaTexto }]);

    await axios.post(
      `https://api.z-api.io/instances/${process.env.Z_API_INSTANCE_ID}/token/${process.env.Z_API_INSTANCE_TOKEN}/send-text`,
      {
        phone: senderPhone,
        message: respostaTexto
      },
      {
        headers: {
          'Content-Type': 'application/json',
          'client-token': process.env.Z_API_CLIENT_TOKEN
        }
      }
    );

    res.status(200).send({ status: 'resposta enviada' });

  } catch (err) {
    console.error('[ERRO INTERNO]', err?.response?.data || err.message);
    res.status(500).send({ status: 'erro', detalhe: err.message });
  }
});

app.get('/', (req, res) => {
  res.send('🤖 Dra. Ana está online!');
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`✅ Servidor rodando em http://localhost:${PORT}`);
});
