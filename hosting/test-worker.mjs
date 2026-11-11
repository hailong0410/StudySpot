import { readFileSync } from "node:fs";
import { DatabaseSync } from "node:sqlite";
import assert from "node:assert/strict";
import { test } from "node:test";

const source = readFileSync(new URL("../dist/server/index.js", import.meta.url), "utf8");
const { default: worker } = await import("data:text/javascript;base64," + Buffer.from(source).toString("base64"));
const schema = readFileSync(new URL("./drizzle/0000_observations.sql", import.meta.url), "utf8");
const origin = "https://studyspot.test";

function fixture() {
  const sqlite = new DatabaseSync(":memory:");
  sqlite.exec(schema);
  const DB = {
    prepare(sql) {
      const query = sqlite.prepare(sql);
      return {
        first: async () => query.get(),
        bind(...values) {
          return {
            all: async () => ({ results: query.all(...values) }),
            run: () => ({ meta: query.run(...values) }),
          };
        },
      };
    },
    async batch(statements) {
      sqlite.exec("BEGIN IMMEDIATE");
      try {
        const results = statements.map((statement) => statement.run());
        sqlite.exec("COMMIT");
        return results;
      } catch (error) {
        sqlite.exec("ROLLBACK");
        throw error;
      }
    },
  };
  const env = { DB, REPORT_SOURCE_KEY: "isolated-test-key" };
  return (path, options) => worker.fetch(new Request(origin + path, options), env);
}

function report({ address = "192.0.2.1", site = origin, body = "crowd=high&noise=loud" } = {}) {
  return {
    method: "POST",
    headers: {
      "Origin": site,
      "Content-Type": "application/x-www-form-urlencoded",
      "CF-Connecting-IP": address,
    },
    body,
  };
}

test("real catalog starts empty and a second client sees the report for the same room", async () => {
  const request = fixture();
  assert.deepEqual(await (await request("/health")).json(), { status: "ok", dataset: "campus" });
  assert.match(await (await request("/")).text(), /Grand Reading Room/);
  const initial = await request("/spaces/1");
  const policy = initial.headers.get("content-security-policy");
  assert.equal(
    policy.split(";").map((directive) => directive.trim()).find((directive) => directive.startsWith("frame-ancestors ")),
    "frame-ancestors 'self' https://chatgpt.com",
  );
  const initialPage = await initial.text();
  assert.match(initialPage, /No updates yet/);
  assert.match(initialPage, /Official hours/);
  assert.doesNotMatch(initialPage, /csrf_token|fictional|OBSERVATIONS/);
  const created = await request("/spaces/1/reports", report());
  assert.equal(created.status, 303);
  assert.match(created.headers.get("location"), /^\/spaces\/1\?/);
  const feed = await request("/spaces/1/live");
  assert.equal(feed.headers.get("cache-control"), "no-store");
  assert.match(await feed.text(), /Very busy.*Loud/);
  assert.match(await (await request("/spaces/2/live")).text(), /No updates yet/);
});

test("report validation and per-space cooldown run before a second write", async () => {
  const request = fixture();
  assert.equal((await request("/spaces/1/reports", report({ site: "https://other.test" }))).status, 403);
  assert.equal((await request("/spaces/1/reports", report({ site: "https://chatgpt.com" }))).status, 403);
  assert.equal((await request("/spaces/1/reports", report({ body: "crowd=toString&noise=loud" }))).status, 400);
  assert.equal((await request("/spaces/1/reports", report({ body: "x".repeat(1025) }))).status, 413);
  assert.equal((await request("/spaces/99/reports", report())).status, 404);
  const simultaneous = await Promise.all([
    request("/spaces/1/reports", report()),
    request("/spaces/1/reports", report()),
  ]);
  assert.deepEqual(simultaneous.map((response) => response.status).sort(), [303, 429]);
  assert.equal((await request("/spaces/2/reports", report())).status, 303);
  assert.equal((await request("/spaces/1/reports", report({ address: "192.0.2.2" }))).status, 303);
});


test("report timestamps show Nashville time in winter and summer", async (t) => {
  let now = Date.parse("2026-11-11T23:19:00Z");
  t.mock.method(Date, "now", () => now);
  const request = fixture();

  assert.equal((await request("/spaces/1/reports", report())).status, 303);
  now += 60_000;
  const winter = await (await request("/spaces/1/live")).text();
  assert.match(winter, /1 min ago.*datetime="2026-11-11T23:19:00.000Z".*5:19 PM CST/);

  now = Date.parse("2026-07-11T23:19:00Z");
  assert.equal((await request("/spaces/2/reports", report())).status, 303);
  const summer = await (await request("/spaces/2/live")).text();
  assert.match(summer, /datetime="2026-07-11T23:19:00.000Z".*6:19 PM CDT/);
});
