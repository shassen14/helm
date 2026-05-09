---
type: design
status: stable
updated: 2026-05-09
---

# helm — risks and tradeoffs

> What's hard, why it's hard, what mitigation we picked, and what we explicitly gave up.
> Read this before changing the architecture.

---

## Hard problems

### 1. Realtime audio in a Python ecosystem

**Why hard:** the audio callback runs at sub-buffer cadence (e.g. every 5 ms at 256-frame buffers / 48 kHz). Any GIL contention, GC pause, or syscall stall produces an audible click. Python in the audio path is a known footgun.

**Mitigation:** Rust core (cpal). Python only on the control plane. IPC via lock-free SPSC ring buffers; control changes applied at buffer boundaries. The audio thread allocates nothing and never calls into Python.

**Residual risk:** virtual audio drivers (BlackHole on Mac) can be flaky across OS upgrades. PipeWire on Linux changes API across versions. Plan: pin tested versions in docs; treat OS upgrades as a regression-test trigger.

---

### 2. Virtual audio output device creation

**Why hard:** OS-level virtual audio devices don't exist out-of-the-box on Mac. Wave Link bundles its own driver. We don't.

**Options considered:**
- **A. BlackHole + Loopback-style aggregate device** — user installs BlackHole; mixd creates aggregate devices on top via CoreAudio HAL. Pro: no driver development. Con: extra install step.
- **B. Custom CoreAudio HAL plugin** — ship our own virtual driver. Pro: zero install friction; matches Wave Link UX. Con: HAL plugin development is heavy; signed kext-adjacent, code signing, Apple notarization.
- **C. Skip virtual outputs, route via existing devices** — only useful for hardware mixers.

**Choice:** **A** for v1 (BlackHole). **B** is a possible v2 if user friction is high. Document the BlackHole install in onboarding.

On Linux: PipeWire null-sinks are first-class. No equivalent friction.

---

### 3. Active-window detection without hangs

**Why hard:** macOS `NSWorkspace` notifications are reliable but require a runloop. Polling with AppKit is fine but mustn't block. Linux x11 `xdotool` is a fork-per-call; Wayland is an entirely different story (each compositor has its own protocol).

**Mitigation:**
- Mac: use `NSWorkspace.notificationCenter` observer — push-driven, no polling.
- Linux X11: poll `wnck` once per `poll_interval_s` (default 2s).
- Linux Wayland: punt to v2. Document as "X11 only on Linux for now."

**Residual risk:** Wayland users are a growing share. Will need per-compositor support (sway has IPC; GNOME has a D-Bus extension) when the time comes.

---

### 4. Hot-plug correctness

**Why hard:** USB hot-plug on macOS via libusb hotplug callbacks works but interacts with sleep/wake oddly. Stream Deck devices may show up before HID claims are valid; race conditions at boot.

**Mitigation:**
- Supervisor pattern with bounded reconnect: detect → small delay (200ms) → claim → render last-known state.
- On daemon start, enumerate devices once, then subscribe to events.
- If a claim fails, mark surface as offline and retry on next event.

**Residual risk:** specific USB hubs (powered/unpowered) sometimes drop devices on macOS sleep. Document: "if your deck shows offline after sleep, try unplug/replug" — not a daemon bug.

---

### 5. Multiple Stream Decks colliding

**Why hard:** if two decks are present and a profile says `deck = "any"`, both render the same layout. Button presses must be attributed to the correct surface, especially when profiles differ.

**Mitigation:**
- Every event carries `serial`. Action dispatch context includes which surface fired.
- Profile resolution: per-surface lookup. `deck = "any"` profile applies if no per-serial profile exists.
- Web UI renders one grid per connected surface, labeled by serial (or user-given alias).

---

### 6. Rust ↔ Python build / packaging

**Why hard:** mixd ships a Rust crate. Users need a Rust toolchain to build, or we need prebuilt wheels per OS/arch.

**Mitigation:**
- Use `maturin` to build a Python extension module from the Rust crate. Wheels for `darwin-arm64`, `darwin-x86_64`, `linux-x86_64`, `linux-aarch64`.
- Dev mode: `maturin develop` rebuilds in place.
- CI builds wheels on each tagged release.

**Residual risk:** Rust toolchain churn. Pin `rust-toolchain.toml` to a known version.

---

### 7. Keypress injection accessibility prompts

**Why hard:** macOS requires Accessibility permission for any process that injects keystrokes. The first time helmd tries, the OS shows a permission dialog. If the user denies, all keypress actions silently fail.

**Mitigation:**
- On first run, web UI shows a setup checklist that includes "Grant Accessibility permission to helmd."
- `/status` reports `accessibility: granted | denied | unknown`.
- Keypress actions check this before firing and return a clear error if denied.

---

### 8. Profile schema drift

**Why hard:** users hand-edit TOML. Adding fields breaks old files; removing fields breaks new code reading old files.

**Mitigation:** versioned schema from day one. Loader runs migrations forward. Unknown future versions rejected with a message pointing at the docs.

---

## Tradeoffs we accepted

| Decision | What we gave up | What we got |
|---|---|---|
| **Two daemons, not one** | Slightly more setup; two ports; two units | Audio realtime safety; independent crash domains; clean dep separation |
| **OBS in veil, not helm** | Tiny extra hop on scene switch (sub-ms) | Singleton OBS connection shared by chat/automation/helm; helm stays a pure dispatcher |
| **Rust core for mixd, not pure Python** | Build complexity (Rust toolchain, wheels) | Realtime guarantees Python cannot provide; no clicks |
| **Localhost-only, no auth** | No remote control out of the box | No auth attack surface; simple trust model; no token management |
| **TOML profiles, no GUI editor v1** | Less friendly to non-technical users (not our user) | Version-controllable, copy-pasteable, scripts can generate them |
| **Multi-device day one** | Slightly more design work upfront | Refactor avoided when second deck shows up |
| **X11-first on Linux** | Wayland users blocked initially | Ship sooner; one window-detection backend |
| **BlackHole dependency on Mac** | One extra install step in onboarding | Skip writing and notarizing a CoreAudio HAL plugin |
| **No cloud sync** | No "my profiles on a new machine" magic | No backend, no privacy concerns; users put profiles in their dotfiles repo |
| **Schema versioning, not "just be careful"** | Slightly more code in the loader | Old profiles keep working; breaking changes are explicit |

---

## What we are explicitly NOT building

| Not building | Why |
|---|---|
| GUI profile editor (v1) | TOML is good enough for the user; v2 if requested |
| Mobile app | Localhost-only design; no remote control |
| Cloud sync | No backend; profiles live in user's dotfiles |
| Plugin marketplace | Not warranted at single-user scale |
| Wave Link parity for "Smart Mute" / "Mix Lock" advanced features | v1 ships basic per-app routing + multi-output. Polish later. |
| Windows support (v1) | Architecture allows it; nobody using Windows yet |
| Wayland support (v1) | Architecture allows it; X11 covers the user |
| Auth on the HTTP plane | Localhost-only; adding auth would be over-engineering |

---

## When to revisit this doc

- Adding a third daemon → reconsider whether monorepo still fits.
- Wanting LAN/mobile control → security section needs a redesign.
- Wayland/Windows demand → `os-support.md` and platform abstraction get exercised.
- Hitting Python audio limits before Rust core is built → may need to reorder build steps.
- BlackHole becomes unmaintained or breaks on a macOS upgrade → option B (HAL plugin) gets re-evaluated.
