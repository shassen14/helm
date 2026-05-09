---
tags: [content, streaming, automation, tools, system-control]
type: project
area: build
status: idea
created: 2026-04-19
---

# helm

> A cross-platform monorepo replacing **both** the Elgato Stream Deck app and the Elgato Wave Link app. Two daemons: `helmd` (control surface — buttons, knobs, profiles, web UI) and `mixd` (virtual audio mixer — Rust realtime core + Python control plane).

---

## Purpose

`helm` replaces Elgato's stack entirely:

- **helmd** — controls **any app on the system** (Spotify, Discord, DaVinci Resolve, OBS, Photoshop, etc.) from a Stream Deck and a web UI. Profiles auto-switch per active foreground app.
- **mixd** — virtual audio mixer with per-app routing and multi-output mixes (Stream / Monitor / Chat), replacing Wave Link.

Both daemons localhost-only, both auto-start with the OS, both support hot-plug of multiple devices on day one.

**Primary OS:** macOS (Apple Silicon) + Linux X11. **Future:** Wayland, Windows. See `os-support.md`.

## Detailed docs

- `plan.md` — repo layout, build order, profile schema
- `architecture.md` — daemon split, ownership boundaries, data flow
- `ilities.md` — reliability / availability / portability / extensibility / maintainability / observability / testability / security / scalability / usability — concrete mechanisms
- `risks-and-tradeoffs.md` — what's hard, what we gave up, what we explicitly do not build
- `os-support.md` — per-OS implementation detail and feature matrix

---

## Core Features

### Activity Profiles
Named profiles loaded per context. Switching profiles reassigns the full button grid.

| Profile | Use case |
|---|---|
| `streaming_coding` | OBS scenes, chat toggle, boneless_couch commands, alert triggers |
| `streaming_gaming` | Game-specific scenes, clip creation, raid handling |
| `streaming_duolingo` | Minimal layout: scene, BRB, end stream |
| `editing` | splice passes, teleprompter, timeline nav |
| `photoshop` | Tool shortcuts, layer visibility, export presets |
| `blender` | Viewport modes, render trigger, timeline scrub |
| `default` | App launcher, system controls, music |

Profiles are defined in TOML files — no GUI required to create or edit them.

### Auto-Switch by Active App
Detect the foreground application and auto-load the matching profile. Override with a manual hold.

```
DaVinci Resolve opens → load "editing" profile automatically
OBS goes fullscreen → load "streaming_*" profile based on active scene
Photoshop focused → load "photoshop" profile
```

### Action Types
Each button maps to one or more actions, executed in sequence:

| Action type | Examples |
|---|---|
| `shell` | Launch app, run script, kill process, control Spotify via CLI |
| `http` | Call veil, splice, boneless_couch APIs, or any localhost service |
| `keypress` | Send keystroke to active app (Discord mute, Photoshop tools, etc.) |
| `scene_switch` | Direct veil scene change |
| `alert_fire` | Trigger veil alert |
| `resolve_pass` | Run a splice CLI pass |
| `multi` | Chain multiple actions on one button press |

### Button States
Buttons can reflect live state (not just fire-and-forget):

- Active scene highlighted in `streaming` profiles
- `splice` pass in-progress shown with spinner/color
- `boneless_couch` stream live/offline status on a key
- Worker health from `content_os` on a key
- Spotify playback state (playing/paused) on a key

### Cross-OS Runtime
Runs as a background daemon. No dependency on Elgato's proprietary software — uses the Stream Deck USB HID protocol directly (via `streamdeck` Python library or similar). Works on macOS, Windows, and Linux.

---

## Architecture

```
Stream Deck (USB HID)
    ↕ HID protocol
helm daemon (Python, cross-platform)
    ├── reads profile TOML configs
    ├── detects active window → auto-switches profile
    └── dispatches actions:
          → shell: subprocess
          → http: requests (to veil, splice, boneless_couch)
          → keypress: platform input injection (pynput)
          → direct Resolve API calls (optional, for editing profile)
```

Optional: small system tray icon showing active profile and daemon status.

---

## Tech Stack

| Layer | Choice |
|---|---|
| Stream Deck HID | `python-elgato-streamdeck` library (cross-platform, no SDK required) |
| Config | TOML profiles |
| HTTP actions | `httpx` (async) |
| Keypress injection | `pynput` |
| Active window detection | `pygetwindow` (Win) / `AppKit` (Mac) / `xdotool` (Linux) |
| Button images | Pillow (PIL) for dynamic key renders |
| Daemon management | systemd (Linux), launchd (Mac), NSSM (Windows) |

---

## Profile Config Format

```toml
[profile]
name = "editing"
trigger_apps = ["DaVinci Resolve"]

[[profile.buttons]]
index = 0
label = "Audio Pass"
icon = "icons/audio.png"
action = {type = "resolve_pass", pass = "audio"}

[[profile.buttons]]
index = 1
label = "Color Pass"
icon = "icons/color.png"
action = {type = "resolve_pass", pass = "color"}

[[profile.buttons]]
index = 2
label = "Teleprompter"
icon = "icons/script.png"
action = {type = "http", url = "http://localhost:7000/script/toggle", method = "POST"}

[[profile.buttons]]
index = 5
label = "OBS Scene: BRB"
icon = "icons/brb.png"
action = {type = "scene_switch", scene = "brb"}
```

---

## Relationship to Other Projects and Apps

| Target | Relationship |
|---|---|
| `veil` | Scene switches, alert triggers, chat toggle via HTTP API |
| `splice` | Trigger editing passes during DaVinci session |
| `boneless_couch` | Fire commands (e.g., mark clip, run ad) via HTTP API |
| `content_os` | Monitor worker status on buttons; could trigger ingest |
| Spotify | Playback control via shell (Spotify CLI or AppleScript/DBus) |
| Discord | Mute/deafen, push-to-talk via keypress injection |
| DaVinci Resolve | Editing shortcuts, marker actions via keypress or splice CLI |
| Photoshop / Blender | Tool shortcuts, viewport modes via keypress injection |
| Any app | Shell actions, keypress injection — helm works for any app on the OS |

---

## Scope Notes

- Elgato's official software is **not required** — helm replaces it entirely
- Controls any app on the OS, not just media_os services
- Profile files are portable and version-controllable (TOML in the repo)
- No cloud sync, no telemetry — pure local daemon
- Cross-OS: macOS, Linux, Windows. OS-specific calls (window detection, keypress) are abstracted behind a platform interface

---

## Next
- [ ] Confirm `python-elgato-streamdeck` works on macOS with current Stream Deck model
- [ ] Prototype: load a profile, render button images, respond to button press
- [ ] Implement active window detection on Mac (AppKit)
- [ ] Define HTTP API contract with veil (needed before implementing http actions)
- [ ] Design profile config schema
- [ ] Implement auto-switch trigger logic
