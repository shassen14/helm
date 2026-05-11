---
type: plan
status: in-progress
updated: 2026-05-11 (steps 1–9 complete)
---

# helm — build plan

> helm is a **monorepo replacing both Elgato Stream Deck and Elgato Wave Link software**.
> Two daemons live in this repo: **helmd** (control surface — HID + web UI + action dispatch)
> and **mixd** (virtual audio mixer — Rust realtime core + Python control plane).
> Both bind localhost only. Both auto-start with the OS. Both support hot-plug of multiple
> devices on day one.

See companion docs:

- `architecture.md` — daemon split, ownership boundaries, data flow
- `ilities.md` — how each -ility is supported, with concrete mechanisms
- `risks-and-tradeoffs.md` — what's hard, what we gave up, why
- `os-support.md` — per-OS implementation detail and feature matrix

---

## Scope

| Replaces               | helm component | What it does                                                                       |
| ---------------------- | -------------- | ---------------------------------------------------------------------------------- |
| Elgato Stream Deck app | **helmd**      | HID input, button/knob bindings, profiles, action dispatch, web UI                 |
| Elgato Wave Link app   | **mixd**       | Virtual audio mixer, per-app routing, multi-output mixes (Stream / Monitor / Chat) |

**helm never owns stateful integrations.** It is input → action mapping. OBS lives in veil.
Twitch lives in boneless_couch. Audio lives in mixd. helmd is the glue.

---

## Ports

| Service      | Bind           | Purpose                              |
| ------------ | -------------- | ------------------------------------ |
| helmd web UI | 127.0.0.1:7100 | Control surface UI + action dispatch |
| mixd HTTP    | 127.0.0.1:7101 | Mixer control plane                  |
| veil         | 127.0.0.1:8002 | OBS scene control, alerts, overlay   |

All localhost only. No auth on the local trust boundary. Document this — adding LAN access requires a token, not just `0.0.0.0`.

---

## Repo structure

```
helm/
  helmd/                     # control surface daemon
    core/
      config.py              # TOML loader + Settings
      constants.py           # ActionType, KnobEvent, ProfileTrigger enums
      paths.py               # XDG / Library paths abstraction
      logger.py              # Structured JSON logger
      platform/
        __init__.py          # selects backend at runtime
        mac.py               # AppKit window detection, keypress
        linux.py             # xdotool / wnck
    actions/
      base.py                # Action ABC + ActionResult
      http.py
      shell.py
      keypress.py
      multi.py
      registry.py            # ActionType → class
    profiles/
      schema.py              # Button, KnobBinding, Profile dataclasses (versioned)
      loader.py              # TOML → Profile, validates
      manager.py             # Active profile, switch logic
      switcher.py            # Foreground app → auto-switch
    hardware/
      surface.py             # Surface ABC (one per physical device)
      deck.py                # python-elgato-streamdeck adapter
      renderer.py            # Pillow: render key images
      supervisor.py          # Hot-plug + reconnect loop, multi-device manager
    web/
      server.py              # FastAPI on 7100
      routes/{ui,profiles,actions,status}.py
    __main__.py              # daemon entry
  mixd/                      # audio mixer daemon
    rust/                    # cpal-based realtime core (cargo crate)
      Cargo.toml
      src/{lib,engine,routing,ipc}.rs
    python/
      server.py              # FastAPI on 7101
      devices.py             # CoreAudio / PipeWire enumeration + hot-plug
      config.py
      state.py
      __main__.py
  shared/
    profile_schema.py        # Cross-daemon constants if needed
  profiles/                  # default TOML profiles (user copies override)
    default.toml
    streaming_coding.toml
    editing.toml
    ...
  packaging/
    launchd/                 # com.media-os.helmd.plist, com.media-os.mixd.plist
    systemd/                 # helmd.service, mixd.service (user units)
  docs/
    plan.md                  # this file
    architecture.md
    ilities.md
    risks-and-tradeoffs.md
    os-support.md
  helm.toml                  # daemon config
  pyproject.toml             # both daemons share top-level project, separate extras
```

All Python files <300 lines. No magic strings — enums in `constants.py`. No inline config values. OOP composition.

---

## Build order

| #   | Task                                                                              | Status  | Notes                                                                              |
| --- | --------------------------------------------------------------------------------- | ------- | ---------------------------------------------------------------------------------- |
| 1   | veil: OBS WebSocket + `/scenes` routes                                            | ✅ done | Confirms OBS ownership stays in veil                                               |
| 2   | helmd: scaffold (pyproject, packaging dirs)                                       | ✅ done | Full stub tree; imports cleanly                                                    |
| 3   | helmd: core (config, constants, paths, platform, logger)                          | ✅ done | Mac (osascript) + Linux (xdotool) backends; pynput chord send_keys                 |
| 4   | helmd: profiles (schema, loader, manager, switcher)                               | ✅ done | discover() globs user profiles dir; switcher polls active window every N s         |
| 5   | helmd: actions (base, types, registry)                                            | ✅ done | HTTP/shell/keypress/multi all wired; multi uses local import to break circular ref |
| 6   | helmd: web (FastAPI on 7100, /status, profile CRUD, dispatch)                     | ✅ done | Factory pattern (create_app); state passed via app.state; all routes live          |
| 7   | helmd: hardware (Surface ABC, StreamDeck adapter, multi-device supervisor)        | ✅ done | Hot-plug poll loop; path-based dedup avoids re-opening held HID handle; dial/key callbacks bridged to asyncio via run_coroutine_threadsafe |
| 8   | helmd: launchd + systemd units                                                    | ✅ done | Token-template plist + service; install.sh detects Python, OS, log dir, loads unit |
| 9   | mixd Python skeleton (device enum, HTTP on 7101, route Spotify→Stream / mic→both) | ✅ done | constants/state/devices/routes/server all wired; factory pattern matches helmd     |
| 10  | mixd Rust mix core (cpal + routing matrix + IPC to Python)                        | ✅      | Realtime callback, no allocations                                                  |
| 11  | helm web UI mixer panel (binds to mixd HTTP)                                      | ⬜      | Final integration                                                                  |

Steps 1–8 ship a Stream Deck replacement. Steps 9–11 ship the Wave Link replacement.

---

## Profile TOML format

Schema is versioned. New top-level field: `schema_version = 1`.

```toml
schema_version = 1

[profile]
name = "streaming_coding"
trigger_apps = ["OBS Studio"]
deck = "any"                  # or specific serial: "AL12K1A12345"

[[profile.buttons]]
index = 0
label = "Scene: Coding"
icon = "icons/coding.png"
action = {type = "http", url = "http://localhost:8002/scenes/switch", method = "POST", body = {scene = "coding"}}

[[profile.buttons]]
index = 1
label = "Mute Stream Mix"
icon = "icons/mute.png"
action = {type = "http", url = "http://localhost:7101/channels/stream/mute", method = "POST"}

# Knobs — Stream Deck +
[[profile.knobs]]
index = 0
label = "Mic Level"
on_turn = {type = "http", url = "http://localhost:7101/channels/mic/level", method = "POST", body_template = {delta = "{delta}"}}
on_press = {type = "http", url = "http://localhost:7101/channels/mic/mute", method = "POST"}
```

User profiles live outside the repo so updates don't clobber:

- macOS: `~/Library/Application Support/helm/profiles/`
- Linux: `~/.config/helm/profiles/` (XDG)

Repo `profiles/` is seed data, copied on first run.

---

## helm.toml (daemon config)

```toml
[helmd]
host = "127.0.0.1"
port = 7100
brightness = 70

[mixd]
host = "127.0.0.1"
port = 7101

[services]
# veil runs on the Pi — set to Pi's LAN IP.
# helmd and mixd run on this machine — localhost is correct for those.
veil_url = "http://192.168.1.X:8002"    # TODO: set Pi LAN IP

[switcher]
enabled = true
poll_interval_s = 2

[devices]
# Empty = accept all decks. Or pin specific serials.
allowed_deck_serials = []
```

---

## What this plan does NOT cover

- **rig** (workspace setup tool) — separate project, triggered by helm via `shell` action.
- **content_os**, **splice** — independent projects; helm calls them via shell or HTTP.
- **LAN / mobile control** — out of scope. Local-only.
- **Cloud sync of profiles** — out of scope. Profiles are git-trackable in a dotfiles repo.
