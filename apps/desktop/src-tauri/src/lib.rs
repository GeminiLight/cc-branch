use std::process::{Child, Command, Stdio};
use std::sync::Mutex;
use std::time::{Duration, Instant};
use tauri::tray::{MouseButton, MouseButtonState, TrayIconBuilder, TrayIconEvent};
use tauri::{Manager, RunEvent, WindowEvent};
use tauri_plugin_shell::process::{CommandChild, CommandEvent};
use tauri_plugin_shell::ShellExt;

pub enum BackendProcess {
    Sidecar(CommandChild),
    Python(Child),
}

impl BackendProcess {
    fn kill(self) {
        match self {
            BackendProcess::Sidecar(child) => {
                let _ = child.kill();
            }
            BackendProcess::Python(mut child) => {
                let _ = child.kill();
            }
        }
    }
}

pub struct PythonServer {
    pub process: Mutex<Option<BackendProcess>>,
    pub port: u16,
    pub config_path: String,
    pub state_path: String,
}

impl PythonServer {
    pub fn api_base(&self) -> String {
        format!("http://127.0.0.1:{}", self.port)
    }
}

impl Drop for PythonServer {
    fn drop(&mut self) {
        if let Ok(mut process) = self.process.lock() {
            if let Some(child) = process.take() {
                child.kill();
            }
        }
    }
}

/// Check whether a command is available on PATH.
fn command_exists(cmd: &str) -> bool {
    Command::new(cmd).arg("--version").output().is_ok()
}

/// Verify that the Python environment has cc-branch installed.
fn check_cc_branch(python: &str) -> Result<(), String> {
    let output = Command::new(python)
        .args(["-m", "cc_branch", "--version"])
        .output()
        .map_err(|e| format!("Failed to run cc-branch: {}", e))?;

    if output.status.success() {
        Ok(())
    } else {
        let stderr = String::from_utf8_lossy(&output.stderr);
        Err(format!(
            "cc-branch is not installed or not accessible.\n{}\n\n\
             Please install it first:\n  pip install cc-branch",
            stderr.trim()
        ))
    }
}

fn find_python() -> Result<String, String> {
    for cmd in ["python3", "python"] {
        if command_exists(cmd) {
            return Ok(cmd.to_string());
        }
    }
    Err("Python is not installed or not on PATH.\n\
         Please install Python 3.10+ and ensure 'python3' or 'python' is available."
        .to_string())
}

/// Poll the health endpoint until it responds or the timeout is reached.
fn wait_for_server(port: u16, timeout: Duration) -> Result<(), String> {
    let start = Instant::now();
    let client = reqwest::blocking::Client::builder()
        .timeout(Duration::from_secs(2))
        .build()
        .map_err(|e| e.to_string())?;

    while start.elapsed() < timeout {
        if client
            .get(format!("http://127.0.0.1:{}/api/status", port))
            .send()
            .is_ok()
        {
            return Ok(());
        }
        std::thread::sleep(Duration::from_millis(100));
    }

    Err(format!(
        "Python backend did not become ready on port {} within {:?}",
        port, timeout
    ))
}

fn start_python_server(config_path: &str, state_path: &str) -> Result<(Child, u16), String> {
    let python = find_python()?;
    check_cc_branch(&python)?;

    let port = portpicker::pick_unused_port().ok_or("No available port")?;

    let child = Command::new(&python)
        .args([
            "-m",
            "cc_branch",
            "serve",
            "--host",
            "127.0.0.1",
            "--port",
            &port.to_string(),
        ])
        .env("CC_BRANCH_CONFIG", config_path)
        .env("CC_BRANCH_STATE", state_path)
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .map_err(|e| format!("Failed to start Python server: {}", e))?;

    // Wait for the server to actually respond instead of a blind sleep.
    if let Err(e) = wait_for_server(port, Duration::from_secs(5)) {
        return Err(format!(
            "{}\n\n\
             Hints:\n\
             • Make sure you are running the desktop app from a directory that contains .cc-branch/config.yaml\n\
             • Check that 'cc-branch serve' works manually in this directory",
            e
        ));
    }

    Ok((child, port))
}

fn start_sidecar_server(
    app: &tauri::AppHandle,
    config_path: &str,
    state_path: &str,
) -> Result<(CommandChild, u16), String> {
    let port = portpicker::pick_unused_port().ok_or("No available port")?;

    let command = app
        .shell()
        .sidecar("cc-branch-backend")
        .map_err(|e| format!("Bundled backend sidecar is not available: {}", e))?
        .args([
            "--host",
            "127.0.0.1",
            "--port",
            &port.to_string(),
            "--config",
            config_path,
            "--state",
            state_path,
        ]);

    let (mut rx, child) = command
        .spawn()
        .map_err(|e| format!("Failed to start bundled backend sidecar: {}", e))?;

    tauri::async_runtime::spawn(async move {
        while let Some(event) = rx.recv().await {
            match event {
                CommandEvent::Stdout(line) => {
                    println!("[cc-branch-backend] {}", String::from_utf8_lossy(&line));
                }
                CommandEvent::Stderr(line) => {
                    eprintln!("[cc-branch-backend] {}", String::from_utf8_lossy(&line));
                }
                _ => {}
            }
        }
    });

    if let Err(e) = wait_for_server(port, Duration::from_secs(8)) {
        return Err(format!(
            "{}\n\n\
             The bundled cc-branch backend was found, but did not become ready.",
            e
        ));
    }

    Ok((child, port))
}

// ── Tauri Commands ──────────────────────────────────────────────────────────

#[tauri::command]
fn get_api_info(state: tauri::State<'_, PythonServer>) -> serde_json::Value {
    serde_json::json!({
        "port": state.port,
        "config_path": state.config_path,
        "state_path": state.state_path,
    })
}

#[tauri::command]
fn show_window(window: tauri::WebviewWindow) {
    let _ = window.show();
    let _ = window.set_focus();
}

#[tauri::command]
fn pick_project_directory(starting_dir: Option<String>) -> Option<String> {
    let mut dialog = rfd::FileDialog::new();
    if let Some(dir) = starting_dir.as_deref().filter(|value| !value.trim().is_empty()) {
        dialog = dialog.set_directory(dir);
    }
    dialog.pick_folder().map(|path| path.to_string_lossy().to_string())
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    let cwd = std::env::current_dir().unwrap_or_default();
    let config_path = cwd.join(".cc-branch").join("config.yaml");
    let state_path = cwd.join(".cc-branch").join("state.yaml");

    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_window_state::Builder::default().build())
        .invoke_handler(tauri::generate_handler![get_api_info, show_window, pick_project_directory])
        .setup(move |app| {
            if cfg!(debug_assertions) {
                app.handle().plugin(
                    tauri_plugin_log::Builder::default()
                        .level(log::LevelFilter::Info)
                        .build(),
                )?;
            }

            let config_path_str = config_path.to_string_lossy().to_string();
            let state_path_str = state_path.to_string_lossy().to_string();

            let (process, port) =
                match start_sidecar_server(app.handle(), &config_path_str, &state_path_str) {
                    Ok((child, port)) => {
                        println!("[tauri] Bundled backend sidecar started on port {}", port);
                        (Some(BackendProcess::Sidecar(child)), port)
                    }
                    Err(sidecar_error) if cfg!(debug_assertions) => {
                        eprintln!(
                            "[tauri] Bundled backend unavailable in dev mode: {}",
                            sidecar_error
                        );
                        match start_python_server(&config_path_str, &state_path_str) {
                            Ok((child, port)) => {
                                println!(
                                    "[tauri] Python backend fallback started on port {}",
                                    port
                                );
                                (Some(BackendProcess::Python(child)), port)
                            }
                            Err(python_error) => {
                                eprintln!(
                                    "[tauri] Warning: could not start Python backend fallback: {}",
                                    python_error
                                );
                                (None, 8080)
                            }
                        }
                    }
                    Err(sidecar_error) => {
                        eprintln!(
                            "[tauri] Warning: could not start bundled backend sidecar: {}",
                            sidecar_error
                        );
                        (None, 8080)
                    }
                };

            app.manage(PythonServer {
                process: Mutex::new(process),
                port,
                config_path: config_path_str,
                state_path: state_path_str,
            });

            // Show window once ready
            if let Some(window) = app.get_webview_window("main") {
                let _ = window.show();
                let _ = window.set_focus();
            }

            // macOS native menu
            #[cfg(target_os = "macos")]
            {
                let _ = app.set_menu(tauri::menu::Menu::with_items(
                    app,
                    &[
                        &tauri::menu::Submenu::with_items(
                            app,
                            "CC Branch",
                            true,
                            &[
                                &tauri::menu::PredefinedMenuItem::about(app, None, None)?,
                                &tauri::menu::PredefinedMenuItem::separator(app)?,
                                &tauri::menu::PredefinedMenuItem::quit(app, None)?,
                            ],
                        )?,
                        &tauri::menu::Submenu::with_items(
                            app,
                            "Edit",
                            true,
                            &[
                                &tauri::menu::PredefinedMenuItem::undo(app, None)?,
                                &tauri::menu::PredefinedMenuItem::redo(app, None)?,
                                &tauri::menu::PredefinedMenuItem::separator(app)?,
                                &tauri::menu::PredefinedMenuItem::cut(app, None)?,
                                &tauri::menu::PredefinedMenuItem::copy(app, None)?,
                                &tauri::menu::PredefinedMenuItem::paste(app, None)?,
                                &tauri::menu::PredefinedMenuItem::select_all(app, None)?,
                            ],
                        )?,
                        &tauri::menu::Submenu::with_items(
                            app,
                            "Window",
                            true,
                            &[
                                &tauri::menu::PredefinedMenuItem::minimize(app, None)?,
                                &tauri::menu::PredefinedMenuItem::close_window(app, None)?,
                                &tauri::menu::PredefinedMenuItem::separator(app)?,
                                &tauri::menu::PredefinedMenuItem::fullscreen(app, None)?,
                            ],
                        )?,
                    ],
                )?);
            }

            // System tray
            let show_i = tauri::menu::MenuItem::with_id(app, "show", "Show", true, None::<&str>)?;
            let hide_i = tauri::menu::MenuItem::with_id(app, "hide", "Hide", true, None::<&str>)?;
            let quit_i = tauri::menu::MenuItem::with_id(app, "quit", "Quit", true, None::<&str>)?;
            let menu = tauri::menu::Menu::with_items(app, &[&show_i, &hide_i, &quit_i])?;

            let tray = TrayIconBuilder::new()
                .menu(&menu)
                .show_menu_on_left_click(false)
                .on_menu_event(|app, event| match event.id.as_ref() {
                    "show" => {
                        if let Some(window) = app.get_webview_window("main") {
                            let _ = window.show();
                            let _ = window.set_focus();
                        }
                    }
                    "hide" => {
                        if let Some(window) = app.get_webview_window("main") {
                            let _ = window.hide();
                        }
                    }
                    "quit" => {
                        app.exit(0);
                    }
                    _ => {}
                })
                .on_tray_icon_event(|tray, event| {
                    if let TrayIconEvent::Click {
                        button: MouseButton::Left,
                        button_state: MouseButtonState::Up,
                        ..
                    } = event
                    {
                        let app = tray.app_handle();
                        if let Some(window) = app.get_webview_window("main") {
                            let _ = window.show();
                            let _ = window.set_focus();
                        }
                    }
                })
                .build(app)?;

            let _ = tray;

            Ok(())
        })
        .on_window_event(|window, event| {
            if let WindowEvent::CloseRequested { api, .. } = event {
                api.prevent_close();
                let _ = window.hide();
            }
        })
        .build(tauri::generate_context!())
        .expect("error while building tauri application")
        .run(|app_handle, event| {
            if let RunEvent::ExitRequested { api, .. } = event {
                // Gracefully terminate the Python child process before exiting.
                if let Some(state) = app_handle.try_state::<PythonServer>() {
                    if let Ok(mut guard) = state.process.lock() {
                        if let Some(child) = guard.take() {
                            child.kill();
                        }
                    }
                }
                api.prevent_exit();
                std::process::exit(0);
            }
        });
}
