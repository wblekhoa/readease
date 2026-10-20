import Foundation

@main struct TranslationTests {
    static func reject(_ operation: () throws -> Void) {
        do { try operation(); fatalError("Expected rejection") } catch {}
    }
    static func request(_ input: [String: Any]) -> [String: Any] {
        let data = try! JSONSerialization.data(withJSONObject: input)
        return String(decoding: data, as: UTF8.self).withCString { raw in
            let result = translationRequest(raw)!
            defer { translationFree(result) }
            return try! JSONSerialization.jsonObject(with: Data(String(cString: result).utf8)) as! [String: Any]
        }
    }
    static func local(_ model: String, _ generation: Int) -> [String: Any] {
        request(["action":"translate", "provider":"ollama", "model":model, "text":"Xin chào", "source":"vi", "target":"en", "generation":generation])
    }
    static func main() async throws {
        try await Task.detached { try await runTests() }.value
    }
    static func runTests() async throws {
        assert(try! localBase("ollama") == "http://127.0.0.1:11434/v1")
        assert(try! localBase("lmstudio") == "http://127.0.0.1:1234/v1")
        reject { _ = try localBase("https://example.com") }
        // RE-PLAY-031: ReadEase's own server, on the host's loopback port only.
        assert(try! localBase("readease", port: 18000) == "http://127.0.0.1:18000/v1")
        reject { _ = try localBase("readease") }
        reject { _ = try localBase("readease", port: 80) }
        assert(try! cleanTranslation("<think>Reasoning</think>\nHello") == "Hello")
        reject { _ = try cleanTranslation("<think>unfinished") }
        reject { _ = try cleanTranslation(" \n ") }
        reject { _ = try cleanTranslation(String(repeating: "a", count: 24001)) }
        assert(request(["action":"status", "provider":"apple", "source":"en", "target":"en"])["installed"] as? Bool == true)
        cancelBefore(20)
        assert(request(["action":"translate", "provider":"apple", "text":"Xin chào", "source":"vi", "target":"en", "generation":19])["error"] as? String == "cancelled")
        assert(request(["action":"translate", "provider":"apple", "text":String(repeating:"a",count:6001), "target":"en", "generation":20])["error"] as? String == "text_limit")
        assert(request(["action":"translate", "provider":"apple", "text":"Hello world.", "source":"en", "target":"en", "generation":21])["text"] as? String == "Hello world.")
        print("PASS translation validation, output cleanup, same-language, cancelled-before-registration")
        if CommandLine.arguments.contains("--apple") {
            let start = Date()
            let vi = request(["action":"translate", "provider":"apple", "text":"Đọc sách mỗi ngày giúp chúng ta hiểu thế giới tốt hơn.", "source":"vi", "target":"en", "generation":22])
            guard let english = vi["text"] as? String, english.contains("read") || english.contains("Reading") else { fatalError("Apple translation failed: \(vi)") }
            let en = request(["action":"translate", "provider":"apple", "text":"I would like to read this book in Vietnamese.", "source":"en", "target":"vi", "generation":23])
            guard let vietnamese = en["text"] as? String, vietnamese.contains("Việt") else { fatalError("Apple reverse translation failed: \(en)") }
            print("PASS Apple VI→EN + EN→VI through production bridge, \(Date().timeIntervalSince(start))s")
        }
        if let raw = ProcessInfo.processInfo.environment["READEASE_TRANSLATOR_PORT"], let port = Int(raw) {
            let start = Date()
            let vi = request(["action":"translate", "provider":"readease", "port":port, "text":"Reading every day helps us understand the world better.", "source":"en", "target":"vi", "generation":40])
            guard let vietnamese = vi["text"] as? String, vietnamese.contains("đọc") else { fatalError("ReadEase EN→VI failed: \(vi)") }
            let en = request(["action":"translate", "provider":"readease", "port":port, "text":"Đọc sách mỗi ngày giúp chúng ta hiểu thế giới tốt hơn.", "source":"vi", "target":"en", "generation":41])
            guard let english = en["text"] as? String, english.lowercased().contains("read") else { fatalError("ReadEase VI→EN failed: \(en)") }
            print("PASS ReadEase translator EN→VI + VI→EN through production bridge, \(Date().timeIntervalSince(start))s")
        }
        if CommandLine.arguments.contains("--fixture") {
            let models = request(["action":"models", "provider":"ollama"])
            assert(models["models"] as? [String] == ["fixture-local"])
            assert(local("fixture-local",30)["text"] as? String == "Hello")
            assert(local("cloud-alias",30)["error"] as? String == "model_missing")
            assert(local("truncated",31)["error"] as? String == "invalid_output")
            assert(local("redirect",32)["error"] as? String == "local_unavailable")
            let job = Task.detached { local("slow", 33) }
            try await Task.sleep(nanoseconds: 300_000_000)
            cancelBefore(34)
            let result = await job.value
            assert(result["error"] as? String == "cancelled")
            print("PASS local protocol, no cloud model list, incomplete output, redirect rejection, in-flight cancellation")
        }
    }
}
