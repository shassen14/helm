---
type: design
status: stable
updated: 2026-05-09
---

# helm — supporting the -ilities

> Concrete mechanism for each quality attribute. If a future change weakens any of these,
> reject it or update this doc deliberately.

---

## Reliability

**Goal:** the daemon stays up across hardware glitches, network blips, and bad config.

| Mechanism | Where |
|---|---|
| Process supervisor (launchd `KeepAlive=true`, systemd `Restart=always`) | `packaging/launchd/`, `packaging/systemd/` |
| HID reconnect loop with exponential backoff (1s → 30s cap) | `helmd/hardware/supervisor.py` |
| HTTP client retries on transient errors only (no retries on 4xx) | `helmd/actions/http.py` |
| Action dispatcher boundary — one bad action never crashes the daemon | `helmd/actions/base.py` (try/except at dispatch) |
| Profile loader rejects invalid TOML, falls back to last-known-good | `helmd/profiles/loader.py` |
| Audio callback never allocates, never calls Python (Rust core) | `mixd/rust/src/engine.rs` |

**What we explicitly don't do:** retry forever on any failure (silent failures hide bugs). Retries are bounded and logged.

---

## Availability

**Goal:** partial failure ≠ unusable system.

| Failure | Behavior |
|---|---|
| No deck connected | Web UI on :7100 still functional |
| Deck unplugged mid-session | Surface goes offline; web UI stays live; auto-reconnect on replug |
| veil down | helm button shows error state, daemon healthy; other buttons unaffected |
| mixd crashed | helmd buttons bound to mixd return errors; supervisor restarts mixd; profile recovers automatically |
| Audio device removed | Channel marked offline in mixd; rest of mix continues |
| Bad profile loaded | Falls back to `default.toml` with logged warning |

Each subsystem degrades independently. No "one error nukes everything."

---

## Portability

**Goal:** same code runs on macOS and Linux. Windows is a future target the design must not preclude.

| OS-specific concern | Abstracted via | Backends |
|---|---|---|
| Active-window detection | `core/platform/__init__.py` | mac: AppKit; linux: xdotool/wnck |
| Keypress injection | same | both via pynput where possible; fallback per-OS |
| Audio device enumeration | `mixd/python/devices.py` | mac: CoreAudio; linux: PipeWire |
| Audio I/O | cpal (Rust) | cross-platform by construction |
| Daemon start | `packaging/` | launchd (mac), systemd (linux), NSSM (windows, future) |
| Filesystem paths | `core/paths.py` | XDG (linux), Application Support (mac) |

**Anti-pattern (forbidden):** `if sys.platform == "darwin"` in business logic. All platform branches live in `core/platform/`.

See `os-support.md` for the full per-OS matrix.

---

## Extensibility

**Goal:** adding an action type, a profile field, or a device model is a focused, low-risk change.

| Extension point | Mechanism |
|---|---|
| New action type | Subclass `Action`, register in `actions/registry.py`. No edits to dispatcher. |
| New profile field | Bump `schema_version`; add migration in `profiles/loader.py`. |
| New deck model | Add entry to `DeckModel` enum + `Surface` factory. python-elgato-streamdeck handles HID. |
| New domain service | Add HTTP action targeting it. helmd is unchanged. |
| New mixer feature | Add HTTP route in `mixd/python/server.py`; Rust core only changes if DSP changes. |

**Schema versioning is non-optional.** Every profile carries `schema_version`. The loader runs migrations forward; unknown versions are rejected loudly.

---

## Maintainability

**Goal:** code stays readable as it grows.

| Rule | Enforcement |
|---|---|
| Files <300 lines | Linter check (line count) in CI |
| No magic strings | All enums in `constants.py`; PR review |
| OOP composition over inheritance | Action types compose, don't inherit each other |
| No daemon imports another daemon's runtime | Linter rule: `helmd/` cannot import `mixd/` and vice versa |
| Configuration externalized | No values hardcoded; all in `helm.toml` or env |

Code style is captured in the user's `feedback_code_style` memory.

---

## Observability

**Goal:** when something breaks, the cause is obvious from logs and `/status`.

| Mechanism | Detail |
|---|---|
| Structured JSON logs | `core/logger.py` — one log line per action, includes profile, button, action_type, duration_ms, result |
| `/status` endpoint per daemon | helmd: active profile, devices online, last action, errors. mixd: channels, levels, devices. |
| Error envelope on action results | `ActionResult{ok, error, duration_ms, details}` — UI shows it |
| Optional Prometheus `/metrics` | Phase 2; counters for action firings, error rate, surface reconnects |
| Log rotation | `~/.../helm/logs/` rotated by size (10MB × 5) |

**No stdout printf.** Logger only.

---

## Testability

**Goal:** unit tests don't need real hardware or real networks.

| Mocked layer | How |
|---|---|
| Surface (HID) | `Surface` ABC; `FakeSurface` returns scripted events |
| HTTP services | `httpx.MockTransport` |
| Active-window detection | `Platform` ABC; `FakePlatform` returns scripted app names |
| Audio devices | mixd Python `DeviceEnumerator` ABC; tests use a stub |

Action dispatcher is **pure**: input = `ActionSpec + Context`, output = `ActionResult`. No side effects beyond what the action itself does.

Rust core is tested with file I/O fixtures (read WAV in, assert routing matrix output). Real audio device tests are integration-only and gated.

---

## Security

**Goal:** local trust boundary held; no accidental LAN exposure.

| Surface | Defense |
|---|---|
| Daemon HTTP bind | `127.0.0.1` only — enforced by config schema; refuses to start if config says `0.0.0.0` |
| Profile TOML | Action commands are not shell-evaluated; `shell` action takes a list, never a string |
| Web UI | No auth (localhost trust); CSRF tokens on POST routes anyway, to prevent random-page-XHR drive-bys |
| Keypress action | Validates key names against a known set; arbitrary text injection requires explicit `text` field |
| Update path | Profiles are user files; daemon does not auto-fetch from internet |

**If LAN access is added later:** require a token in `helm.toml`, log every authentication attempt, never disable.

---

## Scalability

**Not** users — this is single-user software. The relevant axis is **device count**:

| Axis | Support |
|---|---|
| Multiple Stream Decks | Day-one. Surface manager keyed by serial. |
| Multiple audio interfaces | mixd enumerates all; routing matrix is N×M. |
| Many profiles | Loader is lazy; only active profile rendered. |
| Profile size | Hard cap at 256 buttons + 32 knobs (XL is 32 buttons; ample headroom). |

---

## Usability

**Goal:** web UI is full hardware parity; profile creation does not require hardware.

| Feature | Detail |
|---|---|
| Web UI parity | Every hardware action also fireable from UI. UI shows live state. |
| Profile editor | Browser-based form (phase 2); meanwhile TOML is documented and ergonomic |
| Live state on keys | Active scene highlighted, in-progress actions show spinner |
| Multi-deck UI | Each connected deck rendered as its own grid in the UI |
| Onboarding | First run copies `profiles/` to user dir, opens web UI, displays setup checklist |

---

## Cross-references

- Platform abstraction details: `os-support.md`
- Hard parts and what we trade away: `risks-and-tradeoffs.md`
- Component file layout: `plan.md`
- Daemon split rationale: `architecture.md`
