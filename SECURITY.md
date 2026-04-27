# Security Policy

## Supported Versions

We release patches for security vulnerabilities for the following versions:

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |

## Reporting a Vulnerability

If you discover a security vulnerability, please do the following:

1. **Do NOT** open a public issue
2. Email the maintainer at [your-email@example.com] with:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if any)

We will respond within 48 hours and work with you to understand and address the issue.

## Security Best Practices

When using CC Branch:

- **Never commit** `.cc-branch.state.toml` to version control (it's in .gitignore by default)
- **Review generated configs** before running `cc-branch up`
- **Be cautious** with custom commands in window configurations
- **Keep dependencies updated** regularly
- **Use tmux security features** if running in shared environments

## Disclosure Policy

- We will confirm receipt of your vulnerability report within 48 hours
- We will provide a detailed response within 7 days
- We will work on a fix and release it as soon as possible
- We will credit you in the release notes (unless you prefer to remain anonymous)
