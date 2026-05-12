import Foundation
import ScreenCaptureKit

struct AppInfo: Codable {
    let bundleIdentifier: String
    let applicationName: String
    let processID: Int32
}

struct AppLister {
    func run() async throws {
        let content = try await SCShareableContent.excludingDesktopWindows(
            false,
            onScreenWindowsOnly: false
        )
        let apps = content.applications
            .filter { !$0.bundleIdentifier.isEmpty }
            .map {
                AppInfo(
                    bundleIdentifier: $0.bundleIdentifier,
                    applicationName: $0.applicationName,
                    processID: $0.processID
                )
            }
            .sorted {
                $0.applicationName.localizedCaseInsensitiveCompare($1.applicationName)
                    == .orderedAscending
            }

        let encoder = JSONEncoder()
        encoder.outputFormatting = [.prettyPrinted, .sortedKeys]
        let data = try encoder.encode(apps)
        FileHandle.standardOutput.write(data)
        if let nl = "\n".data(using: .utf8) {
            FileHandle.standardOutput.write(nl)
        }
    }
}
