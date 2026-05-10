# helm

Stream Deck controller daemon replacing the Elgato app. Profiles, hot-plug, action dispatch, auto-start on login.

---

## Requirements

- Python 3.12+
- macOS 13+ or Linux (systemd user session)
- Stream Deck connected over USB
- [hidapi](https://github.com/libusb/hidapi) — install via Homebrew on macOS: `brew install hidapi`

---

## Install

```bash
git clone <repo> helm
cd helm
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[helmd]"
```

---

## Run

```bash
source .venv/bin/activate
python3 -m helmd
```

helmd reads `helm.toml` from the project root. Profiles are loaded from:

- **macOS**: `~/Library/Application Support/helm/profiles/`
- **Linux**: `~/.config/helm/profiles/`

Copy a profile to get started:

```bash
# macOS
mkdir -p ~/Library/Application\ Support/helm/profiles
cp profiles/default.toml ~/Library/Application\ Support/helm/profiles/

# Linux
mkdir -p ~/.config/helm/profiles
cp profiles/default.toml ~/.config/helm/profiles/
```

---

## Auto-start on login

```bash
bash packaging/install.sh
```

The script detects Python (respects `$VIRTUAL_ENV`), your OS, creates the log directory, and loads the service:

- **macOS**: installs `~/Library/LaunchAgents/com.media-os.helmd.plist` and loads it with `launchctl`
- **Linux**: installs `~/.config/systemd/user/helmd.service` and enables it with `systemctl --user`

Logs:

- **macOS**: `~/Library/Application Support/helm/logs/helmd.{log,err}`
- **Linux**: `~/.config/helm/logs/helmd.{log,err}`

---

## Configuration — helm.toml

```toml
[helmd]
host = "127.0.0.1"
port = 7100
brightness = 70          # 0–100

[switcher]
enabled = true
poll_interval_s = 2      # how often to check foreground app

[devices]
# Leave empty to accept any connected deck.
# Pin to specific serials to ignore other devices.
allowed_deck_serials = []
```

---

## Profile format

Profiles live in the user profiles directory as `.toml` files.

```toml
schema_version = 1

[profile]
name = "streaming"
trigger_apps = ["OBS Studio"]   # auto-activate when this app is in focus
deck = "any"                    # or a specific serial

[[profile.buttons]]
index = 0
label = "Go Live"
icon = "icons/live.png"         # relative to profiles dir
action = {type = "http", url = "http://localhost:8002/scenes/switch", method = "POST", body = {scene = "live"}}

[[profile.buttons]]
index = 1
label = "Shell"
action = {type = "shell", command = "open -a Terminal"}

# Stream Deck + knobs
[[profile.knobs]]
index = 0
label = "Vol"
on_turn  = {type = "keypress", keys = ["volume_up"]}
on_press = {type = "keypress", keys = ["volume_mute"]}
```

Action types: `http`, `shell`, `keypress`, `multi`.

---

## Web API

helmd exposes a local HTTP API on port 7100.

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/status` | Version, active profile, connected decks |
| `GET` | `/profiles` | List all loaded profiles |
| `POST` | `/profiles/active` | Switch active profile `{"name": "streaming"}` |
| `POST` | `/actions/dispatch` | Fire an action directly |

---

## macOS gotchas

### Quit the Elgato Stream Deck app

The official Elgato app holds the HID device exclusively. helmd cannot open the deck while it is running — not even in the background (`--runinbk`). Quit it from the menu bar before starting helmd, and remove it from Login Items so it does not restart on reboot.
