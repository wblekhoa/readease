//! Translation work stays off the UI and Python audio worker. Native requests
//! carry the selection generation, so Stop/new selection also cancels IO.
use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use std::ffi::{CStr, CString};

extern "C" {
    fn re_translation_request(input: *const std::ffi::c_char) -> *mut std::ffi::c_char;
    fn re_translation_free(output: *mut std::ffi::c_char);
    fn re_translation_cancel_before(generation: u64);
}

#[derive(Clone, Deserialize, Serialize)]
pub(crate) struct Options {
    pub provider: String,
    pub source: String,
    pub target: String,
    pub model: String,
    pub voice_id: String,
}
impl Options {
    pub fn validate(&self) -> Result<(), String> {
        if !["apple", "ollama", "lmstudio"].contains(&self.provider.as_str()) {
            return Err("translation:provider".into());
        }
        if !["auto", "vi", "en"].contains(&self.source.as_str()) || !["vi", "en"].contains(&self.target.as_str()) {
            return Err("translation:language".into());
        }
        if self.voice_id.is_empty() || self.voice_id.starts_with("openai:") || self.voice_id.starts_with("elevenlabs:") {
            return Err("translation:voice_missing".into());
        }
        Ok(())
    }
}

pub(crate) fn cancel_before(generation: u64) { unsafe { re_translation_cancel_before(generation) } }

fn request(value: Value) -> Result<Value, String> {
    let input = CString::new(value.to_string()).map_err(|_| "translation:invalid_request")?;
    let raw = unsafe { re_translation_request(input.as_ptr()) };
    if raw.is_null() { return Err("translation:failed".into()); }
    let output = unsafe { CStr::from_ptr(raw).to_string_lossy().into_owned() };
    unsafe { re_translation_free(raw) };
    let result: Value = serde_json::from_str(&output).map_err(|_| "translation:invalid_output")?;
    if let Some(error) = result["error"].as_str() { return Err(format!("translation:{error}")); }
    Ok(result)
}

pub(crate) fn translate(text: &str, options: &Options, generation: u64) -> Result<Value, String> {
    options.validate()?;
    request(json!({"action":"translate", "provider":options.provider, "source":options.source,
        "target":options.target, "model":options.model, "text":text, "generation":generation}))
}

/// RE-PLAY-029: a pasted text longer than one native request (6,000 Swift
/// characters) is translated in pieces cut at paragraph, then sentence,
/// then word boundaries - never inside a word - and joined back in order.
pub(crate) const PIECE_CHARS: usize = 5_000;

pub(crate) fn pieces(text: &str, limit: usize) -> Vec<String> {
    let mut out: Vec<String> = Vec::new();
    let mut current = String::new();
    let push = |current: &mut String, out: &mut Vec<String>| {
        if !current.trim().is_empty() { out.push(current.trim().to_string()); }
        current.clear();
    };
    for paragraph in text.split("\n\n") {
        let paragraph = paragraph.trim();
        if paragraph.is_empty() { continue; }
        if paragraph.chars().count() > limit {
            push(&mut current, &mut out);
            // Sentences, then words, so no piece exceeds the limit.
            let mut sentence_buf = String::new();
            for word in paragraph.split_inclusive(|c: char| c.is_whitespace()) {
                if sentence_buf.chars().count() + word.chars().count() > limit {
                    let cut = sentence_buf.rfind(|c| c == '.' || c == '!' || c == '?' || c == '…')
                        .filter(|&at| at + 1 < sentence_buf.len() && sentence_buf[..at].chars().count() > limit / 2);
                    match cut {
                        Some(at) => {
                            let rest = sentence_buf[at + 1..].to_string();
                            sentence_buf.truncate(at + 1);
                            push(&mut sentence_buf, &mut out);
                            sentence_buf.push_str(rest.trim_start());
                        }
                        None => push(&mut sentence_buf, &mut out),
                    }
                }
                sentence_buf.push_str(word);
            }
            push(&mut sentence_buf, &mut out);
            continue;
        }
        let joined = if current.is_empty() { 0 } else { current.chars().count() + 2 };
        if joined + paragraph.chars().count() > limit { push(&mut current, &mut out); }
        if !current.is_empty() { current.push_str("\n\n"); }
        current.push_str(paragraph);
    }
    push(&mut current, &mut out);
    out
}

/// Translate a whole text piece by piece under one generation; a newer
/// generation (Stop, a new reading) cancels the rest.
pub(crate) fn translate_long(text: &str, options: &Options, generation: u64) -> Result<String, String> {
    let mut translated = Vec::new();
    for piece in pieces(text, PIECE_CHARS) {
        let result = translate(&piece, options, generation)?;
        translated.push(result["text"].as_str().ok_or("translation:invalid_output")?.to_string());
    }
    if translated.is_empty() { return Err("translation:invalid_output".into()); }
    Ok(translated.join("\n\n"))
}

#[tauri::command(async)]
pub(crate) fn translation_status(source: String, target: String) -> Result<Value, String> {
    request(json!({"action":"status", "provider":"apple", "source":source, "target":target}))
}
#[tauri::command(async)]
pub(crate) fn translation_models(provider: String) -> Result<Value, String> {
    if !["ollama", "lmstudio"].contains(&provider.as_str()) { return Err("translation:provider".into()); }
    request(json!({"action":"models", "provider":provider}))
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn rejects_paid_voices_remote_providers_and_invalid_languages() {
        let mut options = Options { provider:"apple".into(), source:"auto".into(), target:"en".into(), model:String::new(), voice_id:"af_heart".into() };
        assert!(options.validate().is_ok());
        options.voice_id = "openai:alloy".into();
        assert!(options.validate().is_err());
        options.voice_id = "af_heart".into(); options.provider = "https://remote.invalid".into();
        assert!(options.validate().is_err());
        options.provider = "apple".into(); options.target = "unknown".into();
        assert!(options.validate().is_err());
    }
    // RE-PLAY-029
    #[test]
    fn long_text_splits_at_paragraphs_and_never_over_the_limit() {
        let para = "Một câu ngắn. ".repeat(30);
        let text = format!("{para}\n\n{para}\n\n{para}");
        let parts = pieces(&text, 1_000);
        assert!(parts.len() >= 2);
        assert!(parts.iter().all(|p| p.chars().count() <= 1_000), "{:?}", parts.iter().map(|p| p.chars().count()).collect::<Vec<_>>());
        let rejoined: String = parts.join(" ").split_whitespace().collect::<Vec<_>>().join(" ");
        assert_eq!(rejoined, text.split_whitespace().collect::<Vec<_>>().join(" "));
        // A short text is one piece; empty paragraphs vanish.
        assert_eq!(pieces("Xin chào.\n\n\n\nTạm biệt.", 5_000), vec!["Xin chào.\n\nTạm biệt."]);
        // One huge paragraph is cut between words, every piece within the limit.
        let huge = "chữ ".repeat(4_000);
        assert!(pieces(&huge, 5_000).iter().all(|p| p.chars().count() <= 5_000 && !p.starts_with(' ')));
    }
    #[test]
    fn cancelled_generation_never_translates() {
        cancel_before(10);
        let options = Options { provider:"apple".into(), source:"vi".into(), target:"en".into(), model:String::new(), voice_id:"af_heart".into() };
        assert_eq!(translate("Xin chào", &options, 9).unwrap_err(), "translation:cancelled");
    }
}
