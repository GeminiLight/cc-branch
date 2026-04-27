# GitHub 发布准备清单

## ✅ 已完成的优化

### 📄 核心文档
- [x] **LICENSE** - MIT 许可证
- [x] **README.md** - 完整的项目介绍（带徽章）
- [x] **README.zh.md** - 中文版本
- [x] **CHANGELOG.md** - 版本变更记录
- [x] **CONTRIBUTING.md** - 贡献指南
- [x] **SECURITY.md** - 安全政策

### 🔧 项目配置
- [x] **pyproject.toml** - 完善的项目元数据
  - 项目 URLs（主页、文档、问题追踪）
  - 开发依赖配置
  - pytest、coverage、ruff 配置
  - 详细的分类器
- [x] **.gitignore** - 完整的忽略规则
- [x] **MANIFEST.in** - 包分发清单

### 🤖 GitHub 配置
- [x] **.github/workflows/ci.yml** - CI 流水线
  - 多平台 Python 测试（Ubuntu、macOS）
  - 多 Python 版本（3.10、3.11、3.12）
  - Web UI lint / test / build
  - Python 包构建检查
- [x] **.github/workflows/publish-python.yml** - PyPI 发布
- [x] **.github/workflows/release-desktop.yml** - 桌面安装包构建
  - 使用 PyInstaller 构建内置 `cc-branch-backend` sidecar
  - Tauri 安装包内置后端，不要求用户额外安装 Python 包
- [x] **.github/ISSUE_TEMPLATE/** - Issue 模板
  - bug_report.md
  - feature_request.md
- [x] **.github/PULL_REQUEST_TEMPLATE.md** - PR 模板

### 📊 徽章
- [x] License 徽章
- [x] Python 版本徽章
- [x] tmux 徽章
- [x] CI 状态徽章
- [x] Codecov 徽章

## 📋 发布前检查清单

### 1. 代码质量
```bash
# 运行所有测试
python -m pytest tests/ -v

# 检查代码风格
pip install ruff
ruff check cc_branch/ tests/

# 检查测试覆盖率
python -m pytest tests/ --cov=cc_branch --cov-report=term
```

### 2. 文档检查
- [ ] README.md 中的所有链接都有效
- [ ] 示例代码可以运行
- [ ] 安装说明准确
- [ ] Homebrew tap 命令和 PyPI 命令都与当前发布状态一致
- [ ] 所有命令示例正确

### 3. 版本管理
- [ ] 更新 `pyproject.toml` 中的版本号
- [ ] 更新 `CHANGELOG.md`
- [ ] 创建 git tag

### 4. GitHub 设置
- [ ] 创建 GitHub 仓库
- [ ] 设置仓库描述和主题
- [ ] 启用 Issues 和 Discussions
- [ ] 配置 branch protection rules（可选）
- [ ] 添加 Topics 标签

## 🚀 发布步骤

### 步骤 1：创建 GitHub 仓库

```bash
# 在 GitHub 上创建新仓库（不要初始化 README）
# 仓库名：cc-branch
# 描述：Multi-agent workspace orchestrator for shell and tmux runtimes
```

### 步骤 2：推送代码

```bash
# 添加远程仓库
git remote add origin https://github.com/GeminiLight/cc-branch.git

# 推送代码
git push -u origin main

# 推送标签（如果有）
git push --tags
```

### 步骤 3：配置 GitHub 仓库

1. **Settings → General**
   - 添加 Description
   - 添加 Website（如果有）
   - 添加 Topics: `tmux`, `cli`, `agents`, `orchestrator`, `ai`, `workspace`, `python`

2. **Settings → Features**
   - ✅ Issues
   - ✅ Discussions（推荐）
   - ✅ Projects（可选）

3. **Settings → Secrets and variables → Actions**
   - 如果使用 PyPI Trusted Publishing：创建 `pypi` environment，并在 PyPI 侧配置 trusted publisher
   - 如果暂时使用 token 发布：添加 `PYPI_API_TOKEN`

### 步骤 4：创建首个 Release

```bash
# 创建标签，触发桌面端 draft release 构建
git tag -a v0.1.0 -m "Release v0.1.0: Initial public release"
git push origin v0.1.0
```

在 GitHub 上：
1. 等待 `Release Desktop App` workflow 完成
2. 进入 Releases，检查 draft release 的安装包附件
3. 标题：`v0.1.0 - Initial Release`
4. 描述：从 CHANGELOG.md 复制内容
5. 发布 release，触发 PyPI 发布

### 步骤 5：发布到 PyPI

发布 GitHub Release 后，`.github/workflows/publish-python.yml` 会构建并发布到 PyPI。

当前推荐 PyPI Trusted Publishing；如果仓库还没有配置，需要先在 PyPI 项目设置中添加 trusted publisher，workflow 名称为 `publish-python.yml`，environment 为 `pypi`。

### 步骤 6：更新 Homebrew tap（推荐）

```bash
# 在 PyPI 包发布后
python -m pip download --no-binary=:all: --dest /tmp/cc-branch-homebrew cc-branch==0.1.0
shasum -a 256 /tmp/cc-branch-homebrew/*

# 复制并更新 formula 模板
cp packaging/homebrew/Formula/cc-branch.rb.template ../homebrew-cc-branch/Formula/cc-branch.rb
```

然后在 tap 仓库中验证：

```bash
brew install --build-from-source ./Formula/cc-branch.rb
brew test cc-branch
brew audit --strict --online cc-branch
```

### npm 发布状态

当前不发布 npm 包。`apps/web` 和 `apps/desktop` 是产品工程，`private: true` 是正确的。只有在新增真正的 npm CLI wrapper 后，才应该添加 `npm publish` workflow。

## 📢 发布后推广

### 社交媒体
- [ ] 在 Twitter/X 上发布
- [ ] 在 Reddit r/Python 发布
- [ ] 在相关社区分享

### 文档站点（可选）
- [ ] 使用 GitHub Pages 托管文档
- [ ] 使用 Read the Docs

### 示例和教程
- [ ] 创建视频演示
- [ ] 写博客文章
- [ ] 添加更多示例

## 🔍 质量指标

### 目标
- [ ] CI 通过率 > 95%
- [ ] 测试覆盖率 > 80%
- [ ] 文档完整性 > 90%
- [ ] Issue 响应时间 < 48h

### 监控
- GitHub Actions 状态
- Codecov 报告
- Issue/PR 活动
- Star/Fork 增长

## 📝 维护计划

### 定期任务
- **每周**：检查并回复 Issues/PRs
- **每月**：更新依赖版本
- **每季度**：发布新版本
- **每年**：审查和更新文档

### 版本策略
- **Patch (0.1.x)**: Bug 修复
- **Minor (0.x.0)**: 新功能（向后兼容）
- **Major (x.0.0)**: 破坏性更改

## 🎯 下一步改进

### 短期（1-2 周）
- [ ] 添加更多单元测试
- [ ] 改进错误消息
- [ ] 添加更多示例配置

### 中期（1-2 月）
- [ ] 添加更多 profile 模板
- [ ] 实现 agent 认证检查
- [ ] 添加配置验证

### 长期（3-6 月）
- [ ] 构建 Web UI
- [ ] 支持远程 session
- [ ] 插件系统

## 📚 参考资源

- [GitHub 开源指南](https://opensource.guide/)
- [Python 打包指南](https://packaging.python.org/)
- [语义化版本](https://semver.org/)
- [Keep a Changelog](https://keepachangelog.com/)
- [Conventional Commits](https://www.conventionalcommits.org/)

---

**准备就绪！** 🎉 项目已经具备了所有标准开源项目应有的文件和配置。
