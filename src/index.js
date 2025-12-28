// Cloudflare Worker entrypoint
// - Sirve archivos estáticos desde ./public (binding env.ASSETS)
// - Firma de integridad Wompi: POST /api/wompi/signature
// - Webhook Wompi (URL de eventos): POST /api/wompi/webhook

function jsonResponse(obj, status = 200, extraHeaders = {}) {
  return new Response(JSON.stringify(obj), {
    status,
    headers: {
      'content-type': 'application/json; charset=utf-8',
      ...extraHeaders,
    },
  });
}

async function sha256Hex(input) {
  const data = new TextEncoder().encode(input);
  const hashBuffer = await crypto.subtle.digest('SHA-256', data);
  const hashArray = Array.from(new Uint8Array(hashBuffer));
  return hashArray.map((b) => b.toString(16).padStart(2, '0')).join('');
}

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);

    if (url.pathname === '/health') {
      return jsonResponse({ ok: true, hasAssets: !!env.ASSETS, hasStaticContent: !!env.__STATIC_CONTENT });
    }

    // Preflight (si en el futuro llamas desde otro dominio)
    if (request.method === 'OPTIONS') {
      return new Response(null, {
        status: 204,
        headers: {
          'access-control-allow-origin': '*',
          'access-control-allow-methods': 'GET,POST,OPTIONS',
          'access-control-allow-headers': 'content-type',
        },
      });
    }

    if (url.pathname === '/api/wompi/signature') {
      if (request.method !== 'POST') {
        return jsonResponse({ error: 'Method not allowed' }, 405, { 'access-control-allow-origin': '*' });
      }

      // Importante: NO mezclar secretos entre modos.
      // Si el frontend indica mode=test, exigimos WOMPI_INTEGRITY_SECRET_TEST.
      // Si indica mode=prod, exigimos WOMPI_INTEGRITY_SECRET_PROD.
      // Solo si no llega mode, usamos WOMPI_INTEGRITY_SECRET (fallback).

      let payload;
      try {
        payload = await request.json();
      } catch {
        return jsonResponse({ error: 'Invalid JSON body' }, 400, { 'access-control-allow-origin': '*' });
      }

      const reference = String(payload?.reference ?? '').trim();
      const amountInCents = Number(payload?.amountInCents);
      const currency = String(payload?.currency ?? env.WOMPI_CURRENCY ?? 'COP').trim();
      const mode = String(payload?.mode ?? '').trim().toLowerCase();

      if (!reference) {
        return jsonResponse({ error: 'reference is required' }, 400, { 'access-control-allow-origin': '*' });
      }
      if (!Number.isFinite(amountInCents) || amountInCents <= 0) {
        return jsonResponse({ error: 'amountInCents must be a positive number' }, 400, { 'access-control-allow-origin': '*' });
      }
      if (!currency) {
        return jsonResponse({ error: 'currency is required' }, 400, { 'access-control-allow-origin': '*' });
      }

      let secret;
      if (mode === 'test') {
        secret = env.WOMPI_INTEGRITY_SECRET_TEST;
        if (!secret) {
          return jsonResponse(
            { error: 'Missing WOMPI_INTEGRITY_SECRET_TEST for mode=test. Configure it as a Cloudflare secret and redeploy.' },
            500,
            { 'access-control-allow-origin': '*' }
          );
        }
      } else if (mode === 'prod') {
        secret = env.WOMPI_INTEGRITY_SECRET_PROD;
        if (!secret) {
          return jsonResponse(
            { error: 'Missing WOMPI_INTEGRITY_SECRET_PROD for mode=prod. Configure it as a Cloudflare secret and redeploy.' },
            500,
            { 'access-control-allow-origin': '*' }
          );
        }
      } else {
        secret = env.WOMPI_INTEGRITY_SECRET;
        if (!secret) {
          return jsonResponse(
            { error: 'Missing WOMPI_INTEGRITY_SECRET (no mode provided). Configure it as a Cloudflare secret and redeploy.' },
            500,
            { 'access-control-allow-origin': '*' }
          );
        }
      }

      const concatenated = `${reference}${Math.round(amountInCents)}${currency}${secret}`;
      const integrity = await sha256Hex(concatenated);

      return jsonResponse({ integrity }, 200, { 'access-control-allow-origin': '*' });
    }

    if (url.pathname === '/api/wompi/webhook') {
      // GitHub Pages no recibe webhooks; aquí sí. Puedes conectar este endpoint en Wompi.
      // Por ahora solo confirma recepción.
      if (request.method !== 'POST') {
        return jsonResponse({ error: 'Method not allowed' }, 405);
      }

      // Puedes guardar/reenviar el evento (KV/D1/Email) si lo necesitas.
      return jsonResponse({ ok: true });
    }

    // Static assets (index.html, etc.)
    if (env.ASSETS && typeof env.ASSETS.fetch === 'function') {
      return env.ASSETS.fetch(request);
    }

    // Fallback for some asset-binding modes
    if (env.__STATIC_CONTENT) {
      return new Response(
        'Static content binding detected but ASSETS is not configured. Ensure you are using Wrangler assets.directory (wrangler.toml) and redeploy.',
        { status: 500 }
      );
    }

    return new Response('ASSETS binding not configured. Check wrangler.toml [assets] directory and redeploy.', { status: 500 });
  },
};
