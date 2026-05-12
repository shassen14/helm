// swift-tools-version: 5.9
import PackageDescription

let package = Package(
    name: "MixdCaptureDarwin",
    platforms: [.macOS(.v14)],
    products: [
        .executable(name: "mixd-capture-darwin", targets: ["MixdCaptureDarwin"]),
    ],
    targets: [
        .executableTarget(
            name: "MixdCaptureDarwin",
            path: "Sources/MixdCaptureDarwin"
        ),
    ]
)
