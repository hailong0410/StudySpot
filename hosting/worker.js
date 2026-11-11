/* The build supplies trusted HTML, CSS, JS and choice labels from the Flask project. */
const headers = {
  "cache-control": "no-store",
  "content-security-policy": "default-src 'self'; base-uri 'none'; frame-ancestors 'self' https://chatgpt.com; form-action 'self'",
  "x-content-type-options": "nosniff",
};

const minute = 60_000;
const historyRetention = 7 * 24 * 60 * minute;
const recentQuery = "SELECT crowd, noise, created_at FROM observations WHERE space_id = ? AND created_at >= ? ORDER BY created_at DESC, id DESC LIMIT 5";

function html(body, status = 200, extra = {}) {
  return new Response(body, {
    status,
    headers: { ...headers, "content-type": "text/html; charset=utf-8", ...extra },
  });
}

function json(body, status = 200) {
  return Response.json(body, { status, headers });
}

function problem(message, path, status, extra = {}) {
  return html(`<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>StudySpot</title><link rel="stylesheet" href="/static/style.css"><main><h1>${message}</h1><a href="${path}">Back to StudySpot</a></main></html>`, status, extra);
}

function age(timestamp, now) {
  const minutes = Math.max(0, Math.floor((now - timestamp) / minute));
  if (minutes === 0) return "Just now";
  if (minutes < 60) return `${minutes} min ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours} hour${hours === 1 ? "" : "s"} ago`;
  const days = Math.floor(hours / 24);
  return `${days} day${days === 1 ? "" : "s"} ago`;
}

function observationPanel(rows, now) {
  const title = '<div id="observations"><section id="latest" class="latest" aria-labelledby="latest-title"><h2 id="latest-title">Latest crowd and noise report</h2>';
  if (!rows.length) {
    return title + '<p>No updates yet.</p><p class="muted">Be the first to share what you notice.</p></section></div>';
  }

  const [latest] = rows;
  const datetime = new Date(latest.created_at).toISOString();
  const displayTime = datetime.slice(0, 16).replace("T", " ") + " UTC";
  const stale = now - latest.created_at >= 60 * minute;
  const note = stale
    ? '<p class="stale">This report is at least 60 minutes old. Conditions may have changed.</p>'
    : '<p class="fresh">Recent observation. Conditions may still change.</p>';
  const history = rows.map((row) =>
    `<div class="history-row"><span>${data.crowd[row.crowd]} · ${data.noise[row.noise]}</span><span>${age(row.created_at, now)}</span></div>`,
  ).join("");

  return title +
    `<p class="report-main">${data.crowd[latest.crowd]} <span>·</span> ${data.noise[latest.noise]}</p>` +
    `<p class="report-time">${age(latest.created_at, now)} · <time datetime="${datetime}">${displayTime}</time></p>` +
    note + '</section><section class="history" aria-labelledby="history-title"><h2 id="history-title">Recent observations</h2>' +
    history + "</section></div>";
}

async function sourceKey(request, secret) {
  const encoder = new TextEncoder();
  const key = await crypto.subtle.importKey(
    "raw", encoder.encode(secret), { name: "HMAC", hash: "SHA-256" }, false, ["sign"],
  );
  const address = request.headers.get("CF-Connecting-IP") || "unavailable";
  const signature = await crypto.subtle.sign("HMAC", key, encoder.encode(address));
  return Array.from(new Uint8Array(signature), (byte) => byte.toString(16).padStart(2, "0")).join("");
}

async function submit(request, url, env, id, path) {
  if (request.headers.get("Origin") !== url.origin) {
    return problem("Open the space page to submit a report.", path, 403);
  }
  if (!request.headers.get("Content-Type")?.toLowerCase().startsWith("application/x-www-form-urlencoded")) {
    return problem("Please use the report form.", path, 415);
  }
  const reader = request.body?.getReader();
  const decoder = new TextDecoder();
  let body = "";
  let bytes = 0;
  if (reader) {
    for (;;) {
      const chunk = await reader.read();
      if (chunk.done) break;
      bytes += chunk.value.byteLength;
      if (bytes > 1024) {
        await reader.cancel();
        return problem("The report is too large.", path, 413);
      }
      body += decoder.decode(chunk.value, { stream: true });
    }
    body += decoder.decode();
  }
  const values = new URLSearchParams(body);
  const crowd = values.get("crowd");
  const noise = values.get("noise");
  if (!Object.hasOwn(data.crowd, crowd) || !Object.hasOwn(data.noise, noise)) {
    return problem("Select a crowd level and a noise level.", path, 400);
  }

  if (!env.REPORT_SOURCE_KEY) return problem("Reporting is temporarily unavailable.", path, 503);
  const source = await sourceKey(request, env.REPORT_SOURCE_KEY);
  const now = Date.now();
  const [result] = await env.DB.batch([
    env.DB.prepare(
      `INSERT INTO observations (space_id, crowd, noise, created_at, source_key)
       SELECT ?, ?, ?, ?, ? WHERE NOT EXISTS (
         SELECT 1 FROM observations WHERE space_id = ? AND source_key = ? AND created_at > ?
       )`,
    ).bind(id, crowd, noise, now, source, id, source, now - minute),
    env.DB.prepare("DELETE FROM observations WHERE created_at < ?").bind(now - historyRetention),
    env.DB.prepare("UPDATE observations SET source_key = NULL WHERE created_at <= ? AND source_key IS NOT NULL")
      .bind(now - minute),
  ]);
  if (result.meta.changes === 0) {
    return problem("Please wait before sending another report for this space.", path, 429, { "retry-after": "60" });
  }

  return new Response(null, { status: 303, headers: { ...headers, location: path + "?reported=1#latest" } });
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const route = url.pathname.replace(/\/$/, "") || "/";
    try {
      if (route === "/health" && request.method === "GET") {
        await env.DB.prepare("SELECT id FROM observations LIMIT 1").first();
        return json({ status: "ok", dataset: "campus" });
      }
      if (route === "/" && request.method === "GET") return html(data.pages["/"]);
      if (route.startsWith("/static/") && request.method === "GET") {
        const name = route.slice("/static/".length);
        if (!Object.hasOwn(data.assets, name)) return new Response(null, { status: 404, headers });
        const type = name.endsWith(".css") ? "text/css" : "text/javascript";
        return new Response(data.assets[name], { headers: { ...headers, "content-type": type + "; charset=utf-8" } });
      }
      const space = route.match(/^\/spaces\/(\d+)(?:\/(live|reports))?$/);
      if (space) {
        const [, id, action] = space;
        const path = `/spaces/${id}`;
        if (!Object.hasOwn(data.pages, path)) return problem("Study space not found.", "/", 404);
        if (action === "reports" && request.method === "POST") return await submit(request, url, env, Number(id), path);
        if (action !== "reports" && request.method === "GET") {
          const now = Date.now();
          const { results } = await env.DB.prepare(recentQuery).bind(Number(id), now - historyRetention).all();
          const panel = observationPanel(results, now);
          if (action === "live") return html(panel);
          let page = data.pages[path].replace("<!--OBSERVATIONS-->", () => panel);
          if (url.searchParams.get("reported") === "1") {
            page = page.replace("<main>", '<main><div class="success" role="status">Your update was saved.</div>');
          }
          return html(page);
        }
        return problem("This action is unavailable.", path, 405, { allow: action === "reports" ? "POST" : "GET" });
      }
      return problem("Page not found.", "/", 404);
    } catch {
      if (route === "/health") return json({ status: "unavailable", dataset: "campus" }, 503);
      return problem("StudySpot is temporarily unavailable. Try again shortly.", "/", 503);
    }
  },
};
