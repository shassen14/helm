from enum import StrEnum


class MixOutput(StrEnum):
    STREAM = "stream"
    MONITOR = "monitor"
    CHAT = "chat"


class ChannelKind(StrEnum):
    APP = "app"
    MIC = "mic"
    SYSTEM = "system"


# Matches `N_CHANNELS` in `mixd/rust/src/routing.rs`. The Rust audio core
# pre-allocates this many ring-buffer slots, so the dynamic Python channel
# registry can hold at most this many active channels at once.
MAX_CHANNELS = 16

# Bitmask must match `OUT_*` in `mixd/rust/src/routing.rs`.
OUTPUT_BITS: dict[str, int] = {
    MixOutput.STREAM: 0b001,
    MixOutput.MONITOR: 0b010,
    MixOutput.CHAT: 0b100,
}
