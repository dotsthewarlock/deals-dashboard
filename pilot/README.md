# V0.1 local private reader

Local development implementation of the pinned [scope and sequence](../docs/V0.1_SCOPE.md).
**Development review: HOLD**, with browser and live release requirements outstanding.
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
real URL in public reports. The forwarded browser connection and cookie behavior
remain untested here; see the browser checklist below. This is not a production
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

Live recurring retrieval and live persistence are **disabled in policy**. To
inspect the denied state in a separate NEW local database, use the same real
owner setup with a new private path:

```sh
python3 -m pilot.app init --data .local/blocked.sqlite3 --mode live-blocked
python3 -m pilot.app serve --data .local/blocked.sqlite3 --port 8766
```

That mode denies before DNS, worker creation or an injected fetcher. It cannot
persist real metadata. There is no live-enable flag, arbitrary URL field or
Slickdeals adapter. Existing database modes cannot be changed implicitly. Do not
edit permission constants or erase the old compatibility ledger just to get a
live check. The legacy request budget remains intact; V0.1 uses an independent
transactional coordinator and currently has no approved live request budget.

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
either suite; compatibility's generic live test remains explicitly skipped.
No test password, cookie or profile is an actual owner credential. No test
session is left running after the suite.

## Cache, security, backup and browser review

See [architecture and contracts](../docs/V0.1_ARCHITECTURE.md) for source schema,
lease fencing, limits, retention and stack comparison; [operations](../docs/V0.1_OPERATIONS.md)
for backup/rollback/migration and the proposed private deployment gate.

The manifest and responsive shell are present. No service worker stores private
data; offline viewing is deferred to V0.2. PWA installation, visual usability and
physical Chromebook/Android behavior have not been established by HTML or HTTP
tests. Browser validation is a **release requirement**, not a waived acceptance.

When a browser is available, sign in through the Private preview at approximately
1280×800 and mobile emulation 390×844. Record browser/version, viewport and actual
horizontal overflow measurements, label readability, focus/tap targets, source
links and fixture/aggregate/unknown/fresh/stale/empty/failure labels. Verify profile
save/rematch, manual preference, foreground behavior, logout clearing and that
anonymous API access fails. Do not use a checkbox attestation alone. A live-card
browser/repeat retrieval session needs separately established source rights and
budget; no new feed requests are necessary to test synthetic layout.
