# Contributing to CC Branch

Thank you for your interest in contributing to CC Branch! This document provides guidelines and instructions for contributing.

## Code of Conduct

By participating in this project, you agree to maintain a respectful and inclusive environment for everyone.

## How to Contribute

### Reporting Bugs

Before creating bug reports, please check existing issues to avoid duplicates. When creating a bug report, include:

- **Clear title and description**
- **Steps to reproduce** the behavior
- **Expected behavior**
- **Actual behavior**
- **Environment details** (OS, Python version, tmux version)
- **Relevant logs or error messages**

### Suggesting Enhancements

Enhancement suggestions are tracked as GitHub issues. When creating an enhancement suggestion, include:

- **Clear title and description**
- **Use case** - why is this enhancement useful?
- **Proposed solution** (if you have one)
- **Alternatives considered**

### Pull Requests

1. **Fork the repository** and create your branch from `main`
2. **Make your changes**:
   - Follow the existing code style
   - Add tests for new functionality
   - Update documentation as needed
3. **Test your changes**:
   ```bash
   python -m pytest tests/ -v
   ```
4. **Commit your changes**:
   - Use clear, descriptive commit messages
   - Follow [Conventional Commits](https://www.conventionalcommits.org/) format:
     - `feat:` for new features
     - `fix:` for bug fixes
     - `docs:` for documentation changes
     - `test:` for test additions/changes
     - `refactor:` for code refactoring
     - `chore:` for maintenance tasks
5. **Push to your fork** and submit a pull request

### Pull Request Guidelines

- **One feature per PR** - keep changes focused
- **Update tests** - ensure all tests pass
- **Update documentation** - if you change behavior
- **Add changelog entry** - in CHANGELOG.md under [Unreleased]
- **Describe your changes** - explain what and why in the PR description

## Development Setup

### Prerequisites

- Python 3.11+
- tmux
- Git

### Setup

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/cc-branch.git
cd cc-branch

# Install in development mode
pip install -e .

# Install development dependencies
pip install pytest pytest-cov

# Run tests
python -m pytest tests/ -v

# Run specific test file
python -m pytest tests/test_bootstrap.py -v
```

### Project Structure

```
cc-branch/
├── cc_branch/          # Main package
│   ├── cli.py            # CLI entry point
│   ├── config.py         # Configuration loading
│   ├── planner.py        # Workspace planning
│   ├── runtime.py        # Tmux execution
│   ├── state.py          # State persistence
│   ├── bootstrap.py      # First-run experience
│   ├── profiles.py       # Profile templates
│   └── doctor.py         # Health checks
├── tests/                # Test suite
├── docs/                 # Documentation
├── examples/             # Example configs
└── wiki/                 # Specs and design docs
```

### Code Style

- Follow PEP 8
- Use type hints where appropriate
- Keep functions focused and under 50 lines when possible
- Add docstrings for public functions
- Use meaningful variable names

### Testing

- Write tests for new features
- Maintain or improve test coverage
- Test edge cases and error conditions
- Use descriptive test names

Example test structure:
```python
def test_feature_does_something_specific():
    """Test that feature behaves correctly in specific scenario."""
    # Arrange
    input_data = ...

    # Act
    result = function_under_test(input_data)

    # Assert
    assert result == expected_value
```

## Documentation

- Update README.md for user-facing changes
- Update docs/ for detailed documentation
- Add examples for new features
- Keep documentation clear and concise

## Release Process

(For maintainers)

1. Update version in `pyproject.toml`
2. Update CHANGELOG.md
3. Create git tag: `git tag -a v0.2.0 -m "Release v0.2.0"`
4. Push tag: `git push origin v0.2.0`
5. GitHub Actions will handle the release

## Questions?

Feel free to open an issue for questions or discussions about contributing.

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
