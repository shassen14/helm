---
type: design
status: stable
updated: 2026-05-09
---

# helm — OS support

> Per-OS implementation detail and feature support matrix. Anything OS-specific MUST live
> in the platform abstraction; this doc is the source of truth for what each backend does.

---

## Support tiers

| Tier | Meaning |
|---|---|
| **Primary** | Tested on every change. Bugs block release. |
| **Secondary** | Architecture supports it; tested on milestone releases. |
| **Future** | Architecture must not preclude; no current implementation. |

| OS | Tier |
|---|---|
| macOS 14+ (Sonoma, Sequoia) on Apple Silicon | Primary |
| macOS 14+ on Intel | Secondary |
| Linux X11 (Arch, Debian, Ubuntu) | Primary |
| Linux Wayland (sway, GNOME) | Future |
| Windows 11 | Future |

---

## Feature × OS matrix

| Feature | macOS | Linux X11 | Linux Wayland | Windows |
|---|---|---|---|---|
| Stream Deck HID | ✅ python-elgato-streamdeck (libusb) | ✅ same | ✅ same | 🟡 future, lib supports it |
| Active-window detection | ✅ AppKit `NSWorkspace` | ✅ wnck / xdotool | ❌ per-compositor (sway IPC, GNOME D-Bus) | 🟡 future, `pygetwindow` |
| Keypress injection | ✅ pynput + Accessibility permission | ✅ pynput / xdotool | ❌ requires uinput or compositor protocol | 🟡 future, pynput |
| Shell action | ✅ subprocess | ✅ subprocess | ✅ subprocess | 🟡 future, subprocess |
| Auto-start on login | ✅ launchd user agent | ✅ systemd --user | ✅ same | 🟡 future, NSSM / Task Scheduler |
| Audio device enumeration | ✅ CoreAudio | ✅ PipeWire / ALSA | ✅ PipeWire | 🟡 future, WASAPI |
| Audio I/O (mixd Rust core) | ✅ cpal → CoreAudio | ✅ cpal → ALSA/JACK | ✅ cpal → PipeWire | 🟡 future, cpal → WASAPI |
| Virtual output device | 🟡 BlackHole install required | ✅ PipeWire null-sink (built-in) | ✅ same | 🟡 future, VB-Cable or similar |
| Hot-plug (USB) | ✅ libusb hotplug | ✅ udev | ✅ udev | 🟡 future |
| Hot-plug (audio) | ✅ CoreAudio property listener | ✅ PipeWire registry | ✅ same | 🟡 future, MMNotificationClient |

Legend: ✅ supported · 🟡 architecture-ready, not implemented · ❌ blocked by OS / not planned for v1.

---

## Platform abstraction

### `helmd/core/platform/`

```python
# __init__.py
import sys
if sys.platform == "darwin":
    from .mac import MacPlatform as Platform
elif sys.platform.startswith("linux"):
    from .linux import LinuxPlatform as Platform
else:
    raise NotImplementedError(...)

# base interface (declared for type checkers)
class PlatformProtocol(Protocol):
    async def active_window(self) -> ActiveWindow: ...
    async def watch_active_window(self) -> AsyncIterator[ActiveWindow]: ...
    def send_key(self, key: KeySpec) -> None: ...
    def accessibility_status(self) -> PermissionStatus: ...
```

**Hard rule:** `if sys.platform` appears nowhere outside `core/platform/__init__.py`.

---

## macOS specifics

### Active-window detection
`NSWorkspace.sharedWorkspace().notificationCenter()` observer for `NSWorkspaceDidActivateApplicationNotification`. Push-driven. No polling needed for accuracy. Switcher subscribes; profile manager applies.

### Keypress injection
`pynput.keyboard.Controller`. Requires Accessibility permission on first use. helmd's `/status` reports the permission state by attempting a no-op probe and catching the OS error. Setup checklist explains how to grant.

### Auto-start
`packaging/launchd/com.media-os.helmd.plist`:
```xml
<key>KeepAlive</key><true/>
<key>RunAtLoad</key><true/>
<key>ProgramArguments</key><array>...path to helmd...</array>
```
Installed to `~/Library/LaunchAgents/`. mixd has its own plist.

### Audio (mixd)
- Enumerate via CoreAudio `kAudioHardwarePropertyDevices`.
- Hot-plug via `AudioObjectAddPropertyListener` on the same property.
- Virtual outputs require **BlackHole 2ch / 16ch** (user-installed). Onboarding prompts the install.
- Rust core uses cpal → CoreAudio backend.

### Filesystem paths
`~/Library/Application Support/helm/` — config, profiles, state, logs.

### Code signing / notarization
Required if helmd is distributed as a `.app` bundle. CLI install (pip / pipx) doesn't need it. Plan: ship CLI for now; notarized bundle is a v2 packaging concern.

---

## Linux specifics

### Active-window detection (X11)
- **wnck** (GTK lib) preferred — gives WM_CLASS reliably.
- **xdotool** fallback — fork-per-call but universally available.
- Polling at `poll_interval_s` (default 2s). Push-driven via X events is possible but adds runloop complexity; punt.

### Keypress injection
`pynput` works on X11. On Wayland, `pynput` does not work; we'd need `uinput` (root or input group) or compositor-specific protocols. Wayland is Future tier.

### Auto-start
`packaging/systemd/helmd.service` (user unit) installed to `~/.config/systemd/user/`:
```ini
[Service]
ExecStart=...
Restart=always
RestartSec=2

[Install]
WantedBy=default.target
```
Activated with `systemctl --user enable --now helmd`. Same for mixd.

### Audio (mixd)
- Enumerate via PipeWire (preferred) or ALSA (fallback).
- Hot-plug via PipeWire registry events.
- Virtual outputs: `pw-loopback` or `module-null-sink` — first-class on PipeWire. No third-party install.
- Rust core uses cpal → ALSA / JACK / PipeWire backend depending on what's available.

### Filesystem paths
`$XDG_CONFIG_HOME/helm/` (default `~/.config/helm/`) — config, profiles, state.
`$XDG_STATE_HOME/helm/logs/` — logs.

### Distros tested
Arch (rolling), Debian 12+, Ubuntu 24.04+. Older distros may lack PipeWire; mixd falls back to ALSA-direct (lower fidelity in routing).

---

## Wayland (Future)

Blockers:
- No portable active-window protocol; each compositor differs.
  - sway: i3 IPC compatible — `swaymsg -t get_tree`.
  - GNOME: D-Bus extension required (`Window Calls Extended` or similar).
  - KDE: KWin scripting.
- No portable keypress injection. `uinput` requires root or `input` group; some compositors block synthesized events from non-portal sources.

When implemented, the platform layer grows a `linux_wayland.py` backend selected by `XDG_SESSION_TYPE=wayland`.

---

## Windows (Future)

Architecture is Windows-friendly:
- `pygetwindow` / `pywin32` for active window.
- `pynput` for keypress.
- `cpal` → WASAPI for audio.
- NSSM or scheduled task for auto-start.
- Virtual audio: VB-CABLE or similar (analogous to BlackHole).

Not implemented because no current user. Don't take dependencies that preclude it (e.g. unconditional POSIX-only paths).

---

## Hard rules across all OS

1. **Localhost-only bind.** Config refuses `0.0.0.0`.
2. **No platform branches outside `core/platform/`**. Lint check enforces this.
3. **Same profile TOML works on all primary OSes.** Profile authors should not write OS-specific TOML; if they need OS-specific actions, use `shell` action with a script that itself branches.
4. **Daemon must survive OS sleep/wake.** Surfaces and audio devices may disappear and reappear; supervisor handles this.
5. **No silent OS-permission failures.** `/status` reports Accessibility (Mac) and equivalent permissions; UI surfaces them.

---

## Cross-references

- Architecture: `architecture.md`
- Hard problems by OS: `risks-and-tradeoffs.md` (sections 2, 3, 7)
- Build steps: `plan.md`
