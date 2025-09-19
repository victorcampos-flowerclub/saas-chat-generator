const express = require('express');
const cors = require('cors');
const helmet = require('helmet');
const qrcode = require('qrcode');
const axios = require('axios');
const winston = require('winston');
const { Client, LocalAuth } = require('whatsapp-web.js');
require('dotenv').config();

// Configuração do logger
const logger = winston.createLogger({
  level: 'info',
  format: winston.format.combine(
    winston.format.timestamp(),
    winston.format.json()
  ),
  transports: [
    new winston.transports.Console()
  ]
});

// Configuração da aplicação
const app = express();
const PORT = process.env.PORT || 8080;
const BACKEND_URL = process.env.BACKEND_URL || 'https://saas-chat-backend-365442086139.us-east1.run.app';
const CHAT_ENGINE_URL = process.env.CHAT_ENGINE_URL || 'https://saas-chat-engine-365442086139.us-east1.run.app';

// Middlewares
app.use(helmet());
app.use(cors());
app.use(express.json());

// Estado global do serviço
let whatsappClient = null;
let isClientReady = false;
let qrCodeData = null;
let connectedNumber = null;
let sessionStatus = 'disconnected'; // disconnected, connecting, connected, error

// Inicialização do cliente WhatsApp
function initializeWhatsAppClient() {
  logger.info('Iniciando cliente WhatsApp...');
  
  whatsappClient = new Client({
    authStrategy: new LocalAuth({
      clientId: 'saas-chat-client'
    }),
    puppeteer: {
      headless: true,
      args: [
        '--no-sandbox',
        '--disable-setuid-sandbox',
        '--disable-dev-shm-usage',
        '--disable-accelerated-2d-canvas',
        '--no-first-run',
        '--no-zygote',
        '--single-process',
        '--disable-gpu'
      ]
    }
  });

  // Event handlers
  whatsappClient.on('qr', (qr) => {
    logger.info('QR Code gerado');
    qrCodeData = qr;
    sessionStatus = 'connecting';
    
    // Gerar imagem do QR code
    qrcode.toDataURL(qr, (err, url) => {
      if (err) {
        logger.error('Erro ao gerar QR code image:', err);
      } else {
        qrCodeData = { raw: qr, image: url };
      }
    });
  });

  whatsappClient.on('ready', () => {
    logger.info('Cliente WhatsApp conectado!');
    isClientReady = true;
    sessionStatus = 'connected';
    qrCodeData = null;
    
    // Obter informações do número conectado
    whatsappClient.info.wid.user && (connectedNumber = whatsappClient.info.wid.user);
  });

  whatsappClient.on('authenticated', () => {
    logger.info('WhatsApp autenticado com sucesso');
    sessionStatus = 'connected';
  });

  whatsappClient.on('auth_failure', (msg) => {
    logger.error('Falha na autenticação:', msg);
    sessionStatus = 'error';
    qrCodeData = null;
  });

  whatsappClient.on('disconnected', (reason) => {
    logger.warn('Cliente desconectado:', reason);
    isClientReady = false;
    sessionStatus = 'disconnected';
    connectedNumber = null;
  });

  // Handler principal de mensagens
  whatsappClient.on('message', async (message) => {
    try {
      await handleIncomingMessage(message);
    } catch (error) {
      logger.error('Erro ao processar mensagem:', error);
    }
  });

  // Inicializar cliente
  whatsappClient.initialize();
}

// Handler de mensagens recebidas
async function handleIncomingMessage(message) {
  // Ignorar mensagens enviadas por nós
  if (message.fromMe) return;
  
  // Log da mensagem recebida
  logger.info('Mensagem recebida:', {
    from: message.from,
    body: message.body,
    type: message.type
  });

  const phoneNumber = message.from.replace('@c.us', '');
  
  // Buscar chat associado a este número
  const chatInfo = await findChatByPhoneNumber(phoneNumber);
  
  if (!chatInfo) {
    // Sem chat associado - enviar mensagem padrão
    await sendDefaultWelcomeMessage(message.from);
    return;
  }

  // Processar mensagem com o chat-engine
  await processMessageWithChatEngine(chatInfo, message);
}

// Buscar chat associado ao número
async function findChatByPhoneNumber(phoneNumber) {
  try {
    // Fazer chamada para o backend para buscar chat por número
    const response = await axios.get(`${BACKEND_URL}/api/whatsapp/chats/${phoneNumber}`);
    return response.data;
  } catch (error) {
    if (error.response?.status === 404) {
      return null; // Número não associado
    }
    logger.error('Erro ao buscar chat:', error.message);
    return null;
  }
}

// Processar mensagem com chat-engine
async function processMessageWithChatEngine(chatInfo, whatsappMessage) {
  try {
    const payload = {
      chat_id: chatInfo.chat_id,
      conversation_id: `wa_${whatsappMessage.from}`,
      message: whatsappMessage.body,
      source: 'whatsapp',
      phone_number: whatsappMessage.from.replace('@c.us', '')
    };

    const response = await axios.post(`${CHAT_ENGINE_URL}/api/chat/message`, payload);
    
    if (response.data && response.data.response) {
      await sendWhatsAppMessage(whatsappMessage.from, response.data.response);
    }
  } catch (error) {
    logger.error('Erro ao processar com chat-engine:', error.message);
    await sendWhatsAppMessage(whatsappMessage.from, 'Desculpe, ocorreu um erro. Tente novamente em alguns instantes.');
  }
}

// Enviar mensagem de boas-vindas padrão
async function sendDefaultWelcomeMessage(to) {
  const welcomeMessage = `Olá! 👋

Este número ainda não está configurado com um assistente personalizado.

Para configurar seu atendimento automático, acesse: ${BACKEND_URL}

Em caso de dúvidas, entre em contato com o suporte.`;

  await sendWhatsAppMessage(to, welcomeMessage);
}

// Enviar mensagem via WhatsApp
async function sendWhatsAppMessage(to, text) {
  try {
    if (!isClientReady) {
      throw new Error('Cliente WhatsApp não está pronto');
    }

    await whatsappClient.sendMessage(to, text);
    logger.info('Mensagem enviada:', { to, text: text.substring(0, 50) + '...' });
  } catch (error) {
    logger.error('Erro ao enviar mensagem:', error.message);
    throw error;
  }
}

// ==================== ENDPOINTS API ====================

// Health check
app.get('/health', (req, res) => {
  res.json({
    status: 'ok',
    service: 'whatsapp-service',
    version: '1.0.0',
    whatsapp: {
      connected: isClientReady,
      session_status: sessionStatus,
      connected_number: connectedNumber
    },
    timestamp: new Date().toISOString()
  });
});

// Status da conexão WhatsApp
app.get('/api/whatsapp/status', (req, res) => {
  res.json({
    connected: isClientReady,
    session_status: sessionStatus,
    connected_number: connectedNumber,
    qr_available: !!qrCodeData
  });
});

// Obter QR Code para autenticação
app.get('/api/whatsapp/qr', (req, res) => {
  if (!qrCodeData) {
    return res.status(404).json({ 
      error: 'QR Code não disponível',
      session_status: sessionStatus 
    });
  }

  res.json({
    qr_code: qrCodeData.raw,
    qr_image: qrCodeData.image,
    session_status: sessionStatus
  });
});

// Reinicializar conexão WhatsApp
app.post('/api/whatsapp/restart', async (req, res) => {
  try {
    if (whatsappClient) {
      await whatsappClient.destroy();
    }
    
    isClientReady = false;
    sessionStatus = 'disconnected';
    qrCodeData = null;
    connectedNumber = null;

    // Reinicializar após delay
    setTimeout(() => {
      initializeWhatsAppClient();
    }, 2000);

    res.json({ message: 'Reinicializando conexão WhatsApp...' });
  } catch (error) {
    logger.error('Erro ao reinicializar:', error);
    res.status(500).json({ error: 'Erro ao reinicializar conexão' });
  }
});

// Enviar mensagem de teste
app.post('/api/whatsapp/send-test', async (req, res) => {
  const { phone_number, message } = req.body;

  if (!phone_number || !message) {
    return res.status(400).json({ error: 'phone_number e message são obrigatórios' });
  }

  try {
    const formattedNumber = phone_number.includes('@c.us') ? 
      phone_number : `${phone_number}@c.us`;
    
    await sendWhatsAppMessage(formattedNumber, message);
    res.json({ success: true, message: 'Mensagem enviada com sucesso' });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Associar número de telefone a um chat
app.post('/api/whatsapp/associate', async (req, res) => {
  const { phone_number, chat_id } = req.body;

  if (!phone_number || !chat_id) {
    return res.status(400).json({ error: 'phone_number e chat_id são obrigatórios' });
  }

  try {
    // Fazer chamada para o backend para associar
    const response = await axios.post(`${BACKEND_URL}/api/whatsapp/associate`, {
      phone_number,
      chat_id
    });

    res.json(response.data);
  } catch (error) {
    logger.error('Erro ao associar número:', error.message);
    res.status(500).json({ error: 'Erro ao associar número ao chat' });
  }
});

// Middleware de tratamento de erros
app.use((error, req, res, next) => {
  logger.error('Erro não tratado:', error);
  res.status(500).json({ error: 'Erro interno do servidor' });
});

// Inicializar servidor
app.listen(PORT, () => {
  logger.info(`WhatsApp Service rodando na porta ${PORT}`);
  
  // Inicializar cliente WhatsApp após 5 segundos
  setTimeout(() => {
    initializeWhatsAppClient();
  }, 5000);
});

// Graceful shutdown
process.on('SIGINT', async () => {
  logger.info('Encerrando serviço...');
  
  if (whatsappClient) {
    await whatsappClient.destroy();
  }
  
  process.exit(0);
});
