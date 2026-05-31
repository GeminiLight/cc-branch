# 发布与分发

本文档是 CC Branch 的发布 runbook，说明如何准备和验证公开分发渠道。它不表示这些渠道已经发布完成。

- GitHub Releases：发布后提供桌面版安装包
- Homebrew tap：发布后作为 macOS / Linux CLI 安装方式
- PyPI：发布后支持 Python 用户通过 `pip install cc-branch` 安装 CLI/backend 和浏览器 Web UI
- npm：可选发布 `packaging/npm/` wrapper。它会安装随包附带的 Python wheel；`apps/web` 和 `apps/desktop` 仍然是应用工程，不是 npm SDK。

## 前置准备

### 1. 安装发布工具

```bash
pip install build twine
```

### 2. 注册 PyPI 账号

- 生产环境: https://pypi.org/account/register/
- 测试环境: https://test.pypi.org/account/register/

### 3. 配置 API Token

在 PyPI 账号设置中创建 API token,然后配置:

```bash
# 创建 ~/.pypirc
cat > ~/.pypirc << 'EOF'
[pypi]
username = __token__
password = pypi-AgEIcHlwaS5vcmcC...  # 你的 token

[testpypi]
username = __token__
password = pypi-AgENdGVzdC5weXBpLm9yZwI...  # 测试环境 token
EOF

chmod 600 ~/.pypirc
```

## PyPI 发布流程

### 步骤 1: 更新版本号

编辑 `pyproject.toml`:

```toml
[project]
name = "cc-branch"
version = "1.0.0"  # 更新这里
```

### 步骤 2: 清理旧构建

```bash
rm -rf dist/ build/ *.egg-info
```

### 步骤 3: 构建 Web UI

```bash
npm --prefix apps ci
python scripts/build-webui.py
```

PyPI 包不会在用户机器上运行 npm。发布前必须先把 `apps/web` 构建到 `cc_branch/webui/static/`，再构建 Python 包。

### 步骤 4: 构建分发包

```bash
python -m build
```

这会在 `dist/` 目录生成:
- `cc_branch-1.0.0.tar.gz` (源码分发)
- `cc_branch-1.0.0-py3-none-any.whl` (wheel 分发)

### 步骤 5: 检查构建结果

```bash
twine check dist/*
```

应该显示:
```
Checking dist/cc_branch-1.0.0.tar.gz: PASSED
Checking dist/cc_branch-1.0.0-py3-none-any.whl: PASSED
```

### 步骤 6: 测试发布(推荐)

先发布到测试环境:

```bash
twine upload --repository testpypi dist/*
```

测试安装:

```bash
python -m pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple cc-branch
cc-branch --version
cc-branch serve
```

### 步骤 7: 正式发布

确认测试无误后,发布到生产环境:

```bash
twine upload dist/*
```

### 步骤 8: 验证发布

```bash
# 等待几分钟让 PyPI 索引更新
python -m pip install --upgrade cc-branch
cc-branch --version
cc-branch serve
```

## npm 发布流程

npm 包只适合想用 `npm install -g cc-branch` 的用户。它不是 Web UI 包，也不是 JavaScript SDK；发布物会包含 Python wheel，并在 `postinstall` 时创建本地虚拟环境。

### 步骤 1: 确认 npm 包名

如果 `cc-branch` 包名还没归你所有，先在 npm 上创建包或改成 scoped name，例如 `@geminilight/cc-branch`。改 scoped name 时同步更新 `packaging/npm/package.json` 里的 `name`。

### 步骤 2: 创建 npm token

在 npm 账号里创建 automation token，然后在 GitHub 仓库或 `pypi` environment secrets 里添加：

```text
NPM_TOKEN=<你的 npm automation token>
```

### 步骤 3: 构建 npm tarball

本地验证：

```bash
rm -rf dist/ build/
python -m build
python scripts/build-npm-package.py
npm install -g ./dist/cc-branch-1.0.0.tgz
cc-branch --help
npm uninstall -g cc-branch
```

### 步骤 4: 发布

推荐走 GitHub Actions：

1. 打开 `Publish Python Package` workflow。
2. `publish_to_npm` 设为 `true`。
3. 如果同次也发 PyPI，把 `publish_to_pypi` 设为 `true`，否则保持 `false`。

手动发布也可以：

```bash
npm publish dist/cc-branch-1.0.0.tgz --access public
```

## Homebrew 发布流程

Homebrew 适合作为 CLI 的公开分发方式之一，因为用户不需要先准备 Python、pip 或 pipx。Formula 会用 Homebrew 管理的 Python 创建隔离环境。

### 步骤 1: 准备 tap 仓库

建议创建独立仓库：

```bash
GeminiLight/homebrew-cc-branch
```

用户安装命令会是：

```bash
brew install GeminiLight/cc-branch/cc-branch
```

### 步骤 2: 生成 formula

发布 PyPI 包后，复制模板：

```bash
cp packaging/homebrew/Formula/cc-branch.rb.template ../homebrew-cc-branch/Formula/cc-branch.rb
```

下载发布包和依赖源码包，计算 sha256：

```bash
python -m pip download --no-binary=:all: --dest /tmp/cc-branch-homebrew cc-branch==1.0.0
shasum -a 256 /tmp/cc-branch-homebrew/*
```

把模板里的 `__VERSION__` 和 `__..._SHA256__` 占位符替换成真实版本和 hash。

### 步骤 3: 本地验证 formula

```bash
cd ../homebrew-cc-branch
brew install --build-from-source ./Formula/cc-branch.rb
brew test cc-branch
brew audit --strict --online cc-branch
```

### 步骤 4: 发布 tap

```bash
git add Formula/cc-branch.rb
git commit -m "Update cc-branch to 1.0.0"
git push
```

发布后验证：

```bash
brew install GeminiLight/cc-branch/cc-branch
cc-branch --help
```

## 自动化发布(GitHub Actions)

项目已配置以下 workflows:

- `.github/workflows/ci.yml` — 测试 Python、Web UI，并检查 Python 包构建
- `.github/workflows/publish-python.yml` — 发布 Python 包到 PyPI
- `.github/workflows/release-desktop.yml` — 构建桌面版并上传到 GitHub Releases
- `packaging/homebrew/` — Homebrew tap formula 模板

推荐发布顺序:

1. 推送 tag，例如 `v1.0.0`，触发桌面安装包构建并生成 draft release。
2. workflow 完成各平台安装包、macOS DMG notarization、`latest.json` 汇总和 canary 校验。
3. `publish-release` job 会在 canary 通过后自动发布 GitHub Release，强制设为非 prerelease，并显式标记为 GitHub latest，让用户从默认 Release 入口拿到本次桌面安装包。
4. PyPI 发布后，更新 Homebrew tap formula。

PyPI 推荐使用 Trusted Publishing：

1. 在 PyPI 项目设置中添加 GitHub trusted publisher。
2. Repository 填 `GeminiLight/cc-branch`。
3. Workflow 填 `publish-python.yml`。
4. Environment 填 `pypi`。

当前 workflow 的 OIDC claim 应匹配：

- Owner: `GeminiLight`
- Repository: `cc-branch`
- Workflow: `publish-python.yml`
- Environment: `pypi`

如果 PyPI 报 `invalid-publisher`，说明 PyPI 项目里的 trusted publisher 没有和以上字段完全匹配。GitHub 仓库已经有 `pypi` environment；需要在 PyPI 项目设置中补 trusted publisher，或者临时在 GitHub environment/repository secrets 中配置 `PYPI_API_TOKEN`。workflow 会优先使用 `PYPI_API_TOKEN`，没有 token 时才走 Trusted Publishing。PyPI 包未发布前，不要在 README 或 Release note 中把 `pip install cc-branch` 写成当前可用路径。

桌面版会内置 `cc-branch-backend` sidecar。发布 workflow 会先用 PyInstaller 把 Python 后端打成平台二进制，再交给 Tauri 打包。sidecar 构建后会校验目标架构：macOS 用 `lipo -archs`，Linux 读取 ELF machine，Windows 读取 PE machine，防止把错误架构的产物误命名成目标平台包。用户安装桌面版后不需要额外安装 Python 或 `cc-branch` Python 包。

macOS 桌面版发布使用 signed + notarized `.dmg`。首次配置或迁移到新项目时，按 [`wiki/release-kits/apple-developer-id/`](../wiki/release-kits/apple-developer-id/) 准备 Developer ID Application 证书、App Store Connect API key、GitHub Secrets 和本地 `.gitignore` 防护。

创建 tag 之前先跑桌面发布 preflight，确认版本、远端 tag/release 空位、release workflow、GitHub Actions 已启用、release workflow 显式声明 `permissions: contents: write`，以及 Apple/Tauri secrets 都满足发布条件。发布 tag 必须带 `v` 前缀；preflight 和 GitHub Actions 的手动发布入口都会拒绝裸版本号，避免生成 `1.0.0` 这种不符合仓库规范的 release。手动触发 `workflow_dispatch` 时也会 checkout 到传入的 release tag/ref；如果 tag 不存在，构建会在 checkout 阶段失败，避免从分支 head 给某个 release tag 误打包：

```bash
python scripts/preflight_desktop_release.py v1.0.0 --repo GeminiLight/cc-branch
```

桌面端自动更新使用 Tauri updater。发布 workflow 会先让各平台生成安装包和 `.sig`，再由独立的 `publish-updater-json` job 汇总为完整的 `latest.json`，避免 matrix job 并发覆盖更新元数据。必须同时满足：

1. 发布 workflow 通过 Tauri `--config '{"bundle":{"createUpdaterArtifacts":true}}'` 开启 updater artifact；本地默认配置保持关闭，避免普通开发构建要求私钥。
2. `plugins.updater.pubkey` 使用 Tauri updater 公钥，endpoint 指向 `https://github.com/GeminiLight/cc-branch/releases/latest/download/latest.json`。
3. GitHub Secrets 配置 `TAURI_SIGNING_PRIVATE_KEY` 和 `TAURI_SIGNING_PRIVATE_KEY_PASSWORD`。
4. Release 发布后确认附件中存在 `latest.json` 和平台更新包签名文件。
5. sidecar build 会校验 PyInstaller 输出和复制后的 Tauri sidecar 目标架构，Apple Silicon 包必须包含 `arm64` 后端二进制，Linux 和 Windows x64 包必须包含 `x86_64` 后端二进制；随后 `scripts/smoke-test-backend-sidecar.py` 会在隔离的 `HOME`、`USERPROFILE`、`APPDATA`、`LOCALAPPDATA` 和 XDG 数据目录中启动 sidecar，确认 `/api/info` 返回 `backend_source=bundled-sidecar`，且 `desktop_version`、`desktop_platform`、`desktop_arch` 匹配当前 release tag 和 matrix 平台架构，验证首启项目索引为空且没有逃出隔离目录，并调用 `/api/init` 生成项目 `.cc-branch/config.yaml` / `state.yaml` 后再次确认 `/api/status` 已进入 `ready`。
6. macOS、Linux 和 Windows build jobs 会运行 `scripts/smoke-test-desktop-app.py`，直接启动打包后的 `.app` 或平台主程序，并通过 `/api/info` 的 `backend_source=bundled-sidecar`、`desktop_version`、`desktop_platform`、`desktop_arch`、`config_path` 和 `state_path` 确认桌面壳真的拉起了本次启动的内置后端，而不是误用本机 Python fallback 或误连端口上已有的旧后端；`desktop_version` 必须匹配当前 release tag，`desktop_platform` / `desktop_arch` 必须匹配 matrix 平台架构。release 构建中 Python fallback 被禁用，sidecar 不可用必须暴露为安装包问题，且 smoke JSON 必须带上版本、平台、架构和 `port_mode`，方便定位用户到底下载了哪个桌面包、是否走了普通用户的自动端口启动路径。桌面壳自己的 Rust readiness client 和所有访问 `127.0.0.1` 的 Python backend smoke 请求都必须显式禁用系统代理，避免 CI 或用户机器上的 `HTTP_PROXY` / `HTTPS_PROXY` / `ALL_PROXY` 把本地后端 readiness 检查转发到代理后误报 503 或连接失败。Rust readiness 还必须区分 transient probe 失败和 stale backend 语义不匹配：PyInstaller sidecar 冷启动期间的连接失败要持续重试到超时，`Unexpected backend source` / `Unexpected backend config path` / 版本平台架构不匹配才可以立即失败。后端启动失败面板必须保留 Retry、Copy report 和 Open GitHub Releases 入口；如果桌面壳已经拿到 `desktop_version`，入口和复制报告必须指向对应的 `releases/tag/vX.Y.Z`，不能用浮动 latest 把用户带回旧安装包。随后在隔离的 `HOME`、`USERPROFILE`、`APPDATA`、`LOCALAPPDATA` 和 XDG 数据目录中添加一个空项目、调用 `/api/init`，确认首启生成的 `config.yaml` 和 `state.yaml` 落在该项目的 `.cc-branch/` 下，并再次调用 `/api/status` 验证初始化后的项目已进入 `ready` 状态。正常启动 smoke 之后，workflow 还会复制一个不带 sidecar 的主程序运行 `--expect-startup-failure` 负向验收，要求日志明确出现 `Python fallback is disabled in release builds`，并确认没有任何后端 API 被启动，避免坏安装包被 CI 机器上的 Python 环境掩盖；随后运行 `--expect-startup-failure-recovery`，把原始 sidecar 恢复到同一个主程序旁边后再次启动，要求它回到 `backend_source=bundled-sidecar`、`port_mode=auto`，且桌面版本、平台和架构仍匹配本次 release，证明用户点击 Retry 时不是卡死在首次失败状态，也不是只在 CI 固定端口路径下可恢复；还会运行 `--expect-stale-backend-rejection`，先在同一端口启动一个旧的 backend，再启动桌面壳，要求它用 `Unexpected backend source` 或 `Unexpected backend config path` 拒绝旧后端。
7. macOS build job 还会运行 `scripts/verify-macos-dmg.py --launch-app --verify-installed-copy --verify-stale-backend-rejection`，先确认推荐下载的 DMG 文件名匹配当前 release tag，再挂载 `.dmg`，确认其中只包含精确命名的 `CC Branch.app`，该 `.app` 带有可执行的 `cc-branch-backend` sidecar，且 bundle version 匹配当前 release tag；DMG 根目录还必须包含 `Applications -> /Applications` symlink，保证用户打开 DMG 后能按 macOS 习惯拖拽安装。随后直接从 DMG 内启动 App 验证内置后端就绪，并把同一个 App bundle 复制到临时 `Applications` 目录后再次启动，证明用户拖拽安装后的副本也能拉起内置后端；启动结果必须是 `ok=true`、`backend_source=bundled-sidecar`，且 `desktop_version`、`desktop_platform`、`desktop_arch` 匹配当前 release tag 和 DMG 架构。随后同一个 DMG 内的 App 还会运行 stale backend rejection，要求下载资产级 verifier 也返回 `stale_backend_rejection.ok=true` 和 `expected_error=Unexpected backend`。如果请求了启动、安装副本启动、stale rejection 或 Gatekeeper 验证但不在 macOS runner 上执行，脚本必须失败。
8. Linux 和 Windows build jobs 会运行 `scripts/verify-desktop-installers.py`，检查推荐下载的 `.deb`、`.rpm`、`.AppImage`、`.msi` 和 Windows `.exe` setup 内包含后端 sidecar；`.deb` / `.rpm` 的包内版本必须匹配当前 release tag，AppImage、MSI 和 NSIS setup 的文件名也必须匹配当前 release tag，且主程序和后端 sidecar listing 必须唯一、非空、保留可执行位并位于同一安装目录。Linux 验证还会解包 `.deb` / `.rpm`，再次确认解包后的 `cc-branch` 和 `cc-branch-backend` 位于同一目录，然后从解包后的 `cc-branch` 启动；AppImage 验证会运行用户下载到的 `.AppImage` 本体而不是只运行解包后的 `AppRun`；所有 Linux 启动验收都必须返回 `ok=true`、`backend_source=bundled-sidecar`，且 `desktop_version=当前 release`、`desktop_platform=linux`、`desktop_arch=x86_64`，并在同一下载资产上返回 `stale_backend_rejection.ok=true`。MSI/NSIS 解包后的主程序和后端 sidecar 必须唯一、非空且位于同一目录，解包出的 `cc-branch.exe` 文件版本必须匹配当前 release tag，被启动验证的 MSI/NSIS 也必须返回 `ok=true`、`backend_source=bundled-sidecar`、`desktop_platform=windows`、`desktop_arch=x86_64`，并在同一下载资产上返回 `stale_backend_rejection.ok=true`，证明它不会误连端口上已有的旧后端。macOS DMG、Linux installers 和 Windows installers 的构建期 verifier JSON 都会写入 Step Summary，并随 `desktop-smoke-reports-*` artifact 上传，便于定位用户下载资产不可用的问题。如果请求 Windows 安装包启动验证但不在 Windows runner 上执行，脚本必须失败。
9. `canary-release` job 会下载 draft release 中的 `latest.json`、`SHA256SUMS`、所有平台 updater `.sig` 文件和所有 macOS updater `.app.tar.gz` 包，并运行 `scripts/verify_release_canary.py` 校验平台元数据、每个 `latest.json` 平台引用的签名文件非空且内容匹配对应 signature、非空安装包、每个 macOS updater 包内必须精确包含 `CC Branch.app`，其 `Info.plist` 版本号、主应用二进制和后端 sidecar 必须存在且可执行，并且这些关键 app 成员不能重复、`latest.json` 平台 URL 是否精确指向当前 GitHub repo/tag、`latest.json.notes` 和 release body 中的真实下载链接，并确认两处说明内容一致。`SHA256SUMS` 必须覆盖每一个推荐桌面安装包，方便用户和支持确认下载文件到底是哪一个。验证 JSON 会回显 repo/tag provenance，写入 Step Summary，并上传为 `release-canary-verification` artifact；这个 job 失败时不要把 release 标记为可用。
10. `canary-installers` job 会在 release 仍是 draft 时按 macOS Apple Silicon / macOS Intel / Linux / Windows matrix 下载推荐安装包并做内容级验证；两个 macOS runners 会分别用 `--sample-platform darwin-aarch64` 和 `--sample-platform darwin-x86_64` 启动对应 DMG，并用 `--verify-dmg-installed-copy` 复制安装副本后再次启动，用 `--verify-macos-gatekeeper` 校验下载到的 DMG 已 stapled 且能通过 Gatekeeper。每个平台会上传 `draft-installer-verification-*` JSON artifact，顶层会回显 `repo`/`tag` provenance，且 `launch_backend_sources` 必须来自 `launch.ok=true` 且后端来源为 `bundled-sidecar` 的启动验证，包括 macOS 安装副本启动验证；`launch_desktop_metadata` 必须覆盖同一批被启动验证的下载资产，`desktop_version` 必须等于当前 release 版本，`desktop_platform` / `desktop_arch` 必须匹配对应下载资产的系统和架构；`launch_port_modes` 必须覆盖同一批被启动验证的下载资产且全部为 `auto`，证明验收走的是普通用户启动时的自动端口路径；`stale_backend_rejections` 必须覆盖同一批被启动验证的下载资产；`verification_summary` 必须在顶层汇总这些 label、后端来源、桌面元数据、端口模式和旧后端拒绝证据，并带有 `release_state` 与 `checks` 布尔项，确认 release tag/URL、公开状态、latest 是否指向当前 tag、必需启动、旧后端拒绝、bundled sidecar、auto port 和桌面元数据都已覆盖，再先写入 GitHub Step Summary，方便从 workflow 页面和 artifact 快速判断用户下载路径是否真的可用。这个 job 通过后才允许公开 release。
11. `publish-updater-json` job 会用 `scripts/render_desktop_release_notes.py` 基于真实 release assets 生成下载说明，并把同一份内容写入 `latest.json.notes` 和 draft release body，把 macOS、Windows、Linux 推荐安装包列成可直接点击的下载表；同时会下载这些推荐安装包，生成并上传 `SHA256SUMS`，release notes 必须给出该校验清单的当前 tag 链接。release notes 必须明确告诉用户不要把 GitHub 自动显示的 Source code zip/tar.gz 当成桌面 App 安装包，还要告诉 macOS 用户打开 DMG 后把 `CC Branch` 拖到 Applications，Windows 用户运行 MSI 或 setup EXE，Linux 用户安装 DEB/RPM 或直接运行 AppImage。如果启动仍失败，release notes 必须引导用户从当前 release 表格重新下载对应平台安装包，而不是跳到浮动的 latest release；真实下载链接也只能指向当前 tag 的推荐安装包，不能指向 `/releases/latest/download/...`、旧 tag 或非推荐资产；每个推荐安装包还必须出现在平台下载表的对应行里，不能只散落在正文里。这些规则会被 canary/live release verification 重新验证，防止手工改 release body 或 updater notes 时退回错误文案。release notes 还必须引导用户点击启动错误面板里的 Copy report，并在提交 issue 时附上报告，避免把桌面用户推回终端排查。推荐安装包匹配必须唯一，`.sig`、`.blockmap` 等辅助资产不会被当成用户下载入口，`SHA256SUMS` 只作为校验清单链接出现。
12. `verify-live-release` job 会在 release 公开后从 GitHub live release 重新下载用户可见资产，并重新校验公开 release body 的真实下载链接；同时用 `--require-latest` 等待并确认 GitHub `latest` 已指向本次发布 tag，用 `--require-public` 明确拒绝仍处于 draft 或 prerelease 状态的 release：Apple Silicon 和 Intel 两个 macOS runners 会分别验证对应推荐 DMG 已通过 Gatekeeper、DMG 内包含可执行后端 sidecar，并启动对应架构的 App 做后端 smoke test；Linux runner 会验证 `.deb`、`.rpm`、`.AppImage`，Windows runner 会验证 `.msi` 和 `.exe` setup。每个平台会上传 `live-installer-verification-*` JSON artifact，Step Summary 会先展示 `verification_summary` 再展示完整 JSON，顶层会回显 `repo`/`tag` provenance，且 `release_state`、`launch_backend_sources`、`launch_desktop_metadata`、`launch_port_modes`、`stale_backend_rejections` 和 `verification_summary` 分别是发布后验收公开/latest 入口、bundled sidecar、用户下载资产版本/平台/架构、自动端口启动路径、拒绝旧后端与快速审计结论的证据。如果 release 已公开但 live 下载验收没有全部成功，`rollback-live-release` job 会把该 release 改回 draft/prerelease，避免坏安装包继续暴露给用户。

发布后再从 GitHub live release 做一次用户下载级验证：

```bash
python scripts/verify_github_release.py v1.0.0 --repo GeminiLight/cc-branch --expected-version 1.0.0 --require-latest --require-public
```

这个脚本会读取 GitHub release asset metadata，下载 `latest.json`、`SHA256SUMS`、所有 `latest.json` 引用平台的 `.sig`、所有 macOS updater 包，并复用 canary 规则确认平台元数据、推荐下载资产、每个平台签名文件与 metadata 一致、版本号、每个 updater `.app.tar.gz` 内 `Info.plist` 版本号和内置后端 sidecar，以及 `SHA256SUMS` 是否覆盖每个推荐桌面安装包。加上 `--require-latest` 时，它还会等待 GitHub 默认 latest release 指向正在验收的 tag，避免用户从默认入口下载到旧版本；加上 `--require-public` 时，它会拒绝 draft 或 prerelease，避免把还不可从默认入口稳定下载的发布误判为完成。在 macOS 上它还会下载 Apple Silicon 和 Intel 两个推荐 `.dmg`，挂载后确认 DMG 内的 `.app` 带有可执行后端 sidecar；加上 `--launch-dmg-app` 时还会直接从当前选定架构的 DMG 内启动 App 并等待后端 API 就绪，同时对该 DMG 运行 stale backend rejection；加上 `--verify-dmg-installed-copy` 时会把 DMG 内的 App bundle 复制到临时 `Applications` 目录并从复制后的副本启动，模拟用户拖拽安装后的真实路径；加上 `--verify-macos-gatekeeper` 时会运行 `xcrun stapler validate` 和 `spctl` 验证下载到的 DMG 已满足用户打开要求。在 Linux/Windows runner 上分别使用 `--verify-linux-installers` 和 `--verify-windows-installer` 检查推荐安装包内容；Linux 验证可用 `--launch-linux-packages` 解包并启动 `.deb` / `.rpm` 里的主程序，也可用 `--launch-linux-appimage` 启动下载到的 AppImage；Windows 验证会同时覆盖 `.msi` 和 `.exe` setup，并可用 `--launch-windows-msi` / `--launch-windows-nsis` 分别启动验证。输出 JSON 顶层的 `release_state` 会汇总 repo、tag、URL、public 状态、latest 检查结果，以及本次命令是否要求 public/latest；`launch_backend_sources` 会汇总所有已执行且 `ok=true` 的启动检查后端来源，`launch_desktop_metadata` 会汇总同一批启动检查返回的 `desktop_version`、`desktop_platform` 和 `desktop_arch`，并要求版本等于当前 release、平台和架构匹配下载资产标签；`launch_port_modes` 会汇总同一批启动检查的端口模式，并要求全部为 `auto`，避免把 CI 固定端口路径误当成普通用户启动路径；`stale_backend_rejections` 会汇总同一批启动检查的旧后端拒绝证据；`verification_summary` 会把这些证据、必需 label 和 `checks` 布尔项再汇总到一个顶层对象，其中 `public_release_requirement_met` 与 `latest_release_requirement_met` 会直接显示当前验收阶段对用户默认下载入口的要求是否满足，避免 draft 阶段因为尚未公开而显示成失败；任何请求过的启动检查缺少对应 label、启动检查失败、报告 `python-fallback`、缺少 `backend_source`、缺少或不匹配桌面版本/平台/架构、缺少或不是 `auto` 的 `port_mode`，或缺少对应 stale rejection evidence，都会让验收失败。

macOS DMG 还会在 Tauri 打包后单独执行一次 DMG 本体 notarization 和 stapling，然后覆盖上传 Release 里的 DMG。验证时不要只检查 `.app`，也要对 `.dmg` 运行 `spctl -a -vv -t open --context context:primary-signature <file>.dmg`。

## 发布检查清单

发布前确认:

- [ ] 更新了版本号 (`pyproject.toml` + `cc_branch/__init__.py`)
- [ ] 更新了 CHANGELOG
- [ ] 发布 preflight 通过: `python scripts/preflight_desktop_release.py v1.0.0 --repo GeminiLight/cc-branch`。输出里的 `quality_gates` 必须全部为 `true`，尤其是 `release_workflow_action_refs`、`release_workflow_bash_syntax`、`release_workflow_concurrency`、`desktop_smoke_report_artifact_upload`、`desktop_bundle_output_cleanup`、`desktop_backend_port_retry`、`tauri_backend_no_proxy_loopback`、`tauri_backend_transient_probe_retry`、`desktop_webview_fetch_diagnostics`、`desktop_csp_local_backend`、`desktop_backend_ignores_user_web_token`、`installer_sidecar_same_directory`、`startup_failure_recovery_auto_port`、`desktop_smoke_no_proxy_loopback`、`packaged_desktop_auto_port_smoke`、`desktop_smoke_port_mode_report`、`release_verification_expected_version`、`missing_sidecar_failure_smoke`、`backend_sidecar_desktop_metadata_smoke`、`backend_failure_current_release_link`、`packaged_desktop_metadata_value_smoke_per_platform`、`packaged_desktop_missing_sidecar_smoke_per_platform`、`packaged_desktop_startup_failure_recovery_smoke_per_platform`、`packaged_desktop_startup_failure_recovery_report`、`Windows_missing_sidecar_clean_temp_directory`、`packaged_desktop_stale_backend_rejection_smoke_per_platform`、`packaged_desktop_startup_diagnostics_metadata`、`standalone_installer_launch_desktop_metadata`、`GitHub_download_launch_desktop_metadata`、`GitHub_download_launch_port_mode`、`GitHub_download_verification_summary`、`release_verification_summary_step_summary`、`release_notes_platform_install_copy`、`release_notes_source_code_warning`、`release_notes_copy_report_support`、`macOS_DMG_applications_shortcut`、`macOS_DMG_installed_copy_launch`、`macOS_DMG_stale_backend_rejection`、`Linux_DEB_launch`、`Linux_DEB_stale_backend_rejection`、`Linux_RPM_launch`、`Linux_RPM_stale_backend_rejection`、`Linux_AppImage_stale_backend_rejection`、`Windows_MSI_stale_backend_rejection`、`Windows_NSIS_stale_backend_rejection`、`bundled_backend_sidecar_smoke`、`draft_installer_canary`、`live_GitHub_download_verification` 和 `live_release_rollback_on_failed_verification`。
- [ ] 运行了所有测试: `python -m unittest discover tests`
- [ ] 前端构建正常: `python scripts/build-webui.py`
- [ ] 桌面后端 sidecar 构建正常且架构匹配: `python scripts/build-desktop-sidecar.py`
- [ ] 清理了旧构建: `rm -rf dist/ build/`
- [ ] Python 包构建成功: `python -m build`
- [ ] 检查通过: `twine check dist/*`
- [ ] 在测试环境验证过
- [ ] 更新并验证 Homebrew formula（如果本次要同步发布 tap）
- [ ] 创建了 git tag: `git tag v1.0.0 && git push origin v1.0.0`
- [ ] 发布后在 GitHub Release 页面确认桌面版附件已上传
- [ ] 发布后确认自动更新元数据 `latest.json` 已上传，`canary-release`、`canary-installers` 和 `verify-live-release` jobs 通过，桌面端设置页可以检查更新
- [ ] 发布后确认 PyPI 项目可安装；如果 PyPI 仍未发布，Release note 和 README 必须明确标注 CLI 包暂不可用

## 版本管理

遵循语义化版本(Semantic Versioning):

- `0.1.0` → `0.1.1`: 补丁版本(bug 修复)
- `0.1.0` → `0.2.0`: 次版本(新功能,向后兼容)
- `0.1.0` → `1.0.0`: 主版本(破坏性变更)

## 常见问题

### Q: 上传失败,提示文件已存在?

**原因**: PyPI 不允许覆盖已发布的版本。

**解决**: 更新版本号,重新构建和上传。

### Q: 如何撤回已发布的版本?

**答**: PyPI 不支持删除已发布的版本(防止破坏依赖)。只能:
1. 发布新版本修复问题
2. 或者联系 PyPI 管理员(仅限严重安全问题)

### Q: 如何发布预发布版本?

**答**: 使用预发布版本号:

```toml
version = "0.2.0rc1" # release candidate
```

用户需要明确指定才能安装:
```bash
python -m pip install cc-branch==0.2.0rc1
```

## 参考资源

- [Python Packaging User Guide](https://packaging.python.org/)
- [PyPI Help](https://pypi.org/help/)
- [Semantic Versioning](https://semver.org/)
- [twine Documentation](https://twine.readthedocs.io/)
