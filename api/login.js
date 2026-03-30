const crypto = require('crypto');

function generateToken() {
  const timestamp = Date.now().toString();
  const secret = process.env.AUTH_SECRET || '';
  const hmac = crypto.createHmac('sha256', secret).update('auth:' + timestamp).digest('hex');
  return `${timestamp}.${hmac}`;
}

function safeEqual(a, b) {
  if (a.length !== b.length) return false;
  return crypto.timingSafeEqual(a, b);
}

module.exports = async function handler(req, res) {
  if (req.method !== 'POST') {
    return res.status(405).end();
  }

  let body = req.body;
  if (!body) {
    try {
      const chunks = [];
      for await (const chunk of req) chunks.push(chunk);
      body = JSON.parse(Buffer.concat(chunks).toString());
    } catch {
      body = {};
    }
  }
  if (typeof body === 'string') {
    try { body = JSON.parse(body); } catch { body = {}; }
  }

  const { id, password } = body || {};
  const validId = process.env.AUTH_ID || '';
  const validPw = process.env.AUTH_PASSWORD || '';

  if (!validId || !validPw) {
    return res.status(500).json({ ok: false, error: '서버 설정 오류' });
  }

  const idBuf = Buffer.from(String(id || ''));
  const pwBuf = Buffer.from(String(password || ''));
  const validIdBuf = Buffer.from(validId);
  const validPwBuf = Buffer.from(validPw);

  const idMatch = safeEqual(idBuf, validIdBuf);
  const pwMatch = safeEqual(pwBuf, validPwBuf);

  if (idMatch && pwMatch) {
    const token = generateToken();
    return res.status(200).json({ ok: true, token });
  }

  return res.status(401).json({ ok: false, error: 'ID 또는 비밀번호가 올바르지 않습니다.' });
};
