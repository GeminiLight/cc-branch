# Apple Developer ID 发布配置 Kit

这个目录是一套可复用的 macOS 桌面端发布配置说明。以后新项目需要发布 signed + notarized `.dmg` 时，可以直接复制整个目录，再按项目名调整路径和 workflow。

核心原则：Apple 签名文件只放在本机安全目录或 GitHub Secrets。不要把 `.p8`、`.p12`、私钥、CSR、下载的证书文件提交进仓库。

## 目录内容

| 文件 | 用途 |
| --- | --- |
| [`README.md`](README.md) | 完整配置流程 |
| [`gitignore-snippet.txt`](gitignore-snippet.txt) | 可复制到新项目 `.gitignore` 的防误传规则 |
| [`github-secrets.md`](github-secrets.md) | GitHub Secrets 清单和填写说明 |
| [`tauri-macos-workflow-snippet.yml`](tauri-macos-workflow-snippet.yml) | Tauri macOS 签名和 notarization workflow 片段 |
| [`tauri-entitlements.plist`](tauri-entitlements.plist) | PyInstaller sidecar 常用 macOS entitlements 模板 |

## 需要准备什么

| 项目 | 来源 | 是否敏感 | 用途 |
| --- | --- | --- | --- |
| Developer ID Application 证书 | Apple Developer Portal | 公共证书本身风险较低，但配套私钥敏感 | 给 macOS App 签名 |
| `.p12` 文件 | 本机 Keychain 或 OpenSSL 导出 | 是 | GitHub Actions 导入签名证书 |
| `.p12` 密码 | 自己生成 | 是 | 解锁签名证书 |
| App Store Connect API key `.p8` | App Store Connect | 是 | notarization 公证 |
| API Key ID | App Store Connect | 低敏，但建议放 Secret | notarization |
| API Issuer ID | App Store Connect | 低敏，但建议放 Secret | notarization |
| Apple Team ID | Apple Developer 账号 | 低敏，但建议放 Secret | 签名和公证元信息 |

## 本机文件放哪里

建议所有签名材料都放在仓库外。新项目可以把 `cc-branch` 换成自己的项目名：

```bash
mkdir -p ~/.cc-branch-secrets/apple-signing
chmod 700 ~/.cc-branch-secrets ~/.cc-branch-secrets/apple-signing
```

推荐命名：

```text
~/.cc-branch-secrets/apple-signing/
  developer_id_application_YYYYMMDD.key
  developer_id_application_YYYYMMDD.certSigningRequest
  developer_id_application_YYYYMMDD.cer
  developer_id_application_YYYYMMDD.p12
  developer_id_application_YYYYMMDD.p12.password
  AuthKey_KEYID.p8
```

不要把这些文件放进项目目录。新项目也应该把 [`gitignore-snippet.txt`](gitignore-snippet.txt) 复制进 `.gitignore`，作为第二层保护。

## 生成 Developer ID Application 证书

### 方式 A：Keychain Access

适合习惯 Apple 官方图形界面的项目。

1. 打开 Keychain Access。
2. 选择 **Certificate Assistant** -> **Request a Certificate From a Certificate Authority**。
3. 填 Apple Developer 邮箱和 common name。
4. 选择 **Saved to disk**，生成 CSR。
5. 进入 Apple Developer：
   **Certificates, Identifiers & Profiles** -> **Certificates** -> **+** -> **Developer ID Application**。
6. 上传 CSR，下载 `.cer`。
7. 双击 `.cer`，让 Keychain 把证书和本机私钥配对。
8. 在 Keychain Access 里导出证书和私钥为 `.p12`。

### 方式 B：OpenSSL

适合想把私钥、CSR、`.p12` 都放在可控本机目录的项目。

```bash
SIGNING_DIR="$HOME/.cc-branch-secrets/apple-signing"
NAME="developer_id_application_$(date +%Y%m%d)"

openssl genrsa -out "$SIGNING_DIR/$NAME.key" 2048
chmod 600 "$SIGNING_DIR/$NAME.key"

openssl req -new \
  -key "$SIGNING_DIR/$NAME.key" \
  -out "$SIGNING_DIR/$NAME.certSigningRequest" \
  -subj "/CN=Developer ID Application"
```

把 CSR 上传到 Apple Developer，下载 Developer ID Application `.cer` 后，生成 `.p12`：

```bash
SIGNING_DIR="$HOME/.cc-branch-secrets/apple-signing"
NAME="developer_id_application_YYYYMMDD"

openssl x509 \
  -in "$SIGNING_DIR/$NAME.cer" \
  -inform DER \
  -out "$SIGNING_DIR/$NAME.pem"

openssl rand -base64 32 > "$SIGNING_DIR/$NAME.p12.password"
chmod 600 "$SIGNING_DIR/$NAME.p12.password"

openssl pkcs12 -export \
  -inkey "$SIGNING_DIR/$NAME.key" \
  -in "$SIGNING_DIR/$NAME.pem" \
  -out "$SIGNING_DIR/$NAME.p12" \
  -password "file:$SIGNING_DIR/$NAME.p12.password"
chmod 600 "$SIGNING_DIR/$NAME.p12"
```

使用前先确认证书类型：

```bash
openssl x509 -in "$SIGNING_DIR/$NAME.cer" -inform DER -noout -subject -issuer -dates
```

`subject` 必须包含 `Developer ID Application`。公开发布不要用 `Apple Development` 证书。

## 生成 App Store Connect API Key

1. 打开 App Store Connect。
2. 进入 **Users and Access** -> **Integrations** -> **App Store Connect API**。
3. 创建或选择一个有 notarization 权限的 API key。
4. 下载 `.p8` 文件。Apple 通常只允许下载一次。
5. 记录：
   - Key ID
   - Issuer ID
   - Apple Developer Team ID

本机验证 API key：

```bash
xcrun notarytool history \
  --key "$HOME/.cc-branch-secrets/apple-signing/AuthKey_KEYID.p8" \
  --key-id "KEYID" \
  --issuer "ISSUER_ID"
```

如果能返回 notarization history，或者成功返回空历史，说明 API key 可用。

## 配置 GitHub Secrets

把本机文件转成单行 base64：

```bash
base64 -i "$SIGNING_DIR/$NAME.p12" | tr -d '\n' | pbcopy
```

粘贴到 `APPLE_CERTIFICATE_BASE64`。

```bash
base64 -i "$SIGNING_DIR/AuthKey_KEYID.p8" | tr -d '\n' | pbcopy
```

粘贴到 `APPLE_API_KEY_BASE64`。

完整 secret 列表见 [`github-secrets.md`](github-secrets.md)。

## GitHub Actions 应该做什么

Tauri 项目的 macOS release job 应该：

1. 配置 `bundle.macOS.entitlements`。如果项目用 PyInstaller one-file sidecar，可以从 [`tauri-entitlements.plist`](tauri-entitlements.plist) 开始。
2. 构建 `.dmg`，不要只构建 `.app`。
3. 把 `.p12` 导入临时 keychain。
4. 设置 `APPLE_SIGNING_IDENTITY`。
5. 把 `APPLE_API_KEY_BASE64` 解码成 `AuthKey_KEYID.p8`。
6. 导出这些环境变量：
   - `APPLE_API_KEY`
   - `APPLE_API_KEY_PATH`
   - `APPLE_API_ISSUER`
   - `APPLE_TEAM_ID`
7. 使用 `--bundles dmg` 运行 Tauri build。

可复用片段见 [`tauri-macos-workflow-snippet.yml`](tauri-macos-workflow-snippet.yml)。CC Branch 的完整参考实现是 `.github/workflows/release-desktop.yml`。

## 发布前检查

推送 release tag 前确认：

- [ ] `.gitignore` 已包含 [`gitignore-snippet.txt`](gitignore-snippet.txt) 的规则。
- [ ] 没有 `.p8`、`.p12`、`.p12.password`、`.key`、`.pem`、`.cer`、CSR 文件被 Git 跟踪。
- [ ] `git status --short` 不显示本地签名文件。
- [ ] `APPLE_CERTIFICATE_BASE64` 来自 Developer ID Application `.p12`。
- [ ] `APPLE_API_KEY_BASE64` 来自 App Store Connect `.p8`。
- [ ] 本机 `xcrun notarytool history` 能用 API key 跑通。
- [ ] workflow 产物是 signed + notarized `.dmg`。
- [ ] 如果内置 PyInstaller sidecar，安装后的 app 能实际启动 sidecar，而不是只通过 notarization。

检查命令：

```bash
git ls-files | rg '\.(p8|p12|p12\.password|key|pem|cer|csr|certSigningRequest|mobileprovision|provisionprofile)$'
git status --short
```

第一条命令应该没有任何输出。

## 常见错误

### `Could not find a Developer ID Application signing identity`

通常是证书类型错了，或者 `.p12` 没有包含匹配私钥。重新导出 `Developer ID Application` 证书和它对应的私钥。

### `Team ID must be at least 3 characters`

缺少 `APPLE_TEAM_ID`。

### notarization 返回 `401`

检查 `APPLE_API_KEY_ID`、`APPLE_API_ISSUER` 和 `.p8` 是否来自同一个 App Store Connect API key。也确认解码后的文件名类似 `AuthKey_KEYID.p8`。

### `.app.tar.gz` 能出，但 `.dmg` 失败

这通常不是最终方案。公开 macOS 发布应该以 signed + notarized `.dmg` 为目标。优先修复签名和公证，而不是用 `.app.tar.gz` 代替。

### 安装包能打开，但前端提示 API 连不上

如果使用 PyInstaller one-file sidecar，检查 app 日志里是否出现 `Failed to load Python shared library` 和 `different Team IDs`。这是 hardened runtime 的 library validation 拦截了 sidecar 解压出来的 Python runtime。给 macOS 签名配置加 `com.apple.security.cs.disable-library-validation` entitlement 后重新签名和公证。
