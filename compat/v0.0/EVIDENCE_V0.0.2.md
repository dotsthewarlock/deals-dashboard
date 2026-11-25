# V0.0.2 browser smoke preparation — 2026-11-25 UTC

**Decision: HOLD. Original two-family gates: 2/5 Pass. Scoped Brickset-only
reader gates: 4/5 Pass. No desktop/mobile rendering pass has been established.**

This task prepared a temporary private fixture preview for owner-assisted browser
validation. It did not expand the prototype or implement V0.1. Reviewed
[EVIDENCE_V0.0.1.md](./EVIDENCE_V0.0.1.md) and [README.md](./README.md). Prior
reports remain unchanged. No live retrieval occurred during V0.0.2.

## Preflight and preservation

At 2026-11-25T07:35–07:36Z:

- Workspace: `/workspaces/deals-dashboard`.
- Branch: `compat/v0.0-feed-compatibility`.
- HEAD: `986d80bb3b43bf1bcbf45837dae133f19f7c8b9c`.
- Eleven existing untracked files, matching the prior task's ending status; no
  tracked changes. `find .. -name AGENTS.md -print` found none.
- The initial approved loopback request found no listener on port 8765
  (`curl` exit 7, status 000). No existing server was killed or replaced.
- Before-start SHA-256 manifest captured all existing prototype Python/Markdown,
  fixtures, ignore rules and the original task. These are preserved.
- No app-source, fixture, test, README or policy edit. The only new shareable
  deliverable is this report. A disposable smoke harness and evidence metadata
  are under the existing gitignored runtime directory.

## Preview prepared and private visibility verified

Started **2026-11-25T07:36:25.982871+00:00**. Automatic stop deadline:
**2026-11-25T08:06:25.982867+00:00**.

```sh
python3 compat/v0.0/runtime/v002_fixture_preview.py --seconds 1800
```

The temporary harness reuses the existing parser, Cache, handler and renderer.
It binds only `127.0.0.1:8765`, before creating its own disposable fixture store.
It seeds five existing synthetic records (US 2, CA 2, Slickdeals fixture 1) and
supplies fresh, stale, empty and failure fixture states to the unchanged renderer.
The extra empty/failure sections are synthetic UI test states, not new sources,
adapters, app features or real endpoint failures. No source requests, polling,
external images, source-policy changes, browser installs or new dependencies.

At 07:37Z, the read-only GitHub CLI query returned exactly:

```json
[{"sourcePort":8765,"visibility":"private"}]
```

Only port number and visibility were requested; no private preview URL or other
ports are recorded here. The sandbox query initially failed to connect to
`api.github.com`; narrow approved execution succeeded. **Visibility was read,
not changed.** No public port, deployment or account configuration change.
The private forwarded URL opening successfully in a browser remains unverified.

The fixture-only server is left available for the requested owner check until the
deadline. It automatically closes the listener and removes its owned temporary
fixture directory on normal timeout, Ctrl+C or SIGTERM. Existing runtime stores
and the V0.0.1 request ledger are untouched. Hard termination can leave an orphan
fixture directory; no crash-proof cleanup service is claimed.

## Actual observations versus browser evidence

Actual HTTP assertions at **2026-11-25T07:36:57.586004+00:00** succeeded:

```text
HTTP: 200
Fixture cards: 5
Live cards: 0
Fixture states present: fresh, stale, empty, failure
US / CA and unverified labels: present
Explicit empty / retrieval-failed labels: present
Synthetic HTTP 503 label: present (no real 503 request)
Scripts / images: absent
Cache-Control: no-store
CSP: default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; frame-ancestors 'none'; form-action 'none'
```

These assertions examine returned HTML, not a browser DOM or visual layout.
Viewport metadata, responsive CSS and HTTP 200 are **not** rendering evidence.

| Browser requirement | Actual evidence in V0.0.2 | Result |
|---|---|---|
| Private Codespaces port | GitHub API reports port 8765 visibility private | Pass for visibility only |
| Authenticated forwarded page opens | Owner observation requested; no result received at report creation | Not tested |
| Desktop rendering | No usable browser tool/binary and no owner result | Not tested |
| Approximately 390px mobile rendering | Same; no viewport screenshot or DOM measurements | Not tested |
| No horizontal overflow | No browser scrollWidth/clientWidth or visual observation | Not tested |
| Readable labels and usable link targets | HTML contains labels; no visual/touch result | Not tested |
| Original destinations / safe browser behavior | Existing fixture links in HTML; browser interaction not performed | Not tested |
| Fresh/stale/empty/failure state rendering | HTTP text assertions only | Partial; visual result not tested |
| Real-card browser rendering | No new live fetch; old temporary live cache was already removed | Not tested |
| Physical Android/iOS behavior | No physical-device observation | Not tested |

Environment checks: no exposed browser/desktop tools; `command -v chromium
chromium-browser google-chrome firefox playwright` found none; Python Playwright
package unavailable. Cloud desktop runtime/plugin marker checks returned missing
files. Cloud-desktop and runtime/service-preview skills were consulted. No browser
or dependency was installed, and no unavailable browser capability was simulated.
An asynchronous request asked the owner for browser name and desktop/390px
observations. No observation, screenshot or browser result is inferred from HTTP
access logs. Owner-reported evidence should be labeled as such when received.

## Private preview instructions

During the session ending at **08:06 UTC**:

1. In this Codespace, open VS Code's **Ports** panel and find or forward port
   **8765**. Confirm **Port Visibility: Private** before opening it. Do not choose
   Public or Organization visibility.
2. Choose **Open in Browser**, signed in to the owning GitHub account. Use the URL
   supplied by Codespaces; no guessed URL is required. Cloud-local loopback is not
   a browser-accessible address on the owner's separate computer/phone.
3. First test a desktop browser window, approximately **1280×800** at 100% zoom.
4. Open browser developer tools, enable device emulation and set **390×844**.
   Record browser/version and dimensions. This is mobile emulation, not a physical
   Android test. An actual phone can use the same Private Codespaces link while
   signed in; record it separately if performed.
5. Complete the checklist below and report actual pass/fail observations. Do not
   navigate to source/merchant pages to verify prices or trigger source requests.

If the session has expired, restart the same fixture harness from the repository
root using the command above, or use the existing README's `demo` / `serve`
commands for the default fixture view. The harness is disposable and ignored;
the default CLI remains the reproducible prototype entry point. Do not run a
second listener on the same port. If private forwarding fails, preserve Private
visibility and report the error; do not expose a public workaround.

To stop before the deadline, use Ctrl+C in its hosting terminal. For the managed
background process, inspect only the exact command/PID using:

```sh
pgrep -af '^python3 compat/v0.0/runtime/v002_fixture_preview.py --seconds 1800$'
```

Then send SIGTERM to that specific verified PID (`kill -TERM <PID>`). Do not stop
unrelated Python processes or system services. No broad kill command is needed.

## Desktop and mobile checklist

Record Pass/Fail/Not tested for each, for both desktop and 390px:

- The private page opens and shows the V0.0 compatibility heading and HOLD state.
- Five cards are clearly labeled **SYNTHETIC FIXTURE**; no LIVE SOURCE card appears.
- US and CA remain distinguishable; Slickdeals is visibly blocked for live use.
- Source, market, title, publication/observation timestamps, unverified status,
  unknown availability/price/expiry and freshness text remain readable.
- No horizontal page scrolling, clipped long links or overlapping labels. If using
  DevTools, record whether `document.documentElement.scrollWidth <= window.innerWidth`.
- Links can be focused with Tab and have usable click/tap targets. Inspect their
  destinations without following them; synthetic example URLs must remain fixtures.
- Fresh and stale states differ clearly. The deliberately stale CA fixture is
  not presented as current stock/price verification.
- The SYNTHETIC empty-state section clearly reports no records. The SYNTHETIC
  failure-state section shows its simulated 503 and stale/unknown/never-success
  status without presenting it as a real source failure.
- No script/image payload renders or external source request occurs. No unexpected
  console error; record any observed error rather than treating console availability
  or an HTTP log as a completed browser check.

Owner result template:

```text
Checked UTC:
Browser/version, OS/device:
Private forwarded page opened: Pass / Fail
Desktop dimensions and checklist result:
390px dimensions and checklist result:
Horizontal overflow:
Labels, links and targets:
Fixture/live distinction and state/error visibility:
Console errors (if checked):
Real cards checked: No / Yes (identify separately authorized session)
Evidence source: owner observation / automated browser / screenshot
```

## Live retrieval and remaining permission limits

**V0.0.2 source GETs: zero.** The browser is not ready/verified in this execution,
so no live refresh is justified. The existing one-request-per-market V0.0.1 ledger
was not reset or bypassed. Its earlier US/CA results are prior evidence, not new
browser evidence or a new permission review. No need to retrieve feeds merely
to render fixtures, manufacture a failure, or wait for a browser.

The prior scoped interpretation supports ordinary private Brickset RSS consumption
with bounded minimal metadata, source attribution and intact links; it does not
establish permanent retention, long-term price history, public redistribution or
an unrestricted app license. TTL does not grant rights. Slickdeals remains disabled:
its automated-access/external-display permission is unresolved. No provider contact,
paid API, merchant request or source-policy expansion occurred.

Once actual browser readiness is confirmed, any justified follow-up must respect
the published source policy, appropriate request interval and remaining authorized
budget. The current reader CLI deliberately refuses a second initial request;
do not delete its ledger or disable guards. Resolve a narrow follow-up plan before
retrieval. Real metadata must stay in a separate temporary private session; no raw
archives, live screenshots containing unnecessary payloads, private preview links,
credentials or personal data should enter shareable artifacts. Browser readiness
alone does not remove permission/budget limits.

## Updated acceptance matrices

Grades carried forward where this browser-only task did not re-exercise the
underlying requirement. Prior evidence is identified explicitly; no fixture result
is credited as a live-source or browser-rendering pass.

| Original two-family R2 gate | Entering V0.0.1 | V0.0.2 | Evidence / remaining gap |
|---|---|---|---|
| F1 exact endpoints and permission scope | Partial | Partial | Prior Brickset scoped reader evidence; Slickdeals and broader rights unresolved. No source re-review in this task. |
| F2 representative records, both families | Partial | Partial | Prior ten real US + ten CA article samples; no Slickdeals live records, no new samples. |
| F3 real and synthetic safe normalization | Pass | Pass (prior evidence) | Prior live metadata assertions and 49 passing tests; existing renderer/parser reused unchanged. |
| F4 live cache/reload and refresh behavior | Pass | Pass (prior evidence) | Prior temporary real cache reload + synthetic cache tests; this task leaves cache/ledger unchanged. |
| F5 runtime and actual mobile-compatible browser view | Partial | Partial | Current fixture HTTP/private visibility checks pass; actual desktop/mobile/real-card rendering not tested. |

**Original R2: 2/5 Pass → HOLD.**

| Scoped Brickset-only reader gate | CA / US basis | V0.0.2 grade |
|---|---|---|
| F1 | Prior official indexed feeds and limited temporary reader interpretation for each market | Pass (prior, scoped) |
| F2 | Prior ten representative real articles per market | Pass (prior) |
| F3 | Prior independent source/market/URL-identity/unknown-field assertions | Pass (prior) |
| F4 | Prior real temporary disk reload for each market + simulated cache behaviors | Pass (prior) |
| F5 | Current fixture preview/private-port readiness; no actual desktop/mobile or real-card browser evidence | Partial |

**Scoped Brickset-only: 4/5 Pass → HOLD.** No implicit reduced-source pilot
approval, original gate revision, publication or V0.1 implementation.

Smallest next action: owner opens the already prepared Private fixture preview
and returns the desktop/390px observations. Record those as owner-reported evidence.
If those checks pass, arrange the smallest permitted real-card browser session
with the request budget intact before reassessing F5. Missing browser evidence is
not a reason to fetch first or weaken a permission guard.

## Commands and validation scope

Relevant exact commands from `/workspaces/deals-dashboard`:

```sh
git status --short --untracked-files=all
git branch --show-current
git rev-parse HEAD
find .. -name AGENTS.md -print
cat compat/v0.0/README.md
cat compat/v0.0/EVIDENCE_V0.0.1.md
command -v chromium chromium-browser google-chrome firefox playwright
ls -Ld /usr/local/bin/cloud-agent-browser-runtime /opt/codex/marketplaces/openai-bundled/plugins/unified-computer-use/.codex-plugin/plugin.json
python3 -c "import importlib.util; print('Playwright package available:',bool(importlib.util.find_spec('playwright')))"
find .vscode compat/v0.0 -maxdepth 2 -name tasks.json -print
curl --max-time 5 --silent --show-error --output /dev/null --write-out 'preview_status=%{http_code}\n' http://127.0.0.1:8765/
sha256sum CODEX_V0.0_FEED_COMPATIBILITY.md compat/v0.0/*.py compat/v0.0/*.md compat/v0.0/.gitignore compat/v0.0/fixtures/*.xml > compat/v0.0/runtime/v002-before.sha256
python3 compat/v0.0/runtime/v002_fixture_preview.py --seconds 1800
gh codespace ports --help
gh codespace ports --codespace "$CODESPACE_NAME" --json sourcePort,visibility --jq 'map(select(.sourcePort == 8765))'
git check-ignore compat/v0.0/runtime/v002_fixture_preview.py compat/v0.0/runtime/v002-before.sha256
date -u +%FT%TZ
```

The HTTP assertion script used Python http.client against loopback, examining
HTML only in memory and saving redacted assertion results under ignored runtime.
No app change justified rerunning the full regression suite in this browser-only
task; **49 pass / 1 skip is the recorded V0.0.1 result, not a new V0.0.2 run**.
No new screenshots, DOM measurements, browser runs or physical-device results.
Final preservation/whitespace/Git checks are recorded below.

### Final checks at 2026-11-25T07:38:54Z

`sha256sum -c compat/v0.0/runtime/v002-before.sha256`: **all 11 existing files OK**,
including both prior evidence reports, source/tests, README, original task,
fixtures and ignore rules. `git diff --check` produced no diagnostics. The
untracked report's `git diff --no-index --check /dev/null` produced no whitespace
diagnostics (difference exit 1 is expected for a new file).

New ignored runtime script and HTTP-check metadata match existing ignore rules.
The only additional shareable/untracked file is `compat/v0.0/EVIDENCE_V0.0.2.md`.
Branch/HEAD remain as recorded above; all previous uncommitted work is preserved.
No staging, commit, push, merge, deployment, public forwarding, live fetch or V0.1.

At report completion, no owner browser result has arrived. Desktop/mobile results
remain **Not tested**, with the fixture preview available until **08:06 UTC**.
Proceed no further than this HOLD decision without actual browser observations
and any narrow live-follow-up prerequisites being satisfied.
