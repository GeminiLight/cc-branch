# Contributing to CC Branch

Thanks for contributing to CC Branch.

The canonical contributor guide lives in [`docs/contributing.md`](docs/contributing.md). Keep that file as the source of truth for architecture boundaries, test commands, and documentation expectations.

## Quick Setup

Requirements:

- Python 3.10+
- Node.js/npm for Web UI work
- `tmux` when testing `layoutBackend: tmux`
- Git

Install locally:

```bash
pip install -e .
```

Editable installs do not build Web UI assets. Build them when you need to test `cc-branch serve`:

```bash
python scripts/build-webui.py
```

## Quality Checks

Run the relevant checks before opening a pull request:

```bash
python -m unittest discover tests
python -m ruff check .
python -m mypy cc_branch
npm --prefix apps/web run lint
npm --prefix apps/web test -- --run
npm --prefix apps/web run build
```

For package validation:

```bash
python -m build --sdist --wheel
python -m twine check dist/*
```

## Pull Requests

- Keep each PR focused.
- Add or update tests for behavior changes.
- Update user-facing docs when behavior changes.
- Use clear commit messages that describe the real change.
- Include rollout or release notes when touching packaging, desktop, or publishing behavior.

## Documentation

When behavior changes, keep these files aligned as needed:

- [`README.md`](README.md)
- [`README.zh.md`](README.zh.md)
- [`docs/README.md`](docs/README.md)
- [`docs/getting-started.md`](docs/getting-started.md)
- [`docs/quickstart.md`](docs/quickstart.md)
- [`docs/user-guide.md`](docs/user-guide.md)
- [`docs/features.md`](docs/features.md)
- [`docs/architecture.md`](docs/architecture.md)
- [`docs/webui-spec.md`](docs/webui-spec.md)

## Security

Report security issues through the process in [`SECURITY.md`](SECURITY.md).

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
