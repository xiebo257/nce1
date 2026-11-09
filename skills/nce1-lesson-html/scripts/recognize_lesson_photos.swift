// Local, offline OCR of textbook photographs with original pixel coordinates.
// Compile: swiftc -O recognize_lesson_photos.swift -o /path/to/photo-ocr
// Run: photo-ocr OUTPUT_DIRECTORY IMAGE...
import Foundation
import Vision
import ImageIO

let arguments = Array(CommandLine.arguments.dropFirst())
guard arguments.count >= 2 else {
    fputs("Usage: photo-ocr OUTPUT_DIRECTORY IMAGE...\n", stderr)
    exit(2)
}
let output = URL(fileURLWithPath: arguments[0], isDirectory: true)
try FileManager.default.createDirectory(at: output, withIntermediateDirectories: true)
var failures = 0
for path in arguments.dropFirst() {
    autoreleasepool {
        do {
            let url = URL(fileURLWithPath: path)
            guard let source = CGImageSourceCreateWithURL(url as CFURL, nil),
                  let image = CGImageSourceCreateImageAtIndex(source, 0, nil) else {
                throw NSError(domain: "PhotoOCR", code: 1)
            }
            let request = VNRecognizeTextRequest()
            request.recognitionLevel = .accurate
            request.recognitionLanguages = ["en-US", "zh-Hans"]
            request.usesLanguageCorrection = false
            try VNImageRequestHandler(cgImage: image).perform([request])
            let lines: [[String: Any]] = (request.results ?? []).compactMap { item in
                guard let text = item.topCandidates(1).first else { return nil }
                let b = item.boundingBox
                return ["text": text.string, "confidence": text.confidence,
                        "box": [b.minX * Double(image.width), (1 - b.maxY) * Double(image.height),
                                b.maxX * Double(image.width), (1 - b.minY) * Double(image.height)]]
            }
            let record: [String: Any] = ["source": path, "engine": "Apple Vision accurate",
                "coordinate_space": [image.width, image.height],
                "reading_order": "unresolved; reconstruct from coordinates and inspect source photo",
                "lines": lines]
            let destination = output.appendingPathComponent(url.deletingPathExtension().lastPathComponent + ".json")
            try JSONSerialization.data(withJSONObject: record, options: [.prettyPrinted, .sortedKeys])
                .write(to: destination, options: .atomic)
            print("RECOGNIZED \(path) \(lines.count) lines")
            fflush(stdout)
        } catch {
            failures += 1
            fputs("FAILED \(path): \(error)\n", stderr)
        }
    }
}
exit(failures == 0 ? 0 : 1)
