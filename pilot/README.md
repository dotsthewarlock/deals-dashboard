# V0.1 local private reader

Local development implementation of the pinned [scope and sequence](../docs/V0.1_SCOPE.md).
**V0.1 historical review: HOLD.** See the [current V0.1.1 evidence](../docs/V0.1.1_EVIDENCE.md) and [operational handoff](../docs/V0.1.1_OPERATIONS.md) for subsequent results and remaining release requirements.
Read [actual evidence](../docs/V0.1_EVIDENCE.md) before interpreting test success.

Python **3.11+**, standard library only; one backend and one SQLite database. No
package install, external account, hosting service, paid API or cloud setup. The
compatibility prototype remains unchanged under [compat/v0.0](../compat/v0.0/).

## Setup in the existing Codespace

From the repository root, initialize a real local owner password interactively:

```sh
python3 -m pilot.app init
python3 -m pilot.app serve --port 8766
```

Choose a unique password of at least 14 characters at the hidden terminal prompt.
No default owner password or bypass exists. Do not supply credentials in chat,
command arguments, source files or public evidence. Initialization creates only a
local application owner, not a GitHub/Cloudflare/other external account. Repeating
init cannot overwrite an existing owner. Owner initialization is left to the
operator; no actual owner password was created during development tests.

The default private state location is `.local/pilot.sqlite3`, ignored with its
sidecars. Keep it private. The process binds **127.0.0.1 only**, with default
browser origin `http://127.0.0.1:8766`. Port 8765 and its existing compatibility
preview are deliberately not disturbed. Stop with Ctrl+C. No server is installed
as a service and no polling/schedule exists.

For a Codespaces browser, locate/forward **8766** in **Ports**, verify **Visibility:
Private**, and copy its HTTPS origin locally. Restart the app with its exact
origin (no trailing slash):

```sh
python3 -m pilot.app serve --port 8766 --origin 'https://PRIVATE-ORIGIN-PROVIDED-BY-CODESPACES'
```

That is a placeholder, not a published preview URL. The exact origin controls
CSRF checks and Secure cookies. Do not change visibility to public or record the
real URL in public reports. Actual owner Codespaces forwarding remains untested; local TLS Secure-cookie
behavior is now verified by Chromium, as recorded in current evidence; see the browser checklist below. This is not a production
deployment. HTTPS termination, hosting, external owner auth integration if chosen,
device tests and persistent live rights need the separate release gate.

Sign in, open Articles and Manage, edit the one profile and save. Cached articles
are requested first. In foreground mode, an eligible check follows opening or
returning to the visible Articles view. Manage editing is not overwritten by an
automatic foreground reload. Manual mode checks only on the update button.
Include terms match **any**, exclude terms reject **any**, by literal Unicode
casefolded substring in article titles. Lookback is 1–90 days; unknown publication
dates remain visible with unknown dates. Disabled markets/sources do not match or
fetch. Profile edits rematch existing cache without fetching.

## Synthetic mode and live boundary

Default `synthetic` mode generates two explicitly invented article fixtures, one
per market. Their links use clearly synthetic article paths on Brickset's origin;
they are not actual reported offers and need not resolve. Do not navigate to
merchants to test them. Rewards, prices, stock, seller, expiry and individual set
qualification are not inferred. Cards are aggregate articles; optional money,
merchant/product and promotion fields remain null.

V0.1.1 adds opt-in `live` mode for the [bounded private RSS reader policy](../docs/V0.1.1_SOURCE_POLICY.md).
The current Brickset RSS invitation supports a narrow reader interpretation,
not a blanket data licence. Use a new private database, not the synthetic store:

```sh
python3 -m pilot.app init --data .local/private-reader.sqlite3 --mode live
python3 -m pilot.app serve --data .local/private-reader.sqlite3 --port 8766
```

At least 30 minutes between checks, at most eight attempts/source/rolling day,
two-hour logical metadata retention, no live backup/history/full text. Failures
and manual requests count toward the same enforced budget. No owner was set up
by development; these remain private interactive operator steps. The explicit
`live-blocked` mode remains available and never sends requests. Existing database
modes never silently change; no arbitrary URL or Slickdeals adapter exists.

## Tests

```sh
python3 -m unittest discover -s tests -v
python3 -m unittest discover -s compat/v0.0 -v
python3 -m py_compile pilot/*.py tests/*.py
node --check pilot/static/app.js
```

Node is optional and used only for a JavaScript syntax check, not the backend or
runtime. Tests use disposable SQLite stores, actual local password verification,
real HTTP requests on ephemeral loopback ports, and synthetic XML. A synthetic
sleeping child process tests cancellation. No live provider request is made by
either automated Python suite; compatibility's generic live test remains explicitly skipped.
No test password, cookie or profile is an actual owner credential. No test
session is left running after the suite.

## Cache, security, backup and browser review

See [architecture and contracts](../docs/V0.1_ARCHITECTURE.md) for source schema,
lease fencing, limits, retention and stack comparison; [operations](../docs/V0.1_OPERATIONS.md)
for backup/rollback/migration and the proposed private deployment gate.

The manifest and responsive shell are present. No service worker stores private
data; offline viewing is deferred to V0.2. Desktop/mobile-width visual layout is verified in Chromium. PWA installation and
physical Chromebook/Android behavior remain unverified; headless viewport tests
do not establish physical-device acceptance. Browser validation is a **release requirement**, not a waived acceptance.

For the remaining owner session, sign in through the Private preview at approximately
1280×800 and mobile emulation 390×844. Record browser/version, viewport and actual
horizontal overflow measurements, label readability, focus/tap targets, source
links and fixture/aggregate/unknown/fresh/stale/empty/failure labels. Verify profile
save/rematch, manual preference, foreground behavior, logout clearing and that
anonymous API access fails. Do not use a checkbox attestation alone. A live-card
browser/repeat retrieval session needs separately established source rights and
budget; no new feed requests are necessary to test synthetic layout.

## Browser race regressions

The optional browser suite uses Playwright/Chromium as **test tooling only** and
a disposable synthetic server. It never initializes a real owner or fetches a
provider. If browser tooling is not installed, the Python application/tests still
have no package dependency. In this execution tools and downloaded shared
libraries were isolated under ignored `.local/browser-tools/` and removed after validation. To rerun, supply Playwright/Chromium and their platform libraries first; the path example below describes that isolated setup, not an application dependency. See the exact
commands/results in [current evidence](../docs/V0.1.1_EVIDENCE.md).

```sh
NODE_PATH="$PWD/.local/browser-tools/node_modules" \
PLAYWRIGHT_BROWSERS_PATH="$PWD/.local/browser-tools/browsers" \
LD_LIBRARY_PATH="$PWD/.local/browser-tools/sysroot/usr/lib/x86_64-linux-gnu" \
node --test tests/browser_readiness.cjs
```

Logout clears the private view immediately, invalidates/aborts stale requests,
and waits for any pending login cookie before revocation. Failed server logout
shows a retry action; it is not falsely confirmed. Cache loads render only the
latest request generation. Browser automation does not replace the
[single owner device/HTTPS session](../docs/V0.1.1_OPERATIONS.md).
