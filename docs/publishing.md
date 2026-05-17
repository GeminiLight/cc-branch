# 发布与分发

本文档说明如何发布 CC Branch，并维护几种用户安装路径：

- GitHub Releases：桌面版安装包
- Homebrew tap：macOS / Linux 推荐 CLI 安装方式
- PyPI：Python 用户通过 `pipx install cc-branch` 安装
- npm：当前不发布。`apps/web` 和 `apps/desktop` 是应用工程，不是可安装 CLI 包。

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
version = "0.1.0"  # 更新这里
```

### 步骤 2: 清理旧构建

```bash
rm -rf dist/ build/ *.egg-info
```

### 步骤 3: 构建分发包

```bash
python -m build
```

这会在 `dist/` 目录生成:
- `cc_branch-0.1.0.tar.gz` (源码分发)
- `cc_branch-0.1.0-py3-none-any.whl` (wheel 分发)

### 步骤 4: 检查构建结果

```bash
twine check dist/*
```

应该显示:
```
Checking dist/cc_branch-0.1.0.tar.gz: PASSED
Checking dist/cc_branch-0.1.0-py3-none-any.whl: PASSED
```

### 步骤 5: 测试发布(推荐)

先发布到测试环境:

```bash
twine upload --repository testpypi dist/*
```

测试安装:

```bash
pipx install --index-url https://test.pypi.org/simple/ cc-branch
cc-branch --version
pipx uninstall cc-branch
```

### 步骤 6: 正式发布

确认测试无误后,发布到生产环境:

```bash
twine upload dist/*
```

### 步骤 7: 验证发布

```bash
# 等待几分钟让 PyPI 索引更新
pipx install cc-branch
cc-branch --version
```

## Homebrew 发布流程

Homebrew 适合作为 CLI 的主推安装方式，因为用户不需要先准备 Python、pip 或 pipx。Formula 会用 Homebrew 管理的 Python 创建隔离环境。

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
python -m pip download --no-binary=:all: --dest /tmp/cc-branch-homebrew cc-branch==0.1.0
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
git commit -m "Update cc-branch to 0.1.0"
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

1. 推送 tag，例如 `v0.1.0`，触发桌面安装包构建并生成 draft release。
2. 检查 GitHub Release 里的桌面安装包。
3. 发布 GitHub Release，触发 PyPI 发布。
4. PyPI 发布后，更新 Homebrew tap formula。

PyPI 推荐使用 Trusted Publishing：

1. 在 PyPI 项目设置中添加 GitHub trusted publisher。
2. Repository 填 `GeminiLight/cc-branch`。
3. Workflow 填 `publish-python.yml`。
4. Environment 填 `pypi`。

如果暂时不用 Trusted Publishing，需要把 workflow 改回 token 模式，并在 GitHub Secrets 中配置 `PYPI_API_TOKEN`。

桌面版会内置 `cc-branch-backend` sidecar。发布 workflow 会先用 PyInstaller 把 Python 后端打成平台二进制，再交给 Tauri 打包。用户安装桌面版后不需要额外安装 Python 或 `cc-branch` Python 包。

## 发布检查清单

发布前确认:

- [ ] 更新了版本号 (`pyproject.toml` + `cc_branch/__init__.py`)
- [ ] 更新了 CHANGELOG
- [ ] 运行了所有测试: `python -m unittest discover tests`
- [ ] 前端构建正常: `python scripts/build-webui.py`
- [ ] 桌面后端 sidecar 构建正常: `python scripts/build-desktop-sidecar.py`
- [ ] 清理了旧构建: `rm -rf dist/ build/`
- [ ] Python 包构建成功: `python -m build`
- [ ] 检查通过: `twine check dist/*`
- [ ] 在测试环境验证过
- [ ] 更新并验证 Homebrew formula（如果本次要同步发布 tap）
- [ ] 创建了 git tag: `git tag v0.1.0 && git push --tags`
- [ ] 发布后在 GitHub Release 页面确认桌面版附件已上传

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
pipx install cc-branch==0.2.0rc1
```

## 参考资源

- [Python Packaging User Guide](https://packaging.python.org/)
- [PyPI Help](https://pypi.org/help/)
- [Semantic Versioning](https://semver.org/)
- [twine Documentation](https://twine.readthedocs.io/)
