from enum import StrEnum


class MixOutput(StrEnum):
    STREAM = "stream"
    MONITOR = "monitor"
    CHAT = "chat"


class ChannelName(StrEnum):
    SPOTIFY = "spotify"
    MIC = "mic"
    DESKTOP = "desktop"


DEFAULT_ROUTING: dict[str, list[str]] = {
    ChannelName.SPOTIFY: [MixOutput.STREAM],
    ChannelName.MIC: [MixOutput.STREAM, MixOutput.MONITOR],
    ChannelName.DESKTOP: [MixOutput.STREAM, MixOutput.MONITOR],
}
