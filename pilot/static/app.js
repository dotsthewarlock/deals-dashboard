'use strict';
let csrf = null, profile = null, checking = false;
const $ = id => document.getElementById(id);
const node = (tag, text, cls) => { const n = document.createElement(tag); n.textContent = text; if (cls) n.className = cls; return n; };
function message(text, error = false) { $('message').textContent = text; $('message').className = error ? 'error' : ''; }
function forget() {
  csrf = null; profile = null;
  $('articles').replaceChildren(); $('sources').replaceChildren(); $('profile-heading').textContent = 'Your articles';
  $('profile-form').reset(); $('mode').textContent = ''; $('password').value = '';
  $('reader').hidden = true; $('login-panel').hidden = false;
}
async function api(path, method = 'GET', data, extra = {}) {
  const headers = { ...extra };
  if (data !== undefined) headers['Content-Type'] = 'application/json';
  if (csrf) headers['X-CSRF-Token'] = csrf;
  const response = await fetch('/api/' + path, { method, credentials: 'same-origin', cache: 'no-store', headers, body: data === undefined ? undefined : JSON.stringify(data) });
  const value = await response.json();
  if (!response.ok) { if (response.status === 401) forget(); throw new Error(value.error || 'Request failed'); }
  return value;
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
  const [p, data, sources] = await Promise.all([api('profile'), api('deals'), api('sources')]);
  profile = p; fillProfile();
  $('mode').textContent = data.mode === 'synthetic' ? 'SYNTHETIC FIXTURE MODE — invented articles. No real feed requests or price claims.' : 'LIVE MODE BLOCKED — recurring retrieval and persistent live caching are not permitted by the current policy.';
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
  checking = true; $('refresh').disabled = true;
  try {
    message('Checking eligible sources…');
    const result = await api('refresh', 'POST', { trigger }, { 'Idempotency-Key': crypto.randomUUID() });
    await cached(); message('Update result: ' + result.outcome + '. Source status is shown below.', result.outcome === 'failed' || result.outcome === 'partial');
  } catch (error) { message(error.message, true); }
  finally { checking = false; $('refresh').disabled = false; }
}
async function enter() {
  const session = await api('session'); csrf = session.csrf;
  $('login-panel').hidden = true; $('reader').hidden = false;
  await cached(); message('Cached articles loaded.');
  if (profile.refreshPreference === 'foreground') await refresh('open');
}
$('login-form').addEventListener('submit', async event => {
  event.preventDefault(); const password = $('password').value; $('password').value = '';
  try { const session = await api('login', 'POST', { password }); csrf = session.csrf; await enter(); }
  catch (error) { message(error.message, true); }
});
$('logout').addEventListener('click', async () => {
  try { await api('logout', 'POST', {}); message('Signed out; private view cleared.'); }
  catch { message('Private view cleared; server sign-out could not be confirmed.', true); }
  finally { forget(); }
});
for (const [tab, panel] of [['deals', 'deals'], ['settings', 'settings']]) {
  $(tab + '-tab').addEventListener('click', () => {
    for (const name of ['deals', 'settings']) { $(name + '-panel').hidden = name !== panel; $(name + '-tab').setAttribute('aria-pressed', String(name === panel)); }
  });
}
$('refresh').addEventListener('click', () => refresh('manual'));
$('profile-form').addEventListener('submit', async event => {
  event.preventDefault();
  const lines = id => $(id).value.split('\n').map(v => v.trim()).filter(Boolean);
  const markets = ['CA', 'US'].filter(m => $('market-' + m.toLowerCase()).checked);
  const sources = ['ca', 'us'].filter(m => $('source-' + m).checked).map(m => 'brickset-' + m);
  try {
    profile = await api('profile', 'PATCH', { ...profile, name: $('profile-name').value, markets, sources, include: lines('include'), exclude: lines('exclude'), lookbackDays: Number($('lookback').value), refreshPreference: $('preference').value });
    await cached(); message('Profile saved; cached articles rematched.');
  } catch (error) { message(error.message, true); }
});
document.addEventListener('visibilitychange', async () => {
  if (document.visibilityState !== 'visible' || !profile || !$('settings-panel').hidden) return;
  try { await cached(); if (profile.refreshPreference === 'foreground') await refresh('foreground'); }
  catch (error) { message(error.message, true); }
});
enter().catch(() => { forget(); message('Sign in to view your private reader.'); });
window.addEventListener('pagehide', forget);
window.addEventListener('pageshow', event => {
  if (event.persisted) enter().catch(() => { forget(); message('Sign in to view your private reader.'); });
});
