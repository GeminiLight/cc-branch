use std::collections::HashSet;
use std::ffi::{OsStr, OsString};
use std::fs;
use std::path::{Path, PathBuf};
use std::process::{Child, Command, Stdio};
use std::sync::{Arc, Mutex};
use std::time::{Duration, Instant};
use tauri::tray::{MouseButton, MouseButtonState, TrayIconBuilder, TrayIconEvent};
use tauri::{Manager, RunEvent, WebviewUrl, WebviewWindow, WebviewWindowBuilder, WindowEvent};
use tauri_plugin_shell::process::{CommandChild, CommandEvent};
use tauri_plugin_shell::ShellExt;

const DESKTOP_BACKEND_PORT_ENV: &str = "CC_BRANCH_DESKTOP_PORT";
const DESKTOP_BACKEND_ALLOW_FIXED_PORT_ENV: &str = "CC_BRANCH_DESKTOP_ALLOW_FIXED_PORT";
const DESKTOP_BACKEND_SOURCE_ENV: &str = "CC_BRANCH_BACKEND_SOURCE";
const DESKTOP_VERSION_ENV: &str = "CC_BRANCH_DESKTOP_VERSION";
const DESKTOP_PLATFORM_ENV: &str = "CC_BRANCH_DESKTOP_PLATFORM";
const DESKTOP_ARCH_ENV: &str = "CC_BRANCH_DESKTOP_ARCH";
const WEB_TOKEN_ENV: &str = "CC_BRANCH_WEB_TOKEN";
const BUNDLED_BACKEND_SOURCE: &str = "bundled-sidecar";
const PYTHON_FALLBACK_BACKEND_SOURCE: &str = "python-fallback";
const BACKEND_START_MAX_ATTEMPTS: usize = 5;
const GITHUB_RELEASES_URL_PREFIX: &str = "https://github.com/GeminiLight/cc-branch/releases";
const DESKTOP_BACKEND_POISON_ENV: &[&str] = &[
    "PYTHONHOME",
    "PYTHONPATH",
    "VIRTUAL_ENV",
    "CONDA_PREFIX",
    "CONDA_DEFAULT_ENV",
    "LD_LIBRARY_PATH",
    "DYLD_LIBRARY_PATH",
];

enum BackendProbeError {
    Transient(String),
    Fatal(String),
}

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

pub struct BackendRuntime {
    pub process: Option<BackendProcess>,
    pub port: u16,
    pub backend_source: String,
    pub startup_error: Option<String>,
}

type BackendLogBuffer = Arc<Mutex<Vec<String>>>;

fn push_backend_log(logs: &BackendLogBuffer, stream: &str, line: &[u8]) {
    let text = String::from_utf8_lossy(line).trim_end().to_string();
    if text.is_empty() {
        return;
    }
    if let Ok(mut entries) = logs.lock() {
        entries.push(format!("{}: {}", stream, text));
        let extra = entries.len().saturating_sub(80);
        if extra > 0 {
            entries.drain(0..extra);
        }
    }
}

fn backend_log_tail(logs: &BackendLogBuffer) -> String {
    logs.lock()
        .map(|entries| entries.join("\n"))
        .unwrap_or_default()
}

pub struct PythonServer {
    pub runtime: Mutex<BackendRuntime>,
    pub config_path: String,
    pub state_path: String,
    pub desktop_version: String,
    pub desktop_platform: String,
    pub desktop_arch: String,
}

impl PythonServer {
    pub fn api_base(&self) -> String {
        let port = self.runtime.lock().map(|runtime| runtime.port).unwrap_or(0);
        format!("http://127.0.0.1:{}", port)
    }
}

impl Drop for PythonServer {
    fn drop(&mut self) {
        if let Ok(mut runtime) = self.runtime.lock() {
            if let Some(child) = runtime.process.take() {
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

fn desktop_version() -> &'static str {
    env!("CARGO_PKG_VERSION")
}

fn desktop_platform() -> &'static str {
    if cfg!(target_os = "macos") {
        "darwin"
    } else {
        std::env::consts::OS
    }
}

fn desktop_arch() -> &'static str {
    std::env::consts::ARCH
}

fn backend_info_matches_source(
    client: &reqwest::blocking::Client,
    port: u16,
    expected_backend_source: &str,
    expected_config_path: &str,
    expected_state_path: &str,
    expected_desktop_version: &str,
    expected_desktop_platform: &str,
    expected_desktop_arch: &str,
) -> Result<bool, BackendProbeError> {
    let response = client
        .get(format!("http://127.0.0.1:{}/api/info", port))
        .send()
        .map_err(|e| BackendProbeError::Transient(e.to_string()))?;
    if !response.status().is_success() {
        return Ok(false);
    }
    let value = response.json::<serde_json::Value>().map_err(|e| {
        BackendProbeError::Fatal(format!(
            "Backend /api/info response is not valid JSON: {}",
            e
        ))
    })?;
    let source = value
        .get("backend_source")
        .and_then(|source| source.as_str())
        .unwrap_or("");
    if source != expected_backend_source {
        return Err(BackendProbeError::Fatal(format!(
            "Unexpected backend source on 127.0.0.1:{}: got {:?}, expected {:?}",
            port, source, expected_backend_source
        )));
    }
    let config_path = value
        .get("config_path")
        .and_then(|path| path.as_str())
        .unwrap_or("");
    if config_path != expected_config_path {
        return Err(BackendProbeError::Fatal(format!(
            "Unexpected backend config path on 127.0.0.1:{}: got {:?}, expected {:?}",
            port, config_path, expected_config_path
        )));
    }
    let state_path = value
        .get("state_path")
        .and_then(|path| path.as_str())
        .unwrap_or("");
    if state_path != expected_state_path {
        return Err(BackendProbeError::Fatal(format!(
            "Unexpected backend state path on 127.0.0.1:{}: got {:?}, expected {:?}",
            port, state_path, expected_state_path
        )));
    }
    let desktop_version = value
        .get("desktop_version")
        .and_then(|version| version.as_str())
        .unwrap_or("");
    if desktop_version != expected_desktop_version {
        return Err(BackendProbeError::Fatal(format!(
            "Unexpected backend desktop version on 127.0.0.1:{}: got {:?}, expected {:?}",
            port, desktop_version, expected_desktop_version
        )));
    }
    let desktop_platform = value
        .get("desktop_platform")
        .and_then(|platform| platform.as_str())
        .unwrap_or("");
    if desktop_platform != expected_desktop_platform {
        return Err(BackendProbeError::Fatal(format!(
            "Unexpected backend desktop platform on 127.0.0.1:{}: got {:?}, expected {:?}",
            port, desktop_platform, expected_desktop_platform
        )));
    }
    let desktop_arch = value
        .get("desktop_arch")
        .and_then(|arch| arch.as_str())
        .unwrap_or("");
    if desktop_arch != expected_desktop_arch {
        return Err(BackendProbeError::Fatal(format!(
            "Unexpected backend desktop arch on 127.0.0.1:{}: got {:?}, expected {:?}",
            port, desktop_arch, expected_desktop_arch
        )));
    }
    Ok(true)
}

fn backend_http_client(timeout: Duration) -> Result<reqwest::blocking::Client, String> {
    reqwest::blocking::Client::builder()
        .timeout(timeout)
        .no_proxy()
        .build()
        .map_err(|e| e.to_string())
}

/// Poll the health endpoint until the expected backend responds or the timeout is reached.
fn wait_for_server(
    port: u16,
    timeout: Duration,
    expected_backend_source: &str,
    expected_config_path: &str,
    expected_state_path: &str,
    expected_desktop_version: &str,
    expected_desktop_platform: &str,
    expected_desktop_arch: &str,
) -> Result<(), String> {
    let start = Instant::now();
    let client = backend_http_client(Duration::from_secs(2))?;
    let mut last_transient_error: Option<String> = None;
    while start.elapsed() < timeout {
        match backend_info_matches_source(
            &client,
            port,
            expected_backend_source,
            expected_config_path,
            expected_state_path,
            expected_desktop_version,
            expected_desktop_platform,
            expected_desktop_arch,
        ) {
            Ok(true) => return Ok(()),
            Ok(false) => {}
            Err(BackendProbeError::Transient(error)) => {
                last_transient_error = Some(error);
            }
            Err(BackendProbeError::Fatal(error)) => return Err(error),
        }
        std::thread::sleep(Duration::from_millis(100));
    }

    let details = last_transient_error
        .map(|error| format!(" Last transient error: {}.", error))
        .unwrap_or_default();
    Err(format!(
        "Backend {:?} did not become ready on port {} within {:?}.",
        expected_backend_source, port, timeout
    ) + &details)
}

fn backend_probe_error_to_string(error: BackendProbeError) -> String {
    match error {
        BackendProbeError::Transient(error) | BackendProbeError::Fatal(error) => error,
    }
}

fn backend_http_ready(
    port: u16,
    expected_backend_source: &str,
    expected_config_path: &str,
    expected_state_path: &str,
    expected_desktop_version: &str,
    expected_desktop_platform: &str,
    expected_desktop_arch: &str,
) -> Result<bool, String> {
    if port == 0 {
        return Ok(false);
    }
    let client = backend_http_client(Duration::from_millis(600))?;
    backend_info_matches_source(
        &client,
        port,
        expected_backend_source,
        expected_config_path,
        expected_state_path,
        expected_desktop_version,
        expected_desktop_platform,
        expected_desktop_arch,
    )
    .map_err(backend_probe_error_to_string)
}

fn backend_readiness(
    runtime: &BackendRuntime,
    expected_config_path: &str,
    expected_state_path: &str,
    expected_desktop_version: &str,
    expected_desktop_platform: &str,
    expected_desktop_arch: &str,
) -> (bool, Option<String>) {
    if runtime.process.is_none() {
        return (
            false,
            runtime
                .startup_error
                .clone()
                .or_else(|| Some("Desktop backend process is not running.".to_string())),
        );
    }

    match backend_http_ready(
        runtime.port,
        &runtime.backend_source,
        expected_config_path,
        expected_state_path,
        expected_desktop_version,
        expected_desktop_platform,
        expected_desktop_arch,
    ) {
        Ok(true) => return (true, None),
        Ok(false) => {}
        Err(error) => return (false, Some(error)),
    }

    (
        false,
        Some(format!(
            "Desktop backend process is not responding on 127.0.0.1:{}.",
            runtime.port
        )),
    )
}

fn wait_for_sidecar_server(
    child: CommandChild,
    port: u16,
    expected_config_path: &str,
    expected_state_path: &str,
) -> Result<CommandChild, String> {
    match wait_for_server(
        port,
        Duration::from_secs(45),
        BUNDLED_BACKEND_SOURCE,
        expected_config_path,
        expected_state_path,
        desktop_version(),
        desktop_platform(),
        desktop_arch(),
    ) {
        Ok(()) => Ok(child),
        Err(error) => {
            let _ = child.kill();
            Err(error)
        }
    }
}

fn parse_desktop_backend_port(value: &str) -> Result<u16, String> {
    let port = value.parse::<u16>().map_err(|_| {
        format!(
            "Configured desktop backend port must be between 1 and 65535: {}",
            value
        )
    })?;
    if port == 0 {
        return Err(format!(
            "Configured desktop backend port must be between 1 and 65535: {}",
            value
        ));
    }
    Ok(port)
}

fn desktop_backend_fixed_port_allowed() -> bool {
    matches!(
        std::env::var(DESKTOP_BACKEND_ALLOW_FIXED_PORT_ENV).as_deref(),
        Ok("1")
    )
}

fn desktop_backend_port_from_env() -> Result<Option<u16>, String> {
    if !desktop_backend_fixed_port_allowed() {
        return Ok(None);
    }
    match std::env::var(DESKTOP_BACKEND_PORT_ENV) {
        Ok(value) => Ok(Some(parse_desktop_backend_port(&value)?)),
        Err(std::env::VarError::NotPresent) => Ok(None),
        Err(error) => Err(format!(
            "Configured desktop backend port is not valid UTF-8: {}",
            error
        )),
    }
}

fn pick_desktop_backend_port() -> Result<u16, String> {
    portpicker::pick_unused_port().ok_or_else(|| "No available port".to_string())
}

fn desktop_backend_port() -> Result<u16, String> {
    if let Some(port) = desktop_backend_port_from_env()? {
        return Ok(port);
    }
    pick_desktop_backend_port()
}

fn is_poisoned_backend_env(name: &OsStr) -> bool {
    name.to_str().is_some_and(|value| {
        DESKTOP_BACKEND_POISON_ENV
            .iter()
            .any(|blocked| value.eq_ignore_ascii_case(blocked))
    })
}

fn sanitized_backend_environment() -> Vec<(OsString, OsString)> {
    std::env::vars_os()
        .filter(|(name, _value)| !is_poisoned_backend_env(name))
        .collect()
}

fn start_python_server(config_path: &str, state_path: &str) -> Result<(Child, u16), String> {
    let python = find_python()?;
    check_cc_branch(&python)?;

    let port = desktop_backend_port()?;

    let mut command = Command::new(&python);
    command.args([
        "-m",
        "cc_branch",
        "serve",
        "--host",
        "127.0.0.1",
        "--port",
        &port.to_string(),
    ]);
    for name in DESKTOP_BACKEND_POISON_ENV {
        command.env_remove(name);
    }
    let mut child = command
        .env("CC_BRANCH_CONFIG", config_path)
        .env("CC_BRANCH_STATE", state_path)
        .env(DESKTOP_BACKEND_SOURCE_ENV, PYTHON_FALLBACK_BACKEND_SOURCE)
        .env(DESKTOP_VERSION_ENV, desktop_version())
        .env(DESKTOP_PLATFORM_ENV, desktop_platform())
        .env(DESKTOP_ARCH_ENV, desktop_arch())
        .env(WEB_TOKEN_ENV, "")
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .map_err(|e| format!("Failed to start Python server: {}", e))?;

    // Wait for the server to actually respond instead of a blind sleep.
    if let Err(e) = wait_for_server(
        port,
        Duration::from_secs(15),
        PYTHON_FALLBACK_BACKEND_SOURCE,
        config_path,
        state_path,
        desktop_version(),
        desktop_platform(),
        desktop_arch(),
    ) {
        let _ = child.kill();
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
    let fixed_port = desktop_backend_port_from_env()?;
    let attempts = if fixed_port.is_some() {
        1
    } else {
        BACKEND_START_MAX_ATTEMPTS
    };
    let mut attempt_errors: Vec<String> = Vec::new();

    for attempt in 1..=attempts {
        let port = match fixed_port {
            Some(port) => port,
            None => pick_desktop_backend_port()?,
        };

        let command = app
            .shell()
            .sidecar("cc-branch-backend")
            .map_err(|e| format!("Bundled backend sidecar is not available: {}", e))?
            .env_clear()
            .envs(sanitized_backend_environment())
            .args([
                "--host",
                "127.0.0.1",
                "--port",
                &port.to_string(),
                "--config",
                config_path,
                "--state",
                state_path,
            ])
            .env(DESKTOP_BACKEND_SOURCE_ENV, BUNDLED_BACKEND_SOURCE)
            .env(DESKTOP_VERSION_ENV, desktop_version())
            .env(DESKTOP_PLATFORM_ENV, desktop_platform())
            .env(DESKTOP_ARCH_ENV, desktop_arch())
            .env(WEB_TOKEN_ENV, "");

        let backend_logs: BackendLogBuffer = Arc::new(Mutex::new(Vec::new()));
        let (mut rx, child) = command
            .spawn()
            .map_err(|e| format!("Failed to start bundled backend sidecar: {}", e))?;

        let backend_logs_for_task = Arc::clone(&backend_logs);
        tauri::async_runtime::spawn(async move {
            while let Some(event) = rx.recv().await {
                match event {
                    CommandEvent::Stdout(line) => {
                        push_backend_log(&backend_logs_for_task, "stdout", &line);
                        println!("[cc-branch-backend] {}", String::from_utf8_lossy(&line));
                    }
                    CommandEvent::Stderr(line) => {
                        push_backend_log(&backend_logs_for_task, "stderr", &line);
                        eprintln!("[cc-branch-backend] {}", String::from_utf8_lossy(&line));
                    }
                    _ => {}
                }
            }
        });

        match wait_for_sidecar_server(child, port, config_path, state_path) {
            Ok(child) => return Ok((child, port)),
            Err(e) => {
                let output_tail = backend_log_tail(&backend_logs);
                let details = if output_tail.is_empty() {
                    e
                } else {
                    format!("{}\n\nBundled backend output:\n{}", e, output_tail)
                };
                attempt_errors.push(format!("attempt {} on port {}: {}", attempt, port, details));
                if attempt < attempts {
                    eprintln!(
                        "[tauri] Bundled backend did not become ready on port {}; retrying with a new port.",
                        port
                    );
                }
            }
        }
    }

    Err(format!(
        "Bundled backend sidecar did not become ready after {} attempt(s).\n{}\n\n\
         The bundled cc-branch backend was found, but did not become ready.",
        attempts,
        attempt_errors.join("\n")
    ))
}

fn start_backend_runtime(
    app: &tauri::AppHandle,
    config_path: &str,
    state_path: &str,
) -> BackendRuntime {
    match start_sidecar_server(app, config_path, state_path) {
        Ok((child, port)) => {
            println!("[tauri] Bundled backend sidecar started on port {}", port);
            BackendRuntime {
                process: Some(BackendProcess::Sidecar(child)),
                port,
                backend_source: BUNDLED_BACKEND_SOURCE.to_string(),
                startup_error: None,
            }
        }
        Err(sidecar_error) => {
            eprintln!("[tauri] Bundled backend unavailable: {}", sidecar_error);
            if cfg!(debug_assertions) {
                match start_python_server(config_path, state_path) {
                    Ok((child, port)) => {
                        println!("[tauri] Python backend fallback started on port {}", port);
                        BackendRuntime {
                            process: Some(BackendProcess::Python(child)),
                            port,
                            backend_source: PYTHON_FALLBACK_BACKEND_SOURCE.to_string(),
                            startup_error: None,
                        }
                    }
                    Err(python_error) => {
                        eprintln!(
                            "[tauri] Warning: could not start Python backend fallback: {}",
                            python_error
                        );
                        BackendRuntime {
                            process: None,
                            port: 0,
                            backend_source: "none".to_string(),
                            startup_error: Some(format!(
                                "Bundled backend failed: {}\nPython fallback failed: {}",
                                sidecar_error, python_error
                            )),
                        }
                    }
                }
            } else {
                eprintln!(
                    "[tauri] Python fallback is disabled in release builds; reinstall this desktop release or download a fresh installer."
                );
                BackendRuntime {
                    process: None,
                    port: 0,
                    backend_source: "none".to_string(),
                    startup_error: Some(format!(
                        "Bundled backend failed: {}\nPython fallback is disabled in release builds; reinstall this desktop release or download a fresh installer.",
                        sidecar_error
                    )),
                }
            }
        }
    }
}

fn backend_workspace_paths(app: &tauri::App) -> (PathBuf, PathBuf) {
    let base_dir = user_home_dir()
        .unwrap_or_else(|| {
            app.path()
                .app_data_dir()
                .unwrap_or_else(|_| std::env::temp_dir().join("cc-branch"))
        })
        .join(".cc-branch")
        .join("app")
        .join("backend-workspace");

    (
        base_dir.join(".cc-branch").join("config.yaml"),
        base_dir.join(".cc-branch").join("state.yaml"),
    )
}

fn user_home_dir() -> Option<PathBuf> {
    if let Some(home) = std::env::var_os("HOME") {
        let path = PathBuf::from(home);
        if !path.as_os_str().is_empty() {
            return Some(path);
        }
    }

    #[cfg(windows)]
    {
        if let Some(profile) = std::env::var_os("USERPROFILE") {
            let path = PathBuf::from(profile);
            if !path.as_os_str().is_empty() {
                return Some(path);
            }
        }

        if let (Some(drive), Some(path)) =
            (std::env::var_os("HOMEDRIVE"), std::env::var_os("HOMEPATH"))
        {
            let mut home = PathBuf::from(drive);
            home.push(path);
            if !home.as_os_str().is_empty() {
                return Some(home);
            }
        }
    }

    None
}

// ── Tauri Commands ──────────────────────────────────────────────────────────

fn default_shell_name() -> String {
    #[cfg(windows)]
    {
        if let Ok(shell) = std::env::var("COMSPEC") {
            return Path::new(&shell)
                .file_name()
                .and_then(|name| name.to_str())
                .unwrap_or(&shell)
                .to_string();
        }
        return "cmd".to_string();
    }

    #[cfg(not(windows))]
    {
        if let Ok(shell) = std::env::var("SHELL") {
            return Path::new(&shell)
                .file_name()
                .and_then(|name| name.to_str())
                .unwrap_or(&shell)
                .to_string();
        }
        "sh".to_string()
    }
}

fn split_ssh_config_line(line: &str) -> Vec<String> {
    let mut parts = Vec::new();
    let mut current = String::new();
    let mut quote: Option<char> = None;

    for ch in line.chars() {
        if quote.is_none() && ch == '#' {
            break;
        }
        if ch == '"' || ch == '\'' {
            if quote == Some(ch) {
                quote = None;
                continue;
            }
            if quote.is_none() {
                quote = Some(ch);
                continue;
            }
        }
        if quote.is_none() && ch.is_whitespace() {
            if !current.is_empty() {
                parts.push(std::mem::take(&mut current));
            }
            continue;
        }
        current.push(ch);
    }

    if !current.is_empty() {
        parts.push(current);
    }
    parts
}

fn is_concrete_ssh_alias(value: &str) -> bool {
    !value.is_empty() && !value.starts_with('!') && !value.contains('*') && !value.contains('?')
}

fn discover_ssh_hosts() -> Vec<serde_json::Value> {
    let Some(home) = user_home_dir() else {
        return Vec::new();
    };
    let path = home.join(".ssh").join("config");
    let Ok(content) = fs::read_to_string(path) else {
        return Vec::new();
    };

    let mut hosts = Vec::new();
    let mut seen = HashSet::new();
    let mut aliases: Vec<String> = Vec::new();
    let mut hostname: Option<String> = None;
    let mut user: Option<String> = None;
    let mut port: Option<u16> = None;

    let mut flush = |aliases: &mut Vec<String>,
                     hostname: &mut Option<String>,
                     user: &mut Option<String>,
                     port: &mut Option<u16>| {
        for alias in aliases.drain(..) {
            if !seen.insert(alias.clone()) {
                continue;
            }
            let mut host = serde_json::Map::new();
            host.insert("alias".to_string(), serde_json::Value::String(alias));
            if let Some(value) = hostname.clone() {
                host.insert("hostname".to_string(), serde_json::Value::String(value));
            }
            if let Some(value) = user.clone() {
                host.insert("user".to_string(), serde_json::Value::String(value));
            }
            if let Some(value) = *port {
                host.insert("port".to_string(), serde_json::Value::from(value));
            }
            hosts.push(serde_json::Value::Object(host));
        }
        *hostname = None;
        *user = None;
        *port = None;
    };

    for line in content.lines() {
        let parts = split_ssh_config_line(line);
        if parts.is_empty() {
            continue;
        }
        let key = parts[0].to_ascii_lowercase();
        if key == "host" {
            flush(&mut aliases, &mut hostname, &mut user, &mut port);
            aliases = parts[1..]
                .iter()
                .filter(|value| is_concrete_ssh_alias(value))
                .cloned()
                .collect();
            continue;
        }
        if aliases.is_empty() || parts.len() < 2 {
            continue;
        }
        match key.as_str() {
            "hostname" if hostname.is_none() => hostname = Some(parts[1].clone()),
            "user" if user.is_none() => user = Some(parts[1].clone()),
            "port" if port.is_none() => {
                if let Ok(value) = parts[1].parse::<u16>() {
                    if value > 0 {
                        port = Some(value);
                    }
                }
            }
            _ => {}
        }
    }
    flush(&mut aliases, &mut hostname, &mut user, &mut port);
    hosts
}

#[tauri::command]
fn get_api_info(state: tauri::State<'_, PythonServer>) -> serde_json::Value {
    api_info_payload(&state)
}

fn api_info_payload(state: &PythonServer) -> serde_json::Value {
    let Ok(runtime) = state.runtime.lock() else {
        return serde_json::json!({
            "port": 0,
            "config_path": state.config_path,
            "state_path": state.state_path,
            "desktop_version": state.desktop_version,
            "desktop_platform": state.desktop_platform,
            "desktop_arch": state.desktop_arch,
            "backend_ready": false,
            "backend_source": "unknown",
            "startup_error": "Desktop backend state is locked.",
            "default_shell": default_shell_name(),
            "ssh_hosts": discover_ssh_hosts(),
        });
    };
    let (backend_ready, runtime_error) = backend_readiness(
        &runtime,
        &state.config_path,
        &state.state_path,
        &state.desktop_version,
        &state.desktop_platform,
        &state.desktop_arch,
    );
    let startup_error = runtime.startup_error.clone().or(runtime_error);
    serde_json::json!({
        "port": runtime.port,
        "config_path": state.config_path,
        "state_path": state.state_path,
        "desktop_version": state.desktop_version,
        "desktop_platform": state.desktop_platform,
        "desktop_arch": state.desktop_arch,
        "backend_ready": backend_ready,
        "backend_source": runtime.backend_source,
        "startup_error": startup_error,
        "default_shell": default_shell_name(),
        "ssh_hosts": discover_ssh_hosts(),
    })
}

#[tauri::command]
fn restart_backend(
    app: tauri::AppHandle,
    state: tauri::State<'_, PythonServer>,
) -> serde_json::Value {
    let old_process = state.runtime.lock().ok().and_then(|mut runtime| {
        runtime.port = 0;
        runtime.startup_error = Some("Restarting desktop backend.".to_string());
        runtime.process.take()
    });
    if let Some(child) = old_process {
        child.kill();
    }

    let next_runtime = start_backend_runtime(&app, &state.config_path, &state.state_path);
    if let Ok(mut runtime) = state.runtime.lock() {
        *runtime = next_runtime;
    }
    api_info_payload(&state)
}

fn is_valid_release_tag(value: &str) -> bool {
    value.starts_with("v")
        && value.len() >= 6
        && value
            .chars()
            .all(|ch| ch.is_ascii_alphanumeric() || matches!(ch, '.' | '-' | '+'))
}

fn validate_external_release_url(url: &str) -> Result<(), String> {
    if url == GITHUB_RELEASES_URL_PREFIX {
        return Ok(());
    }
    let Some(path) = url.strip_prefix(GITHUB_RELEASES_URL_PREFIX) else {
        return Err(
            "Only GitHub Releases URLs can be opened from the desktop support panel.".to_string(),
        );
    };
    let Some(tag) = path.strip_prefix("/tag/") else {
        return Err(
            "Only GitHub Releases URLs can be opened from the desktop support panel.".to_string(),
        );
    };
    if is_valid_release_tag(tag) {
        return Ok(());
    }
    Err("Only GitHub Releases URLs can be opened from the desktop support panel.".to_string())
}

#[tauri::command]
fn open_external_url(url: String) -> Result<(), String> {
    validate_external_release_url(&url)?;
    #[cfg(target_os = "macos")]
    let status = Command::new("open").arg(&url).status();
    #[cfg(target_os = "windows")]
    let status = Command::new("cmd").args(["/C", "start", "", &url]).status();
    #[cfg(all(not(target_os = "macos"), not(target_os = "windows")))]
    let status = Command::new("xdg-open").arg(&url).status();

    let status = status.map_err(|e| format!("Failed to open GitHub Releases URL: {}", e))?;
    if status.success() {
        Ok(())
    } else {
        Err(format!(
            "Failed to open GitHub Releases URL; opener exited with status {}.",
            status
        ))
    }
}

fn desktop_app_path() -> Result<PathBuf, String> {
    let current = std::env::current_exe()
        .map_err(|e| format!("Failed to locate the running desktop app: {}", e))?;
    #[cfg(target_os = "macos")]
    {
        for ancestor in current.ancestors() {
            if ancestor.extension().is_some_and(|extension| extension == "app") {
                return Ok(ancestor.to_path_buf());
            }
        }
    }
    Ok(current)
}

fn reveal_path_in_file_manager(path: &Path) -> Result<(), String> {
    #[cfg(target_os = "macos")]
    let status = Command::new("open").arg("-R").arg(path).status();
    #[cfg(target_os = "windows")]
    let status = Command::new("explorer")
        .arg(format!("/select,{}", path.to_string_lossy()))
        .status();
    #[cfg(all(not(target_os = "macos"), not(target_os = "windows")))]
    let status = Command::new("xdg-open")
        .arg(path.parent().unwrap_or(path))
        .status();

    let status = status.map_err(|e| format!("Failed to reveal desktop app: {}", e))?;
    if status.success() {
        Ok(())
    } else {
        Err(format!(
            "Failed to reveal desktop app; opener exited with status {}.",
            status
        ))
    }
}

#[tauri::command]
fn reveal_desktop_app() -> Result<serde_json::Value, String> {
    let path = desktop_app_path()?;
    reveal_path_in_file_manager(&path)?;
    Ok(serde_json::json!({
        "success": true,
        "path": path.to_string_lossy().to_string(),
    }))
}

#[tauri::command]
fn show_window(window: tauri::WebviewWindow) {
    let _ = window.show();
    let _ = window.set_focus();
}

fn ensure_main_window(app: &tauri::AppHandle) -> Option<WebviewWindow> {
    let window = app.get_webview_window("main").or_else(|| {
        match WebviewWindowBuilder::new(app, "main", WebviewUrl::App("index.html".into()))
            .title("CC Branch Dashboard")
            .inner_size(960.0, 720.0)
            .min_inner_size(640.0, 480.0)
            .resizable(true)
            .visible(true)
            .center()
            .build()
        {
            Ok(window) => Some(window),
            Err(error) => {
                eprintln!("[tauri] Failed to create main window: {}", error);
                None
            }
        }
    });

    if let Some(window) = &window {
        let _ = window.show();
        let _ = window.set_focus();
    }

    window
}

#[tauri::command]
fn pick_project_directory(starting_dir: Option<String>) -> Option<String> {
    let mut dialog = rfd::FileDialog::new();
    if let Some(dir) = starting_dir
        .as_deref()
        .filter(|value| !value.trim().is_empty())
    {
        dialog = dialog.set_directory(dir);
    }
    dialog
        .pick_folder()
        .map(|path| path.to_string_lossy().to_string())
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_process::init())
        .plugin(tauri_plugin_updater::Builder::new().build())
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_window_state::Builder::default().build())
        .invoke_handler(tauri::generate_handler![
            get_api_info,
            restart_backend,
            open_external_url,
            reveal_desktop_app,
            show_window,
            pick_project_directory
        ])
        .setup(|app| {
            if cfg!(debug_assertions) {
                app.handle().plugin(
                    tauri_plugin_log::Builder::default()
                        .level(log::LevelFilter::Info)
                        .build(),
                )?;
            }

            let (config_path, state_path) = backend_workspace_paths(app);
            let config_path_str = config_path.to_string_lossy().to_string();
            let state_path_str = state_path.to_string_lossy().to_string();
            let runtime = start_backend_runtime(app.handle(), &config_path_str, &state_path_str);

            app.manage(PythonServer {
                runtime: Mutex::new(runtime),
                config_path: config_path_str,
                state_path: state_path_str,
                desktop_version: desktop_version().to_string(),
                desktop_platform: desktop_platform().to_string(),
                desktop_arch: desktop_arch().to_string(),
            });

            // Show window once ready. If the platform did not create the
            // configured window, create it explicitly instead of leaving a
            // headless tray-only process.
            let _ = ensure_main_window(app.handle());

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
                        let _ = ensure_main_window(app);
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
                        let _ = ensure_main_window(app);
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
                    if let Ok(mut runtime) = state.runtime.lock() {
                        if let Some(child) = runtime.process.take() {
                            child.kill();
                        }
                    }
                }
                api.prevent_exit();
                std::process::exit(0);
            }
        });
}
