import 'dotenv/config';
import express from 'express';

const requiredEnv = ['JWT_SECRET', 'SESSION_SECRET'];
const missing = requiredEnv.filter((key) => !process.env[key]);

if (missing.length > 0) {
  throw new Error(`Missing required environment variables: ${missing.join(', ')}`);
}

const app = express();
const host = process.env.HOST || '127.0.0.1';
const port = Number(process.env.PORT || 3020);

app.get('/health', (_request, response) => {
  response.json({
    status: 'OK',
    service: 'auth.syn.gl',
    timestamp: new Date().toISOString(),
  });
});

app.get('/', (_request, response) => {
  response.type('text/plain').send('auth.syn.gl identity service');
});

app.listen(port, host, () => {
  console.log(`auth.syn.gl listening on http://${host}:${port}`);
});
