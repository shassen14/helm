---
type: design
status: stable
updated: 2026-05-09
---

# helm — architecture

> Two daemons in one repo. Strict ownership boundaries. Localhost-only HTTP between
> services. No daemon imports another daemon's runtime.

---

## Daemon split

```
                 ┌──────────────────────────────────────────────────────┐
                 │                     User                             │
                 └────────┬───────────────────────────────┬─────────────┘
                          │ presses key / turns knob       │ opens browser
                          ▼                                ▼
                 ┌──────────────────┐            ┌────────────────────┐
                 │  Stream Deck(s)  │            │  http://localhost  │
                 │   (USB HID)      │            │       :7100        │
                 └────────┬─────────┘            └─────────┬──────────┘
                          │                                │
                          └──────────────┬─────────────────┘
                                         ▼
                              ┌──────────────────────┐
                              │       helmd          │   port 7100
                              │ (Python, asyncio)    │
                              │  ┌───────────────┐   │
                              │  │ profiles      │   │
                              │  │ actions       │   │
                              │  │ surfaces      │   │
                              │  │ switcher      │   │
                              │  └───────────────┘   │
                              └──────┬──────┬────────┘
                                     │      │
                       HTTP          │      │   keypress / shell
                       (localhost)   │      └─────────────► system apps
                                     │                      (Spotify, Discord, …)
        ┌──────────────┬─────────────┼──────────────┐
        ▼              ▼             ▼              ▼
   ┌─────────┐   ┌──────────┐  ┌────────────┐  ┌─────────┐
   │  veil   │   │ boneless │  │   mixd     │  │ (future)│
   │  :8002  │   │  :8003   │  │   :7101    │  │   …     │
   │         │   │          │  │  control   │  │         │
   │  OWNS:  │   │  OWNS:   │  │  plane     │  │         │
   │  OBS    │   │  Twitch  │  │            │  │         │
   │  WS     │   │  Helix   │  │   ↕ IPC    │  │         │
   └─────────┘   └──────────┘  │            │  └─────────┘
                               │  Rust core │
                               │  (cpal)    │
                               │            │
                               │  OWNS:     │
                               │  audio I/O │
                               └────────────┘
```

---

## Ownership rules

| Concern | Owner | Why |
|---|---|---|
| HID / Stream Deck I/O | helmd | Nothing else needs HID |
| Active-window detection | helmd | Profile switcher is the only consumer |
| Keypress injection | helmd | Action dispatch is the only consumer |
| OBS WebSocket | **veil** | Singleton connection, multiple consumers (helm + chat + automation) |
| Twitch Helix / IRC | **boneless_couch** | Singleton bot; helm is just one trigger source |
| Audio device I/O + mix | **mixd** | Realtime, isolated process, separate failure domain |
| Profile schema | helmd | Defines what controls do |
| Action dispatch | helmd | Glue layer |

**Load-bearing principle:** *helm never owns stateful integrations.* Anything with a persistent socket, OAuth token, reconnect loop, or auth state belongs in a domain service. helmd holds no long-lived connections except to its own surfaces.

---

## helmd internal layers

```
┌─────────────────────────────────────────────────────────────┐
│ Web (FastAPI :7100)              Hardware (HID supervisor)  │
│   /status   /profiles  /fire       Surface[serial] ←→ libusb │
└──────────────┬─────────────────────────────────┬────────────┘
               │                                 │
               └────────────┬────────────────────┘
                            ▼
                ┌──────────────────────────┐
                │   Action Dispatcher       │
                │   (registry: Type → cls)  │
                └─────┬──────┬──────┬───┬───┘
                      ▼      ▼      ▼   ▼
                    http   shell keypress multi
                            │      │
                            └──────┴──► Platform layer
                                        (mac.py / linux.py)
                            ▲
                            │
                ┌───────────┴────────────┐
                │   Profile Manager       │
                │   active_profile, swap  │
                └────────┬────────────────┘
                         ▲
                         │
                ┌────────┴────────────────┐
                │   Profile Switcher       │
                │   poll foreground app    │
                │   (Platform layer)       │
                └──────────────────────────┘
```

Every layer talks downward. No sideways imports between routes/, hardware/, profiles/.

---

## mixd internal layers

```
┌─────────────────────────────────────┐
│  Python control plane (FastAPI)     │   port 7101
│   - device enumeration              │
│   - hot-plug listener (CoreAudio /  │
│     PipeWire registry)              │
│   - HTTP API (channels, levels,     │
│     routing matrix)                 │
│   - state persistence               │
└──────────────┬──────────────────────┘
               │ IPC (Unix socket / shared mem)
               ▼
┌─────────────────────────────────────┐
│  Rust core (cpal)                   │
│   - audio thread: pull from inputs, │
│     apply routing matrix, push to   │
│     virtual outputs                 │
│   - NO allocations in callback      │
│   - NO Python in callback           │
│   - lock-free SPSC ring buffers     │
│     for IPC                         │
└─────────────────────────────────────┘
```

The Python side never touches the audio callback. Control changes (level, route) cross IPC as small messages and are applied at buffer boundaries by the Rust thread.

---

## Profile schema (versioned)

```python
@dataclass
class Profile:
    schema_version: int     # bump on breaking change; loader migrates
    name: str
    trigger_apps: list[str]
    deck: str               # "any" or device serial
    buttons: list[Button]
    knobs: list[KnobBinding]
```

`loader.py` checks `schema_version` and runs migrations from older versions. Unknown future versions are rejected with a clear error.

---

## Multi-device model

A **Surface** is one physical device:

```python
class Surface(ABC):
    serial: str
    model: DeckModel       # MK2, XL, PLUS, NEO, MINI, PEDAL
    button_count: int
    knob_count: int

    async def render_button(self, idx: int, image: bytes) -> None: ...
    async def on_event(self) -> AsyncIterator[DeviceEvent]: ...
```

`SurfaceManager` holds `dict[str, Surface]`, listens for libusb hot-plug, and re-renders on reconnect. Profiles can target `deck = "any"` (applies to all connected) or a specific serial.

---

## Persistence

| What | Where |
|---|---|
| Daemon auto-start | launchd plist (mac) / systemd user unit (linux) |
| User profiles | `~/Library/Application Support/helm/profiles/` (mac), `~/.config/helm/profiles/` (linux) |
| Daemon state (active profile, manual override) | `~/.../helm/state.json` |
| Logs | `~/.../helm/logs/{helmd,mixd}.log` (rotated) |

Repo's `profiles/` directory is seed data; copied to user dir on first run if not present.

---

## Failure modes & containment

| Failure | Effect |
|---|---|
| veil down | helmd action returns error; deck button shows red border briefly; daemon stays up |
| Deck unplugged | Surface marked offline; web UI keeps working; auto-reconnect on replug |
| mixd crashes | systemd/launchd restarts it; helmd buttons that bind to mixd error out clearly |
| Profile TOML invalid | Loader rejects file, falls back to last-known-good or `default.toml`; logs which file failed |
| Audio device removed mid-mix | mixd channel goes offline, mix continues without it; UI shows the channel as disconnected |

No single failure cascades. Each daemon is an independent supervisor target.
