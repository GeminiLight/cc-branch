# Homebrew Tap Support

This directory contains the Homebrew formula template for publishing `cc-branch`
through a custom tap such as `GeminiLight/homebrew-cc-branch`.

## User-Facing Install Command

After the tap repository is published, users install with:

```bash
brew install GeminiLight/cc-branch/cc-branch
```

This one-line form taps the repository automatically. The explicit equivalent is
`brew tap GeminiLight/cc-branch` followed by `brew install cc-branch`.

## Release Maintainer Flow

1. Publish the Python package to PyPI.
2. Copy `Formula/cc-branch.rb.template` to the tap repository as `Formula/cc-branch.rb`.
3. Replace all `__...__` placeholders with the released version and source hashes.
4. Run:

```bash
brew install --build-from-source ./Formula/cc-branch.rb
brew test cc-branch
brew audit --strict --online cc-branch
```

## Getting Source Hashes

Download the exact release artifacts and dependency sdists, then compute hashes:

```bash
python -m pip download --no-binary=:all: --dest /tmp/cc-branch-homebrew cc-branch==0.1.0
shasum -a 256 /tmp/cc-branch-homebrew/*
```

Use the hashes in the formula template. The formula uses Homebrew's
`Language::Python::Virtualenv` helper so dependencies are isolated inside the
Homebrew prefix instead of relying on the user's Python environment.
