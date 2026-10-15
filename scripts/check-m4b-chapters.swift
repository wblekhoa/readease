// Reads an audiobook the way QuickTime and Apple Books do (AVFoundation) and
// prints its length, chapters and tags - the check behind RE-PLAY-020 that
// the Python tests cannot make. Developer tool; never shipped.
//
//   swiftc -parse-as-library -O scripts/check-m4b-chapters.swift -o /tmp/check-m4b
//   /tmp/check-m4b "Book.m4b"
import AVFoundation
@main struct Check { static func main() async throws {
  setvbuf(stdout, nil, _IONBF, 0)
  let a = AVURLAsset(url: URL(fileURLWithPath: CommandLine.arguments[1]))
  print("duration", try await a.load(.duration).seconds, "playable", try await a.load(.isPlayable))
  let groups = try await a.loadChapterMetadataGroups(bestMatchingPreferredLanguages: ["vi", "en", "und"])
  for g in groups { print(String(format: "  %.2f-%.2f ", g.timeRange.start.seconds, g.timeRange.end.seconds) + (try await g.items.first?.load(.stringValue) ?? "?")) }
  for item in try await a.load(.commonMetadata) { print("  tag", item.commonKey?.rawValue ?? "?", (try? await item.load(.stringValue)) ?? "(data)") }
}}
