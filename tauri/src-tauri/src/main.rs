use serde::Serialize;
use serde_json::{json, Value};
use std::ffi::OsStr;
use std::fs;
use std::io::Write;
use std::path::{Path, PathBuf};
use std::process::{Command, Stdio};

#[derive(Serialize)]
#[serde(rename_all = "camelCase")]
struct AppSnapshot {
    running: bool,
    model_runtime_state: String,
    model_installed: bool,
    model_size_label: String,
    model_snapshot: String,
    history_count: usize,
    speech_root: String,
    ai_mode: String,
    ai_runtime_state: String,
    ai_model_installed: bool,
    ai_model_size_label: String,
}

#[derive(Serialize)]
#[serde(rename_all = "camelCase")]
struct HistoryItem {
    id: String,
    created_at: String,
    text: String,
    original_text: String,
    processing_mode: String,
    processing_status: String,
    processing_ms: u64,
}

#[tauri::command]
fn app_snapshot() -> Result<AppSnapshot, String> {
    let status = speech_status().unwrap_or_default();
    let root = speech_root();
    let (model_installed, model_snapshot, model_size_label) = model_status(&root);
    let running = status.contains("speech_app run");
    let model_runtime_state = if running {
        read_model_runtime_state(&root)
    } else {
        "stopped".to_string()
    };
    let history = read_history(usize::MAX)?;
    let settings = read_settings(&root);
    let ai_mode = settings["ai_mode"].as_str().unwrap_or("off").to_string();
    let ai_runtime_state = if running {
        read_runtime_field(&root, "ai_state", "unknown")
    } else {
        "stopped".to_string()
    };
    let (ai_model_installed, ai_model_size_label) = ai_model_status(&root);

    Ok(AppSnapshot {
        running,
        model_runtime_state,
        model_installed,
        model_size_label,
        model_snapshot,
        history_count: history.len(),
        speech_root: root.display().to_string(),
        ai_mode,
        ai_runtime_state,
        ai_model_installed,
        ai_model_size_label,
    })
}

fn read_model_runtime_state(root: &Path) -> String {
    read_runtime_field(root, "model_state", "unknown")
}

fn read_runtime_field(root: &Path, field: &str, fallback: &str) -> String {
    let path = root.join("data").join("runtime_state.json");
    let Ok(content) = fs::read_to_string(path) else {
        return fallback.to_string();
    };
    let Ok(value) = serde_json::from_str::<Value>(&content) else {
        return fallback.to_string();
    };
    value[field]
        .as_str()
        .filter(|state| !state.trim().is_empty())
        .unwrap_or(fallback)
        .to_string()
}

#[tauri::command]
fn speech_status() -> Result<String, String> {
    run_speech(["status"])
}

#[tauri::command]
fn speech_diagnose() -> Result<String, String> {
    run_speech(["diagnose"])
}

#[tauri::command]
fn speech_restart() -> Result<String, String> {
    run_speech(["restart"])
}

#[tauri::command]
fn speech_stop() -> Result<String, String> {
    run_speech(["stop"])
}

#[tauri::command]
fn recent_history(limit: usize) -> Result<Vec<HistoryItem>, String> {
    read_history(limit)
}

#[tauri::command]
fn app_settings() -> Result<Value, String> {
    let settings = read_settings(&speech_root());
    Ok(json!({
        "aiMode": settings["ai_mode"].as_str().unwrap_or("off"),
        "aiProfile": settings["ai_profile"].as_str().unwrap_or("clean"),
        "aiGlossary": settings["ai_glossary"].as_str().unwrap_or(""),
        "aiLocalModelId": settings["ai_local_model_id"].as_str().unwrap_or("ai-forever/sage-fredt5-distilled-95m"),
        "aiApiBaseUrl": settings["ai_api_base_url"].as_str().unwrap_or("https://api.openai.com/v1"),
        "aiApiModel": settings["ai_api_model"].as_str().unwrap_or(""),
        "aiTimeoutSeconds": settings["ai_timeout_seconds"].as_f64().unwrap_or(12.0),
    }))
}

#[tauri::command]
fn save_app_settings(payload: Value) -> Result<(), String> {
    let root = speech_root();
    let path = root.join("data").join("settings.json");
    let mut settings = read_settings(&root);
    let object = settings
        .as_object_mut()
        .ok_or_else(|| "Settings file is not a JSON object".to_string())?;

    let mappings = [
        ("aiMode", "ai_mode"),
        ("aiProfile", "ai_profile"),
        ("aiGlossary", "ai_glossary"),
        ("aiLocalModelId", "ai_local_model_id"),
        ("aiApiBaseUrl", "ai_api_base_url"),
        ("aiApiModel", "ai_api_model"),
        ("aiTimeoutSeconds", "ai_timeout_seconds"),
    ];
    for (frontend, disk) in mappings {
        if let Some(value) = payload.get(frontend) {
            object.insert(disk.to_string(), value.clone());
        }
    }
    if !matches!(object.get("ai_mode").and_then(Value::as_str), Some("off" | "local" | "api")) {
        return Err("AI mode must be off, local, or api".to_string());
    }
    if !matches!(object.get("ai_profile").and_then(Value::as_str), Some("clean" | "refine")) {
        return Err("AI profile must be clean or refine".to_string());
    }
    if object.get("ai_mode").and_then(Value::as_str) != Some("api")
        && object.get("ai_profile").and_then(Value::as_str) == Some("refine")
    {
        object.insert("ai_profile".to_string(), Value::String("clean".to_string()));
    }
    fs::create_dir_all(path.parent().unwrap()).map_err(|error| error.to_string())?;
    let serialized = serde_json::to_string_pretty(&settings).map_err(|error| error.to_string())?;
    fs::write(path, serialized).map_err(|error| error.to_string())
}

#[tauri::command]
fn speech_ai_install() -> Result<String, String> {
    run_speech(["ai", "install"])
}

#[tauri::command]
fn speech_set_api_key(api_key: String) -> Result<String, String> {
    let value = api_key.trim();
    if value.is_empty() {
        return Err("API key cannot be empty".to_string());
    }
    run_speech_with_stdin(&["ai", "key", "set", "--stdin"], value)
}

#[tauri::command]
fn speech_delete_api_key() -> Result<String, String> {
    run_speech(["ai", "key", "delete"])
}

fn main() {
    tauri::Builder::default()
        .invoke_handler(tauri::generate_handler![
            app_snapshot,
            speech_status,
            speech_diagnose,
            speech_restart,
            speech_stop,
            recent_history,
            app_settings,
            save_app_settings,
            speech_ai_install,
            speech_set_api_key,
            speech_delete_api_key
        ])
        .run(tauri::generate_context!())
        .expect("error while running Speech Tauri app");
}

fn speech_root() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR"))
        .parent()
        .and_then(Path::parent)
        .map(Path::to_path_buf)
        .unwrap_or_else(|| PathBuf::from(r"D:\Speech"))
}

fn run_speech<I, S>(args: I) -> Result<String, String>
where
    I: IntoIterator<Item = S>,
    S: AsRef<OsStr>,
{
    let mut command = speech_command();
    let output = command
        .args(args)
        .output()
        .map_err(|error| error.to_string())?;

    let stdout = String::from_utf8_lossy(&output.stdout);
    let stderr = String::from_utf8_lossy(&output.stderr);
    let combined = format!("{}{}", stdout, stderr);

    if output.status.success() {
        Ok(combined)
    } else {
        Err(combined)
    }
}

fn run_speech_with_stdin(args: &[&str], stdin_value: &str) -> Result<String, String> {
    let mut child = speech_command()
        .args(args)
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .map_err(|error| error.to_string())?;
    child
        .stdin
        .as_mut()
        .ok_or_else(|| "Could not open secure input pipe".to_string())?
        .write_all(stdin_value.as_bytes())
        .map_err(|error| error.to_string())?;
    let output = child.wait_with_output().map_err(|error| error.to_string())?;
    let combined = format!(
        "{}{}",
        String::from_utf8_lossy(&output.stdout),
        String::from_utf8_lossy(&output.stderr)
    );
    if output.status.success() {
        Ok(combined)
    } else {
        Err(combined)
    }
}

fn speech_command() -> Command {
    #[cfg(target_os = "windows")]
    {
        let mut command = Command::new("cmd");
        command.arg("/C").arg(speech_root().join("bin").join("speech.cmd"));
        command
    }
    #[cfg(not(target_os = "windows"))]
    {
        Command::new(speech_root().join("bin").join("speech"))
    }
}

fn model_status(root: &Path) -> (bool, String, String) {
    let snapshots = root
        .join("models")
        .join("huggingface")
        .join("hub")
        .join("models--nvidia--parakeet-tdt-0.6b-v3")
        .join("snapshots");

    let Ok(entries) = fs::read_dir(snapshots) else {
        return (false, String::new(), "Not installed".to_string());
    };

    let snapshot = entries
        .filter_map(Result::ok)
        .find(|entry| entry.path().is_dir());

    let Some(snapshot) = snapshot else {
        return (false, String::new(), "Not installed".to_string());
    };

    let bytes = dir_size(&snapshot.path());
    let gb = bytes as f64 / 1024.0 / 1024.0 / 1024.0;
    (
        true,
        snapshot.file_name().to_string_lossy().to_string(),
        format!("{gb:.2} GB"),
    )
}

fn ai_model_status(root: &Path) -> (bool, String) {
    let snapshots = root
        .join("models")
        .join("huggingface")
        .join("hub")
        .join("models--ai-forever--sage-fredt5-distilled-95m")
        .join("snapshots");
    let Ok(entries) = fs::read_dir(snapshots) else {
        return (false, "Not installed".to_string());
    };
    let Some(snapshot) = entries.filter_map(Result::ok).find(|entry| entry.path().is_dir()) else {
        return (false, "Not installed".to_string());
    };
    let mb = dir_size(&snapshot.path()) as f64 / 1024.0 / 1024.0;
    (true, format!("{mb:.0} MB"))
}

fn read_settings(root: &Path) -> Value {
    let path = root.join("data").join("settings.json");
    let content = fs::read_to_string(path).unwrap_or_else(|_| "{}".to_string());
    serde_json::from_str(&content).unwrap_or_else(|_| json!({}))
}

fn dir_size(path: &Path) -> u64 {
    let Ok(entries) = fs::read_dir(path) else {
        return 0;
    };

    entries
        .filter_map(Result::ok)
        .map(|entry| {
            let path = entry.path();
            if path.is_dir() {
                dir_size(&path)
            } else {
                entry.metadata().map(|metadata| metadata.len()).unwrap_or(0)
            }
        })
        .sum()
}

fn read_history(limit: usize) -> Result<Vec<HistoryItem>, String> {
    let path = speech_root().join("data").join("history.jsonl");
    let content = match fs::read_to_string(path) {
        Ok(value) => value,
        Err(error) if error.kind() == std::io::ErrorKind::NotFound => return Ok(Vec::new()),
        Err(error) => return Err(error.to_string()),
    };

    let mut rows = Vec::new();
    for line in content.lines().take(limit) {
        let Ok(value) = serde_json::from_str::<Value>(line) else {
            continue;
        };
        rows.push(HistoryItem {
            id: value["id"].as_str().unwrap_or_default().to_string(),
            created_at: value["created_at"].as_str().unwrap_or_default().to_string(),
            text: value["text"].as_str().unwrap_or_default().to_string(),
            original_text: value["original_text"]
                .as_str()
                .unwrap_or_else(|| value["text"].as_str().unwrap_or_default())
                .to_string(),
            processing_mode: value["processing_mode"].as_str().unwrap_or("off").to_string(),
            processing_status: value["processing_status"].as_str().unwrap_or("skipped").to_string(),
            processing_ms: value["processing_ms"].as_u64().unwrap_or(0),
        });
    }
    Ok(rows)
}
