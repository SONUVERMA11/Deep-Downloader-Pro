use serde::{Deserialize, Serialize};
use std::process::{Child, Command};
use std::sync::Mutex;
use tauri::{Manager, State};

// ──────────────────────────────────────────────
// State: Python backend process handle
// ──────────────────────────────────────────────
struct BackendProcess(Mutex<Option<Child>>);

// ──────────────────────────────────────────────
// IPC Types
// ──────────────────────────────────────────────
#[derive(Debug, Serialize, Deserialize)]
pub struct AnalyzeRequest {
    pub url: String,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct AnalyzeResponse {
    pub success: bool,
    pub data: serde_json::Value,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct DownloadRequest {
    pub url: String,
    pub format_id: Option<String>,
    pub output_path: Option<String>,
    pub quality: Option<String>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct ApiResponse {
    pub success: bool,
    pub message: String,
    pub data: Option<serde_json::Value>,
}

// ──────────────────────────────────────────────
// Backend Communication Helper
// ──────────────────────────────────────────────
const BACKEND_URL: &str = "http://127.0.0.1:18920";

async fn api_get(path: &str) -> Result<serde_json::Value, String> {
    let url = format!("{}{}", BACKEND_URL, path);
    let client = reqwest::Client::new();
    let resp = client
        .get(&url)
        .send()
        .await
        .map_err(|e| format!("Backend request failed: {}", e))?;
    let json: serde_json::Value = resp
        .json()
        .await
        .map_err(|e| format!("Failed to parse response: {}", e))?;
    Ok(json)
}

async fn api_post(path: &str, body: &serde_json::Value) -> Result<serde_json::Value, String> {
    let url = format!("{}{}", BACKEND_URL, path);
    let client = reqwest::Client::new();
    let resp = client
        .post(&url)
        .json(body)
        .send()
        .await
        .map_err(|e| format!("Backend request failed: {}", e))?;
    let json: serde_json::Value = resp
        .json()
        .await
        .map_err(|e| format!("Failed to parse response: {}", e))?;
    Ok(json)
}

// ──────────────────────────────────────────────
// Tauri Commands — IPC Bridge
// ──────────────────────────────────────────────

/// Analyze a URL and return available formats/metadata
#[tauri::command]
async fn analyze_url(url: String) -> Result<serde_json::Value, String> {
    let body = serde_json::json!({ "url": url });
    api_post("/api/analyze", &body).await
}

/// Start a download with selected format options
#[tauri::command]
async fn start_download(request: DownloadRequest) -> Result<serde_json::Value, String> {
    let body = serde_json::to_value(&request).map_err(|e| e.to_string())?;
    api_post("/api/download", &body).await
}

/// Pause a download by ID
#[tauri::command]
async fn pause_download(download_id: String) -> Result<serde_json::Value, String> {
    let body = serde_json::json!({ "download_id": download_id });
    api_post("/api/pause", &body).await
}

/// Resume a paused download
#[tauri::command]
async fn resume_download(download_id: String) -> Result<serde_json::Value, String> {
    let body = serde_json::json!({ "download_id": download_id });
    api_post("/api/resume", &body).await
}

/// Cancel a download
#[tauri::command]
async fn cancel_download(download_id: String) -> Result<serde_json::Value, String> {
    let body = serde_json::json!({ "download_id": download_id });
    api_post("/api/cancel", &body).await
}

/// Get all active downloads
#[tauri::command]
async fn get_downloads() -> Result<serde_json::Value, String> {
    api_get("/api/downloads").await
}

/// Get download history
#[tauri::command]
async fn get_history() -> Result<serde_json::Value, String> {
    api_get("/api/history").await
}

/// Search torrents
#[tauri::command]
async fn search_torrents(query: String, category: Option<String>) -> Result<serde_json::Value, String> {
    let body = serde_json::json!({
        "query": query,
        "category": category,
    });
    api_post("/api/torrent/search", &body).await
}

/// Add a torrent (magnet or file)
#[tauri::command]
async fn add_torrent(uri: String, save_path: Option<String>) -> Result<serde_json::Value, String> {
    let body = serde_json::json!({
        "uri": uri,
        "save_path": save_path,
    });
    api_post("/api/torrent/add", &body).await
}

/// Get settings
#[tauri::command]
async fn get_settings() -> Result<serde_json::Value, String> {
    api_get("/api/settings").await
}

/// Update settings
#[tauri::command]
async fn update_settings(settings: serde_json::Value) -> Result<serde_json::Value, String> {
    api_post("/api/settings", &settings).await
}

/// Check backend health
#[tauri::command]
async fn check_backend_health() -> Result<serde_json::Value, String> {
    api_get("/api/health").await
}

// ──────────────────────────────────────────────
// App Entry Point
// ──────────────────────────────────────────────
#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_opener::init())
        .plugin(tauri_plugin_shell::init())
        .manage(BackendProcess(Mutex::new(None)))
        .setup(|app| {
            // Spawn the Python backend on startup
            let app_handle = app.handle().clone();
            std::thread::spawn(move || {
                let backend_dir = app_handle
                    .path()
                    .resource_dir()
                    .unwrap_or_default()
                    .join("backend");

                // Try to start the Python backend
                match Command::new("python3")
                    .arg("-m")
                    .arg("uvicorn")
                    .arg("api.server:app")
                    .arg("--host")
                    .arg("127.0.0.1")
                    .arg("--port")
                    .arg("18920")
                    .current_dir(&backend_dir)
                    .spawn()
                {
                    Ok(child) => {
                        let state: State<BackendProcess> = app_handle.state();
                        *state.0.lock().unwrap() = Some(child);
                        println!("✅ Backend started on port 18920");
                    }
                    Err(e) => {
                        eprintln!("⚠️  Failed to start backend: {}. Running in frontend-only mode.", e);
                    }
                }
            });

            Ok(())
        })
        .on_window_event(|window, event| {
            if let tauri::WindowEvent::Destroyed = event {
                // Kill backend when window closes
                let mut child_process = None;
                {
                    let state: State<BackendProcess> = window.state();
                    child_process = state.0.lock().unwrap().take();
                }
                if let Some(mut child) = child_process {
                    let _ = child.kill();
                    println!("🛑 Backend process terminated");
                }
            }
        })
        .invoke_handler(tauri::generate_handler![
            analyze_url,
            start_download,
            pause_download,
            resume_download,
            cancel_download,
            get_downloads,
            get_history,
            search_torrents,
            add_torrent,
            get_settings,
            update_settings,
            check_backend_health,
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
