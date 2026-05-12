import AVFoundation
import CoreMedia
import Foundation
import ScreenCaptureKit

enum CaptureError: Error, CustomStringConvertible {
    case missingTarget
    case appNotFound(String)
    case noDisplay

    var description: String {
        switch self {
        case .missingTarget: return "specify \(CLIArg.bundleID) <id> or \(CLIArg.system)"
        case .appNotFound(let b): return "app not found: \(b)"
        case .noDisplay: return "no display available for SCK content filter"
        }
    }
}

enum CaptureTarget {
    case app(bundleID: String)
    case system
}

final class AudioCapture: NSObject, SCStreamDelegate, SCStreamOutput {
    private let target: CaptureTarget
    private let emitHeader: Bool
    private var stream: SCStream?
    private let writeQueue = DispatchQueue(label: "mixd.capture.write")
    private var frameCount = 0
    private var totalBytes = 0
    private var formatChecked = false
    private var converter: AVAudioConverter?

    init(args: [String]) throws {
        self.emitHeader = args.contains(CLIArg.header)
        if args.contains(CLIArg.system) {
            self.target = .system
        } else if let i = args.firstIndex(of: CLIArg.bundleID), i + 1 < args.count {
            self.target = .app(bundleID: args[i + 1])
        } else {
            throw CaptureError.missingTarget
        }
        super.init()
    }

    func run() async throws {
        let content = try await SCShareableContent.excludingDesktopWindows(
            false,
            onScreenWindowsOnly: false
        )
        guard let display = content.displays.first else {
            throw CaptureError.noDisplay
        }

        let filter: SCContentFilter
        let label: String
        switch target {
        case .app(let bundleID):
            guard let app = content.applications.first(where: { $0.bundleIdentifier == bundleID })
            else {
                throw CaptureError.appNotFound(bundleID)
            }
            filter = SCContentFilter(display: display, including: [app], exceptingWindows: [])
            label = bundleID
        case .system:
            filter = SCContentFilter(display: display, excludingWindows: [])
            label = "system"
        }

        let config = SCStreamConfiguration()
        config.capturesAudio = true
        config.excludesCurrentProcessAudio = true
        config.sampleRate = AudioFormat.sampleRate
        config.channelCount = AudioFormat.channelCount
        config.width = CaptureGeometry.width
        config.height = CaptureGeometry.height
        config.minimumFrameInterval = CMTime(
            value: CMTimeValue(CaptureGeometry.frameIntervalSeconds),
            timescale: 1
        )

        let s = SCStream(filter: filter, configuration: config, delegate: self)
        try s.addStreamOutput(
            self,
            type: .audio,
            sampleHandlerQueue: DispatchQueue(label: "mixd.capture.audio")
        )
        self.stream = s
        try await s.startCapture()

        if emitHeader {
            let header =
                "{\"sample_rate\":\(AudioFormat.sampleRate)"
                + ",\"channels\":\(AudioFormat.channelCount)"
                + ",\"format\":\"f32le\"}\n"
            if let data = header.data(using: .utf8) {
                try FileHandle.standardOutput.write(contentsOf: data)
            }
        }

        writeStderr(
            "capturing \(label) → stdout (f32le \(AudioFormat.sampleRate) Hz x \(AudioFormat.channelCount))\n"
        )
        let oneSec: UInt64 = 1_000_000_000
        var ticks: UInt64 = 0
        while true {
            try await Task.sleep(nanoseconds: oneSec * Diagnostics.heartbeatSeconds)
            ticks += Diagnostics.heartbeatSeconds
            writeStderr("[heartbeat] \(ticks)s frames=\(frameCount) bytes=\(totalBytes)\n")
        }
    }

    func stream(
        _ stream: SCStream,
        didOutputSampleBuffer sampleBuffer: CMSampleBuffer,
        of outputType: SCStreamOutputType
    ) {
        guard outputType == .audio else { return }
        frameCount += 1
        guard sampleBuffer.dataReadiness == .ready else { return }
        checkFormat(sampleBuffer)
        writeAudio(sampleBuffer)
    }

    // Validates the ASBD on the first frame and sets up an AVAudioConverter if the
    // native sample rate differs from the wire contract. Fatal if format or channel
    // count is incompatible.
    private func checkFormat(_ sampleBuffer: CMSampleBuffer) {
        guard !formatChecked,
              let fmtDesc = CMSampleBufferGetFormatDescription(sampleBuffer),
              let asbdPtr = CMAudioFormatDescriptionGetStreamBasicDescription(fmtDesc)
        else { return }
        formatChecked = true
        let asbd = asbdPtr.pointee

        let isFloat = (asbd.mFormatFlags & kAudioFormatFlagIsFloat) != 0
        let isNonInterleaved = (asbd.mFormatFlags & kAudioFormatFlagIsNonInterleaved) != 0
        writeStderr(
            "[asbd] rate=\(asbd.mSampleRate) ch=\(asbd.mChannelsPerFrame)"
            + " bpc=\(asbd.mBitsPerChannel) flags=0x\(String(asbd.mFormatFlags, radix: 16))"
            + " bpf=\(asbd.mBytesPerFrame) isFloat=\(isFloat) nonInterleaved=\(isNonInterleaved)\n"
        )

        guard isFloat else {
            writeStderr("[fatal] SCK delivered non-float audio — cannot emit f32le wire contract\n")
            exit(ExitCode.failure)
        }
        guard asbd.mChannelsPerFrame == UInt32(AudioFormat.channelCount) else {
            writeStderr(
                "[fatal] channel mismatch: expected \(AudioFormat.channelCount),"
                + " got \(asbd.mChannelsPerFrame)\n"
            )
            exit(ExitCode.failure)
        }

        if asbd.mSampleRate != Double(AudioFormat.sampleRate) {
            writeStderr(
                "[warn] rate mismatch SCK=\(asbd.mSampleRate) contract=\(AudioFormat.sampleRate);"
                + " resampling via AVAudioConverter\n"
            )
            var mutableASBD = asbd
            guard let src = AVAudioFormat(streamDescription: &mutableASBD),
                  let dst = AVAudioFormat(
                      commonFormat: .pcmFormatFloat32,
                      sampleRate: Double(AudioFormat.sampleRate),
                      channels: AVAudioChannelCount(AudioFormat.channelCount),
                      interleaved: true
                  ),
                  let conv = AVAudioConverter(from: src, to: dst)
            else {
                writeStderr("[fatal] could not create AVAudioConverter for resampling\n")
                exit(ExitCode.failure)
            }
            converter = conv
        } else {
            writeStderr(
                "[ok] wire contract confirmed: f32le \(AudioFormat.sampleRate) Hz"
                + " x \(AudioFormat.channelCount) ch interleaved\n"
            )
        }
    }

    private func writeAudio(_ sampleBuffer: CMSampleBuffer) {
        var ablSize = 0
        _ = CMSampleBufferGetAudioBufferListWithRetainedBlockBuffer(
            sampleBuffer, bufferListSizeNeededOut: &ablSize,
            bufferListOut: nil, bufferListSize: 0,
            blockBufferAllocator: nil, blockBufferMemoryAllocator: nil,
            flags: 0, blockBufferOut: nil
        )
        guard ablSize > 0 else { return }

        let ablMem = UnsafeMutableRawPointer.allocate(
            byteCount: ablSize, alignment: MemoryLayout<AudioBufferList>.alignment)
        defer { ablMem.deallocate() }
        var retainedBB: CMBlockBuffer?
        let status = CMSampleBufferGetAudioBufferListWithRetainedBlockBuffer(
            sampleBuffer, bufferListSizeNeededOut: nil,
            bufferListOut: ablMem.assumingMemoryBound(to: AudioBufferList.self),
            bufferListSize: ablSize,
            blockBufferAllocator: nil, blockBufferMemoryAllocator: nil,
            flags: 0, blockBufferOut: &retainedBB
        )
        guard status == noErr else { return }

        let abl = UnsafeMutableAudioBufferListPointer(
            ablMem.assumingMemoryBound(to: AudioBufferList.self))

        let data: Data?
        if let conv = converter {
            data = resample(abl: abl, conv: conv)
        } else if abl.count == 1 {
            let buf = abl[0]
            data = Data(bytes: buf.mData!, count: Int(buf.mDataByteSize))
        } else {
            data = interleave(abl: abl)
        }

        guard let data else { return }
        totalBytes += data.count
        if frameCount % Diagnostics.frameLogInterval == 1 {
            writeStderr("[diag] frame \(frameCount): \(data.count) B (total \(totalBytes) B)\n")
        }
        writeQueue.async {
            do { try FileHandle.standardOutput.write(contentsOf: data) }
            catch { exit(ExitCode.success) }
        }
    }

    private func interleave(abl: UnsafeMutableAudioBufferListPointer) -> Data {
        let numChannels = abl.count
        let numSamples = Int(abl[0].mDataByteSize) / MemoryLayout<Float32>.size
        var out = [Float32](repeating: 0, count: numSamples * numChannels)
        for ch in 0..<numChannels {
            let src = abl[ch].mData!.assumingMemoryBound(to: Float32.self)
            for i in 0..<numSamples {
                out[i * numChannels + ch] = src[i]
            }
        }
        return out.withUnsafeBytes { Data($0) }
    }

    // Resamples a frame's worth of audio from the native SCK rate to AudioFormat.sampleRate.
    // Output format is interleaved f32le; floatChannelData[0] contains all samples.
    private func resample(abl: UnsafeMutableAudioBufferListPointer, conv: AVAudioConverter) -> Data? {
        let srcFormat = conv.inputFormat
        let inputFrames = Int(abl[0].mDataByteSize) / MemoryLayout<Float32>.size
        guard let inBuf = AVAudioPCMBuffer(
            pcmFormat: srcFormat, frameCapacity: AVAudioFrameCount(inputFrames))
        else { return nil }
        inBuf.frameLength = AVAudioFrameCount(inputFrames)

        if let planes = inBuf.floatChannelData {
            for ch in 0..<Int(srcFormat.channelCount) {
                let src = abl[ch].mData!.assumingMemoryBound(to: Float32.self)
                planes[ch].update(from: src, count: inputFrames)
            }
        }

        let outCapacity = AVAudioFrameCount(
            Double(inputFrames) * conv.outputFormat.sampleRate / conv.inputFormat.sampleRate + 64
        )
        guard let outBuf = AVAudioPCMBuffer(
            pcmFormat: conv.outputFormat, frameCapacity: outCapacity)
        else { return nil }

        var inputGiven = false
        var convError: NSError?
        let result = conv.convert(to: outBuf, error: &convError) { _, status in
            if inputGiven { status.pointee = .noDataNow; return nil }
            inputGiven = true
            status.pointee = .haveData
            return inBuf
        }

        guard result != .error, convError == nil,
              let floatData = outBuf.floatChannelData
        else {
            if let err = convError {
                writeStderr("[warn] resample error: \(err.localizedDescription)\n")
            }
            return nil
        }

        let byteCount = Int(outBuf.frameLength) * AudioFormat.channelCount * MemoryLayout<Float32>.size
        return Data(bytes: floatData[0], count: byteCount)
    }

    func stream(_ stream: SCStream, didStopWithError error: Error) {
        writeStderr("stream stopped: \(error)\n")
        exit(ExitCode.failure)
    }
}
