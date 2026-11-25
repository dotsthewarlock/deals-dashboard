'use strict';
let csrf = null, profile = null, checking = false;
let epoch = 0, loadSequence = 0, loggingOut = false, loginRequest = null;
const requests = new Set();
const stale = () => new DOMException('Superseded request', 'AbortError');
const current = generation => generation === epoch;
function report(error, generation) {
  if (current(generation) && error.name !== 'AbortError') message(error.message, true);
}
const $ = id => document.getElementById(id);
const node = (tag, text, cls) => { const n = document.createElement(tag); n.textContent = text; if (cls) n.className = cls; return n; };
function message(text, error = false) { $('message').textContent = text; $('message').className = error ? 'error' : ''; }
function forget() {
  epoch++; loadSequence++;
  for (const controller of requests) controller.abort();
  requests.clear(); checking = false; $('refresh').disabled = false;
  $('logout-retry').hidden = true;
  csrf = null; profile = null;
  $('articles').replaceChildren(); $('sources').replaceChildren(); $('profile-heading').textContent = 'Your articles';
  $('profile-form').reset(); $('mode').textContent = ''; $('password').value = '';
  $('reader').hidden = true; $('login-panel').hidden = false;
}
async function api(path, method = 'GET', data, extra = {}, options = {}) {
  const generation = epoch, controller = new AbortController();
  const auth = path === 'login' || path === 'logout';
  if (!auth) requests.add(controller);
  const headers = { ...extra };
  if (data !== undefined) headers['Content-Type'] = 'application/json';
  const token = options.csrf === undefined ? csrf : options.csrf;
  if (token) headers['X-CSRF-Token'] = token;
  try {
    const response = await fetch('/api/' + path, { method, credentials: 'same-origin', cache: 'no-store', headers,
      signal: controller.signal, body: data === undefined ? undefined : JSON.stringify(data) });
    const value = await response.json();
    if (!auth && !current(generation)) throw stale();
    if (!response.ok) {
      if (response.status === 401 && !auth && !loggingOut && current(generation)) {
        forget(); message('Sign in to view your private reader.');
      }
      throw Object.assign(new Error(value.error || 'Request failed'), { status: response.status });
    }
    return value;
  } finally { requests.delete(controller); }
}
function fillProfile() {
  $('profile-name').value = profile.name;
  for (const market of ['CA', 'US']) {
    const suffix = market.toLowerCase();
    $('market-' + suffix).checked = profile.markets.includes(market);
    $('source-' + suffix).checked = profile.sources.includes('brickset-' + suffix);
  }
  $('include').value = profile.include.join('\n'); $('exclude').value = profile.exclude.join('\n');
  $('lookback').value = profile.lookbackDays; $('preference').value = profile.refreshPreference;
  $('profile-heading').textContent = profile.name;
}
async function cached() {
  const generation = epoch, sequence = ++loadSequence;
  const [p, data, sources] = await Promise.all([api('profile'), api('deals'), api('sources')]);
  if (!current(generation) || sequence !== loadSequence) throw stale();
  profile = p; fillProfile();
  $('mode').textContent = data.mode === 'synthetic' ? 'SYNTHETIC FIXTURE MODE — invented articles. No real feed requests or price claims.' : data.mode === 'live' ? 'PRIVATE RSS READER — reported aggregate articles. Temporary metadata cache; no independent price verification.' : 'LIVE MODE BLOCKED — no feed requests permitted for this store.';
  $('articles').replaceChildren();
  for (const row of data.articles) {
    const card = node('article', '');
    card.append(node('span', row.provenance.synthetic ? 'SYNTHETIC FIXTURE · AGGREGATE ARTICLE' : 'REPORTED · AGGREGATE ARTICLE', 'badge'));
    card.append(node('h3', row.title));
    card.append(node('p', 'Brickset · ' + row.market + ' · ' + row.verification + ' · Availability unknown', 'meta'));
    card.append(node('p', 'Published: ' + (row.publishedAt || 'unknown') + '\nObserved: ' + row.observedAt, 'meta'));
    card.append(node('p', 'Price, seller, discount and offer expiry unknown. Cache valid until ' + row.cacheExpiresAt, 'meta'));
    const link = node('a', 'Read original article'); link.href = row.canonicalUrl; link.rel = 'noopener noreferrer';
    card.append(link); $('articles').append(card);
  }
  if (!data.articles.length) $('articles').append(node('p', 'No retained articles match this profile. Check source status for empty, failed or expired data.'));
  $('sources').replaceChildren();
  for (const s of sources.sources) {
    const box = node('section', '', 'source');
    box.append(node('h3', 'Brickset · ' + s.market));
    box.append(node('p', s.enabled ? 'Enabled for this profile' : 'Disabled for this profile', 'meta'));
    box.append(node('p', s.freshness + ' · ' + s.outcome + ' · ' + s.count + ' retained', 'meta'));
    if (s.error) box.append(node('p', 'Check failed: ' + s.error, 'error'));
    box.append(node('p', 'Last success: ' + (s.lastSuccessAt || 'never') + '\nLast attempt: ' + (s.lastAttemptAt || 'never'), 'meta'));
    box.append(node('p', 'Next eligible: ' + (s.nextEligibleAt || 'now'), 'meta'));
    $('sources').append(box);
  }
}
async function refresh(trigger) {
  if (checking || !profile) return;
  const generation = epoch;
  checking = true; $('refresh').disabled = true;
  try {
    message('Checking eligible sources…');
    const result = await api('refresh', 'POST', { trigger }, { 'Idempotency-Key': crypto.randomUUID() });
    if (!current(generation)) throw stale();
    await cached(); message('Update result: ' + result.outcome + '. Source status is shown below.', result.outcome === 'failed' || result.outcome === 'partial');
  } catch (error) { report(error, generation); }
  finally { if (current(generation)) { checking = false; $('refresh').disabled = false; } }
}
async function enter() {
  const generation = epoch;
  const session = await api('session');
  if (!current(generation) || loggingOut) throw stale();
  csrf = session.csrf;
  $('login-panel').hidden = true; $('reader').hidden = false;
  await cached(); message('Cached articles loaded.');
  if (profile.refreshPreference === 'foreground') await refresh('open');
}
$('login-form').addEventListener('submit', async event => {
  event.preventDefault();
  if (loggingOut || loginRequest) return;
  const password = $('password').value;
  // Initial/session reads from the previous view must not revoke this new login.
  forget();
  const generation = epoch;
  loginRequest = api('login', 'POST', { password });
  try {
    const session = await loginRequest;
    if (!current(generation) || loggingOut) return;
    csrf = session.csrf; await enter();
  } catch (error) { report(error, generation); }
  finally { loginRequest = null; }
});
async function signOut() {
  if (loggingOut) return;
  loggingOut = true;
  const pendingLogin = loginRequest;
  let token = csrf;
  forget(); const generation = epoch;
  message('Signing out…');
  try {
    // Let login settle: aborting it can still leave a cookie set by the server.
    if (pendingLogin) { try { token = (await pendingLogin).csrf; } catch { /* Try the existing session. */ } }
    if (!token) token = (await api('session')).csrf;
    await api('logout', 'POST', {}, {}, { csrf: token });
    if (current(generation)) message('Signed out; private view cleared.');
  } catch (error) {
    if (current(generation)) {
      if (error.status === 401) message('Signed out; no active server session.');
      else {
        message('Private view cleared; server sign-out could not be confirmed. Retry sign-out before leaving a shared device.', true);
        $('logout-retry').hidden = false;
      }
    }
  }
  finally { loggingOut = false; }
}
$('logout').addEventListener('click', signOut);
$('logout-retry').addEventListener('click', signOut);
for (const [tab, panel] of [['deals', 'deals'], ['settings', 'settings']]) {
  $(tab + '-tab').addEventListener('click', () => {
    for (const name of ['deals', 'settings']) { $(name + '-panel').hidden = name !== panel; $(name + '-tab').setAttribute('aria-pressed', String(name === panel)); }
  });
}
$('refresh').addEventListener('click', () => refresh('manual'));
$('profile-form').addEventListener('submit', async event => {
  event.preventDefault();
  if (!profile || loggingOut) return;
  const generation = epoch;
  const lines = id => $(id).value.split('\n').map(v => v.trim()).filter(Boolean);
  const markets = ['CA', 'US'].filter(m => $('market-' + m.toLowerCase()).checked);
  const sources = ['ca', 'us'].filter(m => $('source-' + m).checked).map(m => 'brickset-' + m);
  try {
    const saved = await api('profile', 'PATCH', { ...profile, name: $('profile-name').value, markets, sources, include: lines('include'), exclude: lines('exclude'), lookbackDays: Number($('lookback').value), refreshPreference: $('preference').value });
    if (!current(generation)) throw stale();
    profile = saved;
    await cached(); message('Profile saved; cached articles rematched.');
  } catch (error) { report(error, generation); }
});
document.addEventListener('visibilitychange', async () => {
  if (document.visibilityState !== 'visible' || !profile || !$('settings-panel').hidden) return;
  const generation = epoch;
  try { await cached(); if (profile.refreshPreference === 'foreground') await refresh('foreground'); }
  catch (error) { report(error, generation); }
});
function openReader() {
  if (loggingOut) return;
  const generation = epoch;
  enter().catch(error => {
    if (error.name !== 'AbortError' && current(generation)) { forget(); message('Sign in to view your private reader.'); }
  });
}
openReader();
window.addEventListener('pagehide', forget);
window.addEventListener('pageshow', event => {
  if (event.persisted) openReader();
});
