"use strict";

const fs = require("node:fs");
const path = require("node:path");
const { spawnSync } = require("node:child_process");

const packageRoot = path.resolve(__dirname, "..");
const venvDir = path.join(packageRoot, ".venv");
const vendorDir = path.join(packageRoot, "vendor");

function run(command, args, options = {}) {
  const result = spawnSync(command, args, {
    cwd: packageRoot,
    stdio: "inherit",
    shell: false,
    ...options,
  });
  if (result.error || result.status !== 0) {
    const detail = result.error ? result.error.message : `${command} exited with ${result.status}`;
    throw new Error(detail);
  }
}

function isSupportedPython(command, args) {
  const result = spawnSync(
    command,
    [
      ...args,
      "-c",
      "import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)",
    ],
    { stdio: "ignore", shell: false },
  );
  return !result.error && result.status === 0;
}

function findPython() {
  if (process.env.CC_BRANCH_PYTHON) {
    if (isSupportedPython(process.env.CC_BRANCH_PYTHON, [])) {
      return { command: process.env.CC_BRANCH_PYTHON, args: [] };
    }
    throw new Error("CC_BRANCH_PYTHON must point to Python 3.10 or newer.");
  }
  if (process.platform === "win32" && isSupportedPython("py", ["-3"])) {
    return { command: "py", args: ["-3"] };
  }
  for (const candidate of ["python3.12", "python3.11", "python3.10", "python3", "python"]) {
    if (isSupportedPython(candidate, [])) {
      return { command: candidate, args: [] };
    }
  }
  throw new Error("Python 3.10 or newer is required to install cc-branch from npm.");
}

function venvPython() {
  return process.platform === "win32"
    ? path.join(venvDir, "Scripts", "python.exe")
    : path.join(venvDir, "bin", "python");
}

function bundledWheel() {
  const wheel = fs
    .readdirSync(vendorDir)
    .find((name) => /^cc_branch-.+-py3-none-any\.whl$/.test(name));
  if (!wheel) {
    throw new Error("Missing bundled cc-branch wheel in vendor/.");
  }
  return path.join(vendorDir, wheel);
}

if (process.env.CC_BRANCH_NPM_SKIP_POSTINSTALL === "1") {
  process.exit(0);
}

try {
  const python = findPython();
  if (!fs.existsSync(venvDir)) {
    run(python.command, [...python.args, "-m", "venv", venvDir]);
  }
  const py = venvPython();
  run(py, ["-m", "pip", "install", "--upgrade", "pip"]);
  run(py, ["-m", "pip", "install", "--upgrade", bundledWheel()]);
} catch (error) {
  console.error("");
  console.error("Failed to initialize cc-branch.");
  console.error(String(error.message || error));
  console.error("");
  console.error("Set CC_BRANCH_PYTHON=/path/to/python3 if Python is installed in a custom location.");
  process.exit(1);
}
