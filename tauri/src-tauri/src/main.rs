use serde::Serialize;
use serde_json::Value;
use std::ffi::OsStr;
use std::fs;
use std::path::{Path, PathBuf};
use std::process::Command;

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
}

#[derive(Serialize)]
#[serde(rename_all = "camelCase")]
struct HistoryItem {
    id: String,
    created_at: String,
    text: String,
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

    Ok(AppSnapshot {
        running,
        model_runtime_state,
        model_installed,
        model_size_label,
        model_snapshot,
        history_count: history.len(),
        speech_root: root.display().to_string(),
    })
}

fn read_model_runtime_state(root: &Path) -> String {
    let path = root.join("data").join("runtime_state.json");
    let Ok(content) = fs::read_to_string(path) else {
        return "unknown".to_string();
    };
    let Ok(value) = serde_json::from_str::<Value>(&content) else {
        return "unknown".to_string();
    };
    value["model_state"]
        .as_str()
        .filter(|state| !state.trim().is_empty())
        .unwrap_or("unknown")
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

fn main() {
    tauri::Builder::default()
        .invoke_handler(tauri::generate_handler![
            app_snapshot,
            speech_status,
            speech_diagnose,
            speech_restart,
            speech_stop,
            recent_history
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
    let command = speech_root().join("bin").join("speech.cmd");
    let output = Command::new("cmd")
        .arg("/C")
        .arg(command)
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
        });
    }
    Ok(rows)
}
