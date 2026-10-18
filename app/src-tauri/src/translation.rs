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
    #[test]
    fn cancelled_generation_never_translates() {
        cancel_before(10);
        let options = Options { provider:"apple".into(), source:"vi".into(), target:"en".into(), model:String::new(), voice_id:"af_heart".into() };
        assert_eq!(translate("Xin chào", &options, 9).unwrap_err(), "translation:cancelled");
    }
}
