# GitHub Secrets 清单

这些 secrets 配在 GitHub repository 的 **Settings** -> **Secrets and variables** -> **Actions**。

不要把 secret 值写进文档、issue、PR、commit message 或 workflow 明文。

## 必需 Secrets

| Secret | 值 | 说明 |
| --- | --- | --- |
| `APPLE_CERTIFICATE_BASE64` | `.p12` 文件的单行 base64 | 必须是 Developer ID Application 证书和匹配私钥导出的 `.p12` |
| `APPLE_CERTIFICATE_PASSWORD` | `.p12` 导出密码 | 用于 CI 导入签名证书 |
| `APPLE_API_KEY_BASE64` | App Store Connect `.p8` 文件的单行 base64 | 用于 notarization |
| `APPLE_API_KEY_ID` | App Store Connect Key ID | 例如 `NQ8ZM3WLHB` |
| `APPLE_API_ISSUER` | App Store Connect Issuer ID | UUID 格式 |
| `APPLE_TEAM_ID` | Apple Developer Team ID | 例如 `6Y34Q27J49` |

## 可选 Secrets

| Secret | 值 | 什么时候需要 |
| --- | --- | --- |
| `APPLE_SIGNING_IDENTITY` | `Developer ID Application: Name (TEAMID)` | workflow 自动识别失败时再填 |
| `KEYCHAIN_PASSWORD` | 任意强密码 | 需要固定 CI keychain 密码时；通常不用 |

## Base64 生成命令

`.p12`：

```bash
base64 -i "$SIGNING_DIR/$NAME.p12" | tr -d '\n' | pbcopy
```

`.p8`：

```bash
base64 -i "$SIGNING_DIR/AuthKey_KEYID.p8" | tr -d '\n' | pbcopy
```

## 本机验证

验证证书类型：

```bash
openssl x509 -in "$SIGNING_DIR/$NAME.cer" -inform DER -noout -subject -issuer -dates
```

`subject` 必须包含 `Developer ID Application`。

验证 App Store Connect API key：

```bash
xcrun notarytool history \
  --key "$SIGNING_DIR/AuthKey_KEYID.p8" \
  --key-id "KEYID" \
  --issuer "ISSUER_ID"
```
