# cc-branch npm package

This package installs the `cc-branch` and `ccb` commands through a bundled Python wheel.

Requirements:

- Node.js 18+
- Python 3.10+

Install from a local package artifact:

```bash
npm install -g ./cc-branch-1.1.1.tgz
cc-branch --version
```

If Python is installed in a custom location, set `CC_BRANCH_PYTHON` before installing.
