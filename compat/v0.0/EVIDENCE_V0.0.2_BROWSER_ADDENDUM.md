# Gate A browser addendum — 2026-11-25

**Decision: HOLD at Gate A. Scoped Brickset ordinary-reader gates: 4/5 Pass
(F1–F4, with qualifications below); F5 Blocked. V0.1 development has not begun.**

This is new dated evidence, not a replacement for [V0.0](./EVIDENCE.md),
[V0.0.1](./EVIDENCE_V0.0.1.md), or [V0.0.2](./EVIDENCE_V0.0.2.md).
Historical original two-family gates remain 2/5 / HOLD. The owner's source-scope
amendment now makes Brickset CA/US the sole initial family for future V0.1 work;
it does not retroactively validate Slickdeals or change historical results.

## Instruction and repository verification

Fetched `origin handoff/v0.1`. The sandbox attempt failed because FETCH_HEAD was
read-only; narrowly approved execution succeeded. Verified:

```text
git rev-parse FETCH_HEAD
46b27ce243b3990238f14f26d03a47ee1f24fc0c

git show --no-patch --format='%H%n%s' FETCH_HEAD
46b27ce243b3990238f14f26d03a47ee1f24fc0c
docs: publish V0.1 Brickset private pilot task
```

Read the authorized task with exactly:

```sh
git show FETCH_HEAD:CODEX_V0.1_BRICKSET_PRIVATE_PILOT.md
```

The controlling amendment remains accessible in that verified Git object. Its
scope: Brickset-only V0.1, article-level private reader, Slickdeals deferred,
local development authorized only after Gate A, no deployment or publication
authorized by this trigger. The instruction is not checked out or merged.

Preflight at approximately **2026-11-25T08:10Z**:

- Remote fetch/push: `https://github.com/dotsthewarlock/deals-dashboard`.
- Current branch: `compat/v0.0-feed-compatibility`.
- HEAD: `cff7570f450504416898e080a07c3e6afc4ed80d`, exactly the pinned reviewed
  implementation. Git object exists and is a commit.
- `git diff cff7570f450504416898e080a07c3e6afc4ed80d -- compat/v0.0` returned no
  differences. Source, tests, fixtures, README, ignore rules and historical
  reports match the previously reviewed pinned content; no prototype edit needed.
- Starting status: only `?? CODEX_V0.0_FEED_COMPATIBILITY.md`. This existing
  untracked task is preserved and was not edited.
- `find .. -name AGENTS.md -print` found no instruction files.
- No PROJECT_RESPONSE_WORKFLOW.md or full R2 Project source set is present in
  this checkout. The verified handoff specifies the relevant reporting rules
  and controlling amendment; external Project documents were not invented or
  silently claimed to be updated. No development branch was created while Gate A
  remains blocked.

## Fresh regression execution

Actual command, approved execution with loopback socket access:

```sh
python3 -m unittest discover -s compat/v0.0 -v > compat/v0.0/runtime/gate-a-tests.txt 2>&1
```

Exit **0**. Actual final output:

```text
Ran 50 tests in 0.604s

OK (skipped=1)
```

**49 passed, 1 skipped, 0 failures/errors.** The general live test is explicitly
skipped: `Live permissions unresolved; no fixture counts as live retrieval`.
Tests exercise synthetic transport/cache/parser behavior and a real loopback
HTTP server. No live feed GET was made. Prior separate live US/CA observations
remain historical evidence, not another independent execution in this turn.

## Browser capability, preview and actual checks

No browser/desktop/environment-status tool is exposed in this session. Executable
discovery for Chromium, Chrome, Firefox and Playwright found none; Python
Playwright detection returned False. The desktop runtime/plugin marker files
were absent. No dependency or browser installation was attempted. Previously
read cloud-desktop/runtime guidance was followed for the owner-assisted fallback.

The previous preview expired at 08:06Z. A narrowly approved curl check returned
connection failure / status 000 before restart; no existing listener was stopped.
Reused the existing ignored fixture smoke harness without editing prototype code:

```sh
python3 compat/v0.0/runtime/v002_fixture_preview.py --seconds 1800
```

Actual start: **2026-11-25T08:11:17.059037+00:00**.
Automatic stop: **2026-11-25T08:41:17.059034+00:00**.
Bind: **127.0.0.1:8765**, five fixture cards plus synthetic fresh/stale/empty/failure
states, zero source GETs. Its own temporary fixture store is removed on normal
shutdown; pre-existing caches and request ledgers are untouched.

Read-only Codespaces visibility query:

```sh
gh codespace ports --codespace "$CODESPACE_NAME" --json sourcePort,visibility --jq 'map(select(.sourcePort == 8765))'
```

The initial query around startup returned `[]`; it did not prove a private
forward existed. One recheck after the server became ready returned:

```json
[{"sourcePort":8765,"visibility":"private"}]
```

No visibility or account configuration was changed. No actual private URL is
stored in this report. This verifies port visibility, not browser authentication
or a successful forwarded page opening.

Actual loopback assertions at **2026-11-25T08:12:04.519857+00:00**:

```json
{"HTTP":200,"fixtures":5,"liveCards":0,"statesPresent":true,"cacheControl":"no-store","browserRendering":"not tested"}
```

Assertions checked US/CA unverified labels, fresh/stale/empty/failure text, no
scripts/images, and fixture/live separation. HTML stayed in memory; no raw/live
payload was saved. HTTP 200 and string assertions do not establish rendered layout.

### Missing actual browser evidence

| Required observation | This execution |
|---|---|
| Authenticated Private Codespaces page opening | Not tested |
| Browser name/version and OS/device/emulation | Not available |
| Desktop 1280×800 rendering and DOM/visual findings | Not tested |
| Mobile emulation 390×844 rendering and DOM/visual findings | Not tested |
| Horizontal overflow, readable labels, usable links | Not tested |
| Visual fixture/live and fresh/stale/empty/failure distinctions | Not tested |
| Source link destinations checked in browser | Not tested |
| Real-card view in a ready browser | Blocked by browser prerequisite |
| Physical Android | Not tested; never inferred from emulation |

An asynchronous owner request provided exact preview/viewport steps and asked
for DOM measurements plus specific observations. No owner result was received
when this addendum was written. A generic assertion of completion or page GET in
an access log is not a browser pass.

## Exact owner action to unblock Gate A

Before **08:41 UTC**, in this Codespace:

1. Open **Ports**, locate/forward **8765**, confirm **Visibility: Private**, and
   choose **Open in Browser** while signed in. Do not make it Public and do not
   share the private URL in public evidence.
2. At approximately **1280×800** and then DevTools mobile emulation **390×844**,
   record browser/version and the actual viewport. In the console, collect:

   ```js
   JSON.stringify({width:innerWidth,height:innerHeight,scrollWidth:document.documentElement.scrollWidth})
   ```

3. Supply those measurements for both sizes, and actual observations of readable
   titles/source/market/freshness, usable links, fixture labels, and visibly distinct
   fresh/stale/empty/failure states. Inspect link destinations without navigating
   to merchants. Note console/layout errors if observed. Sanitized fixture-only
   screenshots can supplement measurements; generic completion attestation alone
   is insufficient.
4. Do not fetch live feeds or reset the old request ledger. After fixture browser
   readiness is demonstrated, the remaining live-card check needs its own narrowly
   scoped, permitted session budget, at most one justified request per market.
   Keep the V0.0.1 ledger intact. No fresh live budget was created in this turn.

If the preview expires, reuse the ignored existing harness command above. The
public reproducible fixture CLI is also documented in [README.md](./README.md),
though it does not create all the temporary smoke states. No duplicate listener
or new coding task is needed. The server stops automatically; Ctrl+C in its
hosting terminal or SIGTERM to its exact verified process stops it sooner.

## Permission review and live boundary

Rechecked official documentation during **08:11–08:12Z**, before any possible
live operation; no feed endpoint or keyed API was invoked:

- [Brickset RSS index](https://brickset.com/article/52663/): still explicitly
  provides personal RSS-reader feeds and distinct CA/US Amazon links.
- [Keeping up to date](https://brickset.com/article/57700/keeping-up-to-date):
  still describes RSS-reader consumption.
- [Robots guidance](https://brickset.com/robots.txt): reviewed; no listed
  disallow matches the CA/US feed paths. This is guidance, not a permission grant.
- [Supplied API terms lead](https://brickset.com/article/52666/api-version-3-documentation-terms-of-use):
  still a separate keyed web-services page. No API call or key requested; API
  rules are not silently substituted for an RSS license.
- [Slickdeals terms](https://corp-site.slickdeals.net/content-list-slickdeals-terms-of-service/):
  documentation reviewed only. No Slickdeals feed/service retrieval by the app.
  Slickdeals remains deferred, not validated.

The limited ordinary personal-reader interpretation remains defensible for
temporary attributed metadata; this is an interpretation of the RSS invitation,
not an express blanket license. Persistent structured-data retention, recurring
retrieval beyond this scoped session, public redistribution and historical pricing
rights are not established. A successful request, Private port or chosen TTL is
not permission. These remain V0.1 release questions even if scoped Gate A later
passes. No new live GETs were made while browser readiness is blocked.

## Scoped Gate A matrix

Only the amended **Brickset CA/US ordinary temporary reader** scope is assessed
here. Prior real observations are identified; no fixture substitutes for them.

| Gate | Grade | Evidence and scope |
|---|---|---|
| F1 | Pass, scoped interpretation | Current RSS invitation/robots/API guidance reviewed. Only temporary personal-reader metadata; persistent production rights unresolved. |
| F2 | Pass, prior evidence | Pinned V0.0.1 records ten inspected real articles per market; no new real samples in this execution. |
| F3 | Pass | New 49-pass regression execution plus prior real source/market/URL-identity/unknown-field assertions. No offer-level price qualification claimed. |
| F4 | Pass, limited temporary persistence | Prior actual temporary real disk reload; new simulated TTL/304/empty/failure/dedupe/lock/backoff tests. No real repeat retrieval or current live 304; no recurring production-cache acceptance. |
| F5 | Blocked | Private fixture preview/HTTP are ready, but no actual authenticated desktop/mobile browser or real-card result. |

**4/5 Pass → Gate A HOLD.** No silent scope relaxation. Original two-family
historical 2/5 and scoped prior 4/5 grades remain dated evidence, not retroactive
production acceptance.

## V0.1 development boundary and ending state

| Development gate | Result |
|---|---|
| D1 Entry | Blocked: Gate A has not passed; conditional development authorization not activated. |
| D2 Core | Not tested / not implemented. |
| D3 Cache/refresh | Not tested / not implemented. |
| D4 Security/runtime | Not tested for V0.1; compatibility results are not owner-app authentication. |
| D5 Handoff | Not tested for V0.1; this is only the Gate A blocker report. |

**V0.1 development: 0/5 Pass, not entered.** No stack selection, feature code,
new development branch, deployment preparation, account setup, paid use,
implementation commit, push or merge. Fetching the authorized handoff is the
only remote Git operation. Existing branches and historical evidence preserved.
This new addendum is the sole new non-ignored file from the Gate A execution.

Relevant exact commands also included:

```sh
git status --short --untracked-files=all
git branch --show-current
git rev-parse HEAD
git remote -v
find .. -name AGENTS.md -print
git fetch origin handoff/v0.1
git cat-file -t cff7570f450504416898e080a07c3e6afc4ed80d
git diff cff7570f450504416898e080a07c3e6afc4ed80d -- compat/v0.0
git ls-tree -r --name-only FETCH_HEAD
command -v chromium chromium-browser google-chrome firefox playwright
ls -Ld /usr/local/bin/cloud-agent-browser-runtime /opt/codex/marketplaces/openai-bundled/plugins/unified-computer-use/.codex-plugin/plugin.json
python3 -c "import importlib.util; print('Playwright available:',bool(importlib.util.find_spec('playwright')))"
curl --max-time 5 --silent --show-error --output /dev/null --write-out 'preview_status=%{http_code}\n' http://127.0.0.1:8765/
tail -n 7 compat/v0.0/runtime/gate-a-tests.txt
git diff --name-only
date -u +%FT%TZ
```

No PROJECT_RESPONSE_WORKFLOW.md was found by local discovery. The handoff's
decision/evidence/limits/Git-state requirements have been followed directly.
Remaining prerequisite is owner-supplied actual browser observations, followed
by the bounded real-card browser check if permitted. Stop here at Gate A.

Final checks at **2026-11-25T08:13:33Z**: tracked `git diff --name-only` is empty;
`git diff --check` and the untracked addendum's no-index whitespace check produced
no diagnostics. Status contains only the preserved original untracked task and
this new untracked addendum. Branch remains `compat/v0.0-feed-compatibility`, HEAD
`cff7570f450504416898e080a07c3e6afc4ed80d`, FETCH_HEAD
`46b27ce243b3990238f14f26d03a47ee1f24fc0c`. The test log is gitignored. No owner
browser result has arrived; the fixture-only preview remains available until
08:41 UTC. No publication or implementation change was made.
