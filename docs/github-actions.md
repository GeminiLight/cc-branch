# GitHub Actions 配置指南

本项目的自动化流程分为三类：CI、Python 包发布、桌面端发布。Homebrew tap 通过 `packaging/homebrew/` 中的 formula 模板维护。当前不发布 npm 包；`apps/web` 和 `apps/desktop` 是产品工程，不是 npm CLI 包。

## 工作流

### CI (`ci.yml`)

触发条件：

- push 到 `main` / `master` / `develop`
- pull request 到 `main` / `master` / `develop`

检查内容：

- Python 3.10 / 3.11 / 3.12
- Ubuntu / macOS
- Python 单测和 CLI smoke test
- Web UI lint / test / build
- Python wheel / sdist 构建和 `twine check`

### Python 发布 (`publish-python.yml`)

触发条件：

- GitHub Release published
- 手动触发

发布内容：

- 运行 Python 测试
- 运行 Web UI 测试
- 构建并同步 Web UI 静态资源
- 构建 Python package
- 上传构建产物到 workflow artifacts
- 发布到 PyPI

推荐使用 PyPI Trusted Publishing：

1. 在 GitHub 仓库创建 `pypi` environment。
2. 在 PyPI 项目设置里添加 trusted publisher。
3. Repository 填 `GeminiLight/cc-branch`。
4. Workflow 填 `publish-python.yml`。
5. Environment 填 `pypi`。

如果暂时不能使用 Trusted Publishing，需要把 workflow 改为 token 发布，并配置 `PYPI_API_TOKEN`。

### 桌面端发布 (`release-desktop.yml`)

触发条件：

- push tag，例如 `v0.1.0`
- 手动触发，并输入 release tag

构建目标：

- macOS Apple Silicon
- macOS Intel
- Linux
- Windows

workflow 会先用 PyInstaller 构建 `cc-branch-backend` sidecar，再创建或更新 GitHub draft release，并上传 Tauri 构建产物。

桌面端安装包内置 CC Branch 后端。用户不需要额外安装 Python 或 `cc-branch` Python 包。Agent CLI、tmux、git 等外部开发工具仍按用户环境检测和引导。

## 推荐发布流程

1. 更新版本号：

```bash
vim pyproject.toml
vim apps/desktop/src-tauri/tauri.conf.json
vim apps/desktop/src-tauri/Cargo.toml
```

2. 更新 `CHANGELOG.md`。

3. 本地验证：

```bash
python -m unittest discover tests
cd apps/web && npm run lint && npm run test && npm run build
cd ../..
python scripts/build-webui.py
python scripts/build-desktop-sidecar.py
python -m build
twine check dist/*
```

4. 创建并推送 tag：

```bash
git tag -a v0.1.0 -m "Release v0.1.0"
git push origin v0.1.0
```

5. 等待 `Release Desktop App` 完成，检查 draft release 中的安装包。

6. 发布 GitHub Release，触发 `Publish Python Package`。

7. PyPI 发布后，更新 Homebrew tap formula。

## npm 发布状态

当前不要发布 npm 包。

原因：

- Web UI 是内置前端，不是 SDK。
- Desktop 是 Tauri 应用，不是 npm CLI。
- CLI 主实现是 Python 包，推荐安装方式是 `pipx` 或 Homebrew。

只有在新增真正的 npm wrapper 包后，才应该添加 `npm publish` workflow。这个 wrapper 至少需要明确处理 Python 后端安装、版本同步和跨平台 PATH 问题。

## 故障排除

### PyPI 发布失败：Trusted Publishing 未配置

检查 PyPI 项目的 trusted publisher 设置是否匹配：

- Repository
- Workflow filename
- Environment

### PyPI 发布失败：版本已存在

PyPI 不允许覆盖已有版本。更新 `pyproject.toml` 版本号后重新发布。

### 桌面端构建失败

优先看对应平台日志：

- Linux 常见是 WebKit / appindicator 依赖问题
- macOS 常见是 target 或签名问题
- Windows 常见是 Rust / WebView2 环境问题

当前 workflow 未做代码签名和 notarization。正式面向普通用户分发 macOS / Windows 安装包前，需要补签名链路。

## 参考资源

- [GitHub Actions 文档](https://docs.github.com/en/actions)
- [PyPI Trusted Publishing](https://docs.pypi.org/trusted-publishers/)
- [Tauri 发布指南](https://tauri.app/distribute/)
