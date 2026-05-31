#!/usr/bin/env node
"use strict";

const fs = require("node:fs");
const path = require("node:path");
const { spawnSync } = require("node:child_process");

const packageRoot = path.resolve(__dirname, "..");
const executable =
  process.platform === "win32"
    ? path.join(packageRoot, ".venv", "Scripts", "cc-branch.exe")
    : path.join(packageRoot, ".venv", "bin", "cc-branch");

if (!fs.existsSync(executable)) {
  console.error("cc-branch is not initialized in this npm package.");
  console.error("Run `npm rebuild cc-branch` to recreate the bundled Python environment.");
  process.exit(1);
}

const result = spawnSync(executable, process.argv.slice(2), {
  stdio: "inherit",
  env: process.env,
  shell: false,
});

if (result.error) {
  console.error(result.error.message);
  process.exit(1);
}

process.exit(result.status ?? 0);
