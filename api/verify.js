import crypto from 'crypto';

function verifyToken(token) {
  if (!token || typeof token !== 'string') return false;
  try {
    const dotIdx = token.indexOf('.');
    if (dotIdx === -1) return false;
    const timestamp = token.slice(0, dotIdx);
    const hmac = token.slice(dotIdx + 1);

    const secret = process.env.AUTH_SECRET || '';
    const expected = crypto.createHmac('sha256', secret).update('auth:' + timestamp).digest('hex');

    // Token expires in 24 hours
    const age = Date.now() - parseInt(timestamp, 10);
    if (isNaN(age) || age < 0 || age > 86400000) return false;

    const expectedBuf = Buffer.from(expected, 'hex');
    const hmacBuf = Buffer.from(hmac, 'hex');
    if (expectedBuf.length !== hmacBuf.length) return false;

    return crypto.timingSafeEqual(expectedBuf, hmacBuf);
  } catch {
    return false;
  }
}

export default function handler(req, res) {
  if (req.method !== 'POST') {
    return res.status(405).end();
  }

  let body = req.body;
  if (typeof body === 'string') {
    try { body = JSON.parse(body); } catch { body = {}; }
  }

  const { token } = body || {};
  if (verifyToken(token)) {
    return res.status(200).json({ ok: true });
  }

  return res.status(401).json({ ok: false });
}
