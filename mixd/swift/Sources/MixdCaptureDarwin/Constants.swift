import Foundation

enum Subcommand {
    static let listApps = "list-apps"
    static let capture = "capture"
}

enum CLIArg {
    static let bundleID = "--bundle-id"
    static let system = "--system"
    static let header = "--header"
}

enum Diagnostics {
    static let frameLogInterval: Int = 50  // log every Nth audio buffer to stderr
    static let heartbeatSeconds: UInt64 = 2
}

enum ExitCode {
    static let success: Int32 = 0
    static let failure: Int32 = 1
    static let usage: Int32 = 2
}

enum AudioFormat {
    static let sampleRate: Int = 48_000
    static let channelCount: Int = 2
}

enum CaptureGeometry {
    // SCK requires a display config even for audio-only; minimize CPU by
    // requesting the smallest possible frame and the longest interval.
    static let width: Int = 2
    static let height: Int = 2
    static let frameIntervalSeconds: Int32 = 60
}

enum UsageText {
    static let body = """
    usage: mixd-capture-darwin <command> [args]

    commands:
      list-apps                       print JSON of capturable running apps
      capture --bundle-id <bundle-id> stream one app's audio to stdout
      capture --system                stream system-wide audio to stdout (diagnostic)
    """
}
