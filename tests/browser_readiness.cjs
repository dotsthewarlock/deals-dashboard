'use strict';
// Browser regressions use a disposable synthetic-only server and invented credentials.
const { test, before, after } = require('node:test');
const assert = require('node:assert/strict');
const { spawn } = require('node:child_process');
const { once } = require('node:events');
const readline = require('node:readline');
const { chromium } = require('playwright');
let server, browser, origin;
const password = 'SYNTHETIC browser-only passphrase!';
const defer = () => { let resolve; const promise = new Promise(r => { resolve = r; }); return { promise, resolve }; };
before(async () => {
  server = spawn('python3', ['-m', 'tests.browser_server'], { stdio: ['ignore', 'pipe', 'inherit'] });
  const lines = readline.createInterface({ input: server.stdout });
  const timeout = setTimeout(() => server.kill(), 15000);
  try {
    const [port] = await once(lines, 'line');
    assert.match(port, /^\d+$/); origin = 'http://127.0.0.1:' + port;
    browser = await chromium.launch({ headless: true });
    console.log('Browser:', await browser.version());
  } finally { clearTimeout(timeout); lines.close(); }
});
after(async () => {
  if (browser) await browser.close();
  if (server && server.exitCode === null) { const exit = once(server, 'exit'); server.kill(); await exit; }
});
async function pageFor(t, viewport = { width: 1280, height: 800 }) {
  const context = await browser.newContext({ viewport });
  t.after(() => context.close());
  const page = await context.newPage();
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  t.after(() => assert.deepEqual(errors, []));
  await page.goto(origin);
  await page.locator('#password').fill(password);
  await page.locator('#login-form button').click();
  await page.locator('#reader').waitFor({ state: 'visible' });
  await page.waitForFunction(() => profile !== null && !checking);
  return { page, context };
}
async function checkCleared(page) {
  await page.locator('#reader').waitFor({ state: 'hidden' });
  assert.equal(await page.locator('#articles').textContent(), '');
  assert.equal(await page.locator('#sources').textContent(), '');
  assert.equal(await page.locator('#profile-name').inputValue(), '');
  assert.equal(await page.locator('#mode').textContent(), '');
}
for (const viewport of [{ width: 1280, height: 800 }, { width: 390, height: 844 }]) {
  test(`authenticated synthetic reader/profile/reload/logout at ${viewport.width}x${viewport.height}`, async t => {
    const { page, context } = await pageFor(t, viewport);
    assert.equal(await page.locator('#mode').textContent().then(x => x.includes('SYNTHETIC')), true);
    await page.locator('#settings-tab').click();
    await page.locator('#market-ca').check(); await page.locator('#market-us').check();
    await page.locator('#source-ca').check(); await page.locator('#source-us').check();
    await page.locator('#include').fill(''); await page.locator('#exclude').fill('');
    await page.locator('#profile-name').fill('SYNTHETIC browser profile');
    await page.locator('#preference').selectOption('manual');
    await page.locator('#profile-form button').click();
    await page.waitForFunction(() => document.getElementById('message').textContent.includes('Profile saved'));
    await page.locator('#deals-tab').click();
    await page.locator('#refresh').click();
    await page.waitForFunction(() => !checking);
    assert.equal(await page.locator('#articles article').count(), 2);
    const links = await page.locator('#articles a').evaluateAll(nodes => nodes.map(n => ({ href: n.href, rel: n.rel })));
    assert.ok(links.every(x => x.href.startsWith('https://brickset.com/article/synthetic-') && x.rel.includes('noreferrer')));
    assert.match(await page.locator('#articles').textContent(), /Availability unknown/);
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true);
    assert.ok((await page.locator('#logout').boundingBox()).height >= 44);
    await page.locator('#settings-tab').click();
    await page.locator('#market-us').uncheck();
    await page.locator('#include').fill('Galactic');
    await page.locator('#profile-form button').click();
    await page.waitForFunction(() => document.getElementById('message').textContent.includes('Profile saved'));
    await page.locator('#deals-tab').click();
    assert.equal(await page.locator('#articles article').count(), 1);
    await page.reload();
    await page.waitForFunction(() => profile !== null && !checking);
    assert.equal(await page.locator('#articles article').count(), 1);
    assert.equal(await page.locator('#profile-heading').textContent(), 'SYNTHETIC browser profile');
    const cookies = await context.cookies();
    assert.ok(cookies.some(c => c.name === 'pilot_session' && c.httpOnly && c.sameSite === 'Strict'));
    await page.locator('#logout').click();
    await page.waitForFunction(() => !loggingOut);
    await checkCleared(page);
    assert.equal((await context.request.get(origin + '/api/deals')).status(), 401);
  });
}

test('logout invalidates delayed cache results even if fetch ignores abort', async t => {
  const { page } = await pageFor(t);
  await page.evaluate(() => { const original = fetch; window.fetch = (url, options) => original(url, { ...options, signal: undefined }); });
  const captured = defer(), release = defer();
  await page.route('**/api/deals', async route => {
    const response = await route.fetch(); captured.resolve(); await release.promise;
    await route.fulfill({ response });
  });
  await page.evaluate(() => { window.delayed = cached().catch(() => {}); });
  await captured.promise;
  await page.locator('#logout').click();
  await page.waitForFunction(() => !loggingOut);
  release.resolve(); await page.evaluate(() => window.delayed);
  await checkCleared(page);
  assert.match(await page.locator('#message').textContent(), /Signed out/);
});

test('latest cache load wins when responses complete out of order', async t => {
  const { page } = await pageFor(t);
  const captured = defer(), release = defer(); let first = true;
  await page.route('**/api/profile', async route => {
    if (!first) return route.continue();
    first = false;
    const response = await route.fetch(); const body = await response.json();
    body.name = 'SYNTHETIC obsolete response'; captured.resolve(); await release.promise;
    await route.fulfill({ response, json: body });
  });
  await page.evaluate(() => { window.oldLoad = cached().catch(() => {}); });
  await captured.promise;
  await page.evaluate(() => cached());
  const expected = await page.locator('#profile-heading').textContent();
  release.resolve(); await page.evaluate(() => window.oldLoad);
  assert.equal(await page.locator('#profile-heading').textContent(), expected);
  assert.notEqual(expected, 'SYNTHETIC obsolete response');
});

test('late obsolete 401 cannot sign out a newer view', async t => {
  const { page } = await pageFor(t);
  await page.evaluate(() => { const original = fetch; window.fetch = (url, options) => original(url, { ...options, signal: undefined }); });
  const captured = defer(), release = defer();
  await page.route('**/api/deals', async route => {
    captured.resolve(); await release.promise;
    await route.fulfill({ status: 401, contentType: 'application/json', body: '{"error":"synthetic-old-session"}' });
  });
  await page.evaluate(() => { window.oldRequest = api('deals').catch(() => {}); });
  await captured.promise;
  await page.evaluate(() => { forget(); csrf = 'synthetic-new-view'; profile = { name: 'synthetic-new-view' }; document.getElementById('reader').hidden = false; });
  release.resolve(); await page.evaluate(() => window.oldRequest);
  assert.equal(await page.evaluate(() => profile.name), 'synthetic-new-view');
  assert.equal(await page.locator('#reader').isVisible(), true);
});

test('logout clears immediately, blocks refresh completion and supports failed sign-out retry', async t => {
  const { page, context } = await pageFor(t);
  const captured = defer(), release = defer();
  await page.route('**/api/refresh', async route => {
    const response = await route.fetch(); captured.resolve(); await release.promise;
    try { await route.fulfill({ response }); } catch { /* Aborted by logout. */ }
  });
  await page.locator('#refresh').click(); await captured.promise;
  let fail = true;
  await page.route('**/api/logout', route => fail ? route.abort('failed') : route.continue());
  await page.locator('#logout').click();
  await checkCleared(page);
  await page.waitForFunction(() => !loggingOut);
  release.resolve();
  await page.locator('#logout-retry').waitFor({ state: 'visible' });
  assert.equal((await context.request.get(origin + '/api/deals')).status(), 200);
  fail = false;
  await page.locator('#logout-retry').click();
  await page.waitForFunction(() => !loggingOut);
  assert.equal((await context.request.get(origin + '/api/deals')).status(), 401);
  await checkCleared(page);
});

test('logout during a pending login waits for its cookie and revokes it', async t => {
  const { page, context } = await pageFor(t);
  await page.locator('#logout').click(); await page.waitForFunction(() => !loggingOut);
  const captured = defer(), release = defer();
  await page.route('**/api/login', async route => {
    const response = await route.fetch(); captured.resolve(); await release.promise;
    await route.fulfill({ response });
  });
  await page.locator('#password').fill(password);
  await page.locator('#login-form button').click(); await captured.promise;
  await page.evaluate(() => { window.signingOut = signOut(); });
  await checkCleared(page);
  release.resolve(); await page.evaluate(() => window.signingOut);
  assert.equal((await context.request.get(origin + '/api/deals')).status(), 401);
  await checkCleared(page);
});

test('logout invalidates a profile save already accepted by the server', async t => {
  const { page } = await pageFor(t);
  await page.evaluate(() => {
    const original = fetch;
    window.fetch = async (url, options) => {
      const response = await original(url, { ...options, signal: undefined });
      if (options.method === 'PATCH') {
        const json = response.json.bind(response);
        response.json = async () => { const value = await json(); window.saveConsumed = true; return value; };
      }
      return response;
    };
  });
  const captured = defer(), release = defer();
  await page.route('**/api/profile', async route => {
    if (route.request().method() !== 'PATCH') return route.continue();
    const response = await route.fetch(); captured.resolve(); await release.promise;
    await route.fulfill({ response });
  });
  await page.locator('#settings-tab').click();
  await page.locator('#profile-name').fill('SYNTHETIC pending save');
  await page.locator('#profile-form button').click(); await captured.promise;
  await page.locator('#logout').click(); await page.waitForFunction(() => !loggingOut);
  release.resolve();
  await page.waitForFunction(() => window.saveConsumed === true);
  await checkCleared(page);
  assert.match(await page.locator('#message').textContent(), /Signed out/);
});

test('pagehide clears private DOM and aborts pending reads before restoration', async t => {
  const { page } = await pageFor(t);
  await page.evaluate(() => window.dispatchEvent(new PageTransitionEvent('pagehide', { persisted: true })));
  await checkCleared(page);
  await page.evaluate(() => window.dispatchEvent(new PageTransitionEvent('pageshow', { persisted: true })));
  await page.waitForFunction(() => profile !== null && !checking);
  assert.equal(await page.locator('#reader').isVisible(), true);
  // This dispatch tests the lifecycle handlers, not the browser's BFCache eligibility.
});

test('article markup is literal text, CSP permits app, keyboard controls are focusable', async t => {
  const { page } = await pageFor(t);
  await page.evaluate(() => { window.violations = []; document.addEventListener('securitypolicyviolation', e => window.violations.push(e.violatedDirective)); });
  await page.route('**/api/deals', async route => {
    const response = await route.fetch(); const body = await response.json();
    if (body.articles.length) body.articles[0].title = '<img src=x onerror="window.syntheticXss=true">';
    await route.fulfill({ response, json: body });
  });
  await page.evaluate(() => cached());
  assert.equal(await page.locator('#articles img').count(), 0);
  assert.equal(await page.evaluate(() => window.syntheticXss), undefined);
  assert.match(await page.locator('#articles h3').first().textContent(), /<img/);
  await page.locator('#deals-tab').focus();
  await page.keyboard.press('Tab');
  assert.equal(await page.evaluate(() => document.activeElement.id), 'settings-tab');
  assert.deepEqual(await page.evaluate(() => window.violations), []);
  assert.equal(await page.evaluate(() => localStorage.length + sessionStorage.length), 0);
});

test('real local TLS delivers Secure __Host cookie and rejects CSRF and logout replay', async t => {
  const tlsServer = spawn('python3', ['-m', 'tests.browser_server', '--https'], { stdio: ['ignore', 'pipe', 'inherit'] });
  t.after(async () => { if (tlsServer.exitCode === null) { const exit = once(tlsServer, 'exit'); tlsServer.kill(); await exit; } });
  const lines = readline.createInterface({ input: tlsServer.stdout });
  const [port] = await once(lines, 'line'); lines.close();
  assert.match(port, /^\d+$/);
  const tlsOrigin = 'https://127.0.0.1:' + port;
  const context = await browser.newContext({ ignoreHTTPSErrors: true });
  t.after(() => context.close());
  const page = await context.newPage();
  await page.goto(tlsOrigin);
  await page.locator('#password').fill(password); await page.locator('#login-form button').click();
  await page.waitForFunction(() => profile !== null && !checking);
  const cookie = (await context.cookies()).find(c => c.name === '__Host-pilot_session');
  assert.ok(cookie && cookie.secure && cookie.httpOnly && cookie.sameSite === 'Strict' && cookie.path === '/');
  const bad = await context.request.post(tlsOrigin + '/api/logout', { data: {}, headers: { Origin: tlsOrigin, 'X-CSRF-Token': 'synthetic-invalid' } });
  assert.equal(bad.status(), 403);
  const replay = cookie.value;
  await page.locator('#logout').click(); await page.waitForFunction(() => !loggingOut);
  const denied = await context.request.get(tlsOrigin + '/api/deals', { headers: { Cookie: '__Host-pilot_session=' + replay } });
  assert.equal(denied.status(), 401);
  await checkCleared(page);
});

test('a delayed initial anonymous session response cannot clear a successful login', async t => {
  const context = await browser.newContext(); t.after(() => context.close());
  const page = await context.newPage();
  await page.addInitScript(() => {
    const original = fetch;
    window.fetch = async (url, options) => {
      const response = await original(url, { ...options, signal: undefined });
      if (url === '/api/session') {
        const json = response.json.bind(response);
        response.json = async () => { const value = await json(); window.sessionReads = (window.sessionReads || 0) + 1; return value; };
      }
      return response;
    };
  });
  const captured = defer(), release = defer(); let first = true;
  await page.route('**/api/session', async route => {
    if (!first) return route.continue();
    first = false;
    const response = await route.fetch(); captured.resolve(); await release.promise;
    await route.fulfill({ response });
  });
  await page.goto(origin); await captured.promise;
  await page.locator('#password').fill(password); await page.locator('#login-form button').click();
  await page.waitForFunction(() => profile !== null && !checking);
  release.resolve();
  await page.waitForFunction(() => window.sessionReads === 2);
  assert.equal(await page.locator('#reader').isVisible(), true);
  assert.ok(await page.evaluate(() => csrf !== null && profile !== null));
});

test('actual browser Back after server logout cannot restore private cards', async t => {
  const historyBrowser = await chromium.launch({ headless: true, ignoreDefaultArgs: ['--disable-back-forward-cache'] });
  t.after(() => historyBrowser.close());
  const context = await historyBrowser.newContext();
  const page = await context.newPage();
  await page.goto(origin); await page.locator('#password').fill(password);
  await page.locator('#login-form button').click();
  await page.waitForFunction(() => profile !== null && !checking);
  const token = (await (await context.request.get(origin + '/api/session')).json()).csrf;
  await page.goto(origin + '/style.css');
  assert.equal((await context.request.post(origin + '/api/logout', { data: {}, headers: { Origin: origin, 'X-CSRF-Token': token } })).status(), 200);
  await page.goBack();
  await page.locator('#login-panel').waitFor({ state: 'visible' });
  await page.waitForFunction(() => document.getElementById('message').textContent.includes('Sign in'));
  await checkCleared(page);
  assert.equal((await context.request.get(origin + '/api/deals')).status(), 401);
  // Actual history navigation, without asserting that Chromium selected BFCache.
});

test('foreground handling preserves an unsaved Manage edit without fetching', async t => {
  const { page } = await pageFor(t);
  await page.locator('#settings-tab').click();
  await page.locator('#profile-name').fill('SYNTHETIC unsaved edit');
  let requests = 0;
  const count = request => { if (request.url().includes('/api/')) requests++; };
  page.on('request', count);
  await page.evaluate(() => document.dispatchEvent(new Event('visibilitychange')));
  await page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))));
  assert.equal(await page.locator('#profile-name').inputValue(), 'SYNTHETIC unsaved edit');
  assert.equal(requests, 0);
});
