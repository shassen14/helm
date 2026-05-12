import Foundation

@main
struct Mixd {
    static func main() async {
        let args = CommandLine.arguments
        guard args.count >= 2 else {
            printUsage()
            exit(ExitCode.usage)
        }
        let command = args[1]
        let rest = Array(args.dropFirst(2))

        do {
            switch command {
            case Subcommand.listApps:
                try await AppLister().run()
            case Subcommand.capture:
                try await AudioCapture(args: rest).run()
            default:
                printUsage()
                exit(ExitCode.usage)
            }
        } catch {
            writeStderr("error: \(error)\n")
            exit(ExitCode.failure)
        }
    }

    static func printUsage() {
        writeStderr(UsageText.body + "\n")
    }
}

func writeStderr(_ s: String) {
    if let data = s.data(using: .utf8) {
        FileHandle.standardError.write(data)
    }
}
