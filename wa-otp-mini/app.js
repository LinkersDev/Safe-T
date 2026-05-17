import makeWASocket, {
  DisconnectReason,
  useMultiFileAuthState,
  fetchLatestBaileysVersion,
} from '@whiskeysockets/baileys';
import express from 'express';
import pino from 'pino';
import QRCode from 'qrcode';

const PORT = process.env.PORT || 3001;
const app = express();
app.use(express.json());

let sock = null;
let isConnecting = false;
let latestQR = null;

async function connectWhatsApp() {
  if (isConnecting) return;
  isConnecting = true;

  console.log('Connecting WhatsApp...');

  const { state, saveCreds } = await useMultiFileAuthState('auth');
  const { version } = await fetchLatestBaileysVersion();

  sock = makeWASocket({
    version,
    printQRInTerminal: false,
    auth: state,
    logger: pino({ level: 'silent' }),
    browser: ['WA-OTP-Mini', 'Chrome', '1.0.0'],
    markOnlineOnConnect: false,
    syncFullHistory: false,
  });

  sock.ev.on('creds.update', saveCreds);

  sock.ev.on('connection.update', async ({ connection, lastDisconnect, qr }) => {
    if (qr) {
      latestQR = await QRCode.toDataURL(qr);
      console.log('QR ready → open http://localhost:' + PORT + '/qr in your browser');
    }

    if (connection === 'open') {
      latestQR = null;
      console.log('WhatsApp Connected ✓');
      isConnecting = false;
    }

    if (connection === 'close') {
      const code = lastDisconnect?.error?.output?.statusCode;
      const shouldReconnect = code !== DisconnectReason.loggedOut;
      isConnecting = false;
      sock = null;
      latestQR = null;

      if (shouldReconnect) {
        console.log(`WhatsApp disconnected (code ${code}). Reconnecting in 4s...`);
        setTimeout(connectWhatsApp, 4000);
      } else {
        console.log('WhatsApp logged out. Call GET /connect to reconnect.');
      }
    }
  });
}

// ─── Routes ───────────────────────────────────────────────────────────────────

// GET /connect — start WhatsApp, QR appears in browser at /qr
app.get('/connect', async (req, res) => {
  if (sock?.user) {
    return res.json({ ok: true, message: 'Already connected', phone: sock.user.id });
  }
  try {
    connectWhatsApp(); // non-blocking — QR will appear at /qr
    res.json({ ok: true, message: 'Connecting... Open /qr in your browser to scan the QR code.' });
  } catch (err) {
    res.status(500).json({ ok: false, error: err.message });
  }
});

// GET /qr-data — returns QR as JSON (polled by the browser page)
app.get('/qr-data', (req, res) => {
  res.json({
    connected: Boolean(sock?.user),
    qr: latestQR,
  });
});

// GET /qr — browser page that auto-refreshes QR every 2 seconds
app.get('/qr', (req, res) => {
  res.setHeader('Content-Type', 'text/html');
  res.send(`<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Scan WhatsApp QR</title>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body {
      background: #000;
      color: #fff;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      min-height: 100vh;
      font-family: Arial, sans-serif;
    }
    h1 { font-size: 1.4rem; margin-bottom: 24px; color: #25d366; }
    #qr-img { width: 280px; height: 280px; border-radius: 12px; }
    #status {
      margin-top: 20px;
      font-size: 0.95rem;
      color: #aaa;
    }
    #status.connected { color: #25d366; font-weight: bold; font-size: 1.1rem; }
    #waiting { color: #888; margin-top: 12px; font-size: 0.85rem; }
  </style>
</head>
<body>
  <h1>Scan WhatsApp QR</h1>
  <img id="qr-img" src="" alt="QR Code" style="display:none" />
  <div id="status">Waiting for QR code...</div>
  <div id="waiting"></div>

  <script>
    const img = document.getElementById('qr-img');
    const status = document.getElementById('status');
    const waiting = document.getElementById('waiting');

    async function poll() {
      try {
        const res = await fetch('/qr-data');
        const data = await res.json();

        if (data.connected) {
          img.style.display = 'none';
          status.textContent = '✓ WhatsApp Connected!';
          status.className = 'connected';
          waiting.textContent = 'You can close this tab.';
          return; // stop polling
        }

        if (data.qr) {
          img.src = data.qr;
          img.style.display = 'block';
          status.textContent = 'Open WhatsApp → Linked Devices → Scan QR';
          status.className = '';
        } else {
          img.style.display = 'none';
          status.textContent = 'Waiting for QR code... Make sure you called /connect';
        }
      } catch (e) {
        status.textContent = 'Error fetching QR. Is the server running?';
      }
      setTimeout(poll, 2000);
    }

    poll();
  </script>
</body>
</html>`);
});

// POST /send — send a WhatsApp message
// Body: { "phone": "2526XXXXXXX", "message": "Your OTP is 123456" }
app.post('/send', async (req, res) => {
  const { phone, message } = req.body;

  if (!phone || !message) {
    return res.status(400).json({ ok: false, error: '"phone" and "message" are required' });
  }

  if (!sock?.user) {
    return res.status(503).json({
      ok: false,
      error: 'WhatsApp is not connected. Call GET /connect first.',
    });
  }

  try {
    const jid = `${String(phone).replace(/\D/g, '')}@s.whatsapp.net`;
    await sock.sendMessage(jid, { text: message });
    console.log(`Message sent → ${phone}`);
    res.json({ ok: true, message: 'Message sent' });
  } catch (err) {
    console.error('Send failed:', err.message);
    res.status(500).json({ ok: false, error: err.message });
  }
});

// GET /status — check connection state
app.get('/status', (req, res) => {
  res.json({
    ok: true,
    connected: Boolean(sock?.user),
    phone: sock?.user?.id ?? null,
  });
});

// ─── Start ────────────────────────────────────────────────────────────────────
app.listen(PORT, () => {
  console.log(`\nWA-OTP-Mini running on port ${PORT}`);
  console.log('──────────────────────────────');
  console.log('GET  /connect  → start WhatsApp connection');
  console.log('GET  /qr       → open in browser to scan QR');
  console.log('GET  /qr-data  → JSON QR data (polled by browser)');
  console.log('POST /send     → { phone, message }');
  console.log('GET  /status   → check connection state');
  console.log('──────────────────────────────\n');

  // Auto-connect on startup if auth session already exists
  connectWhatsApp();
});
