# Changelog

All notable changes to `tfexplain` are documented here.

The project follows semantic versioning while the public API is still early.

## [Unreleased]

### Added

- Saved plan conversion now falls back from `terraform show -json` to `tofu show -json` and `terragrunt show -json`.
- Human-readable Terraform, OpenTofu, and Terragrunt plan text can now be read from files, not only stdin.

### Changed

- Added clearer guidance when a `.json` file is not real Terraform plan JSON, including the common `plan -out=json` mistake.

## [0.1.3] - 2026-07-06

### Fixed

- Switched the macOS release binary build from `macos-13` to `macos-latest` to avoid unavailable runner queues.
- Renamed the macOS release bundle to `tfexplain-macos.zip` so it does not imply a specific CPU architecture.

## [0.1.2] - 2026-07-06

### Added

- GitHub release workflow now builds standalone CLI binary bundles for Linux, macOS, and Windows.
- Release workflow now attaches SHA-256 checksums for binary bundle artifacts.
- PyInstaller binary entrypoint for reproducible standalone builds.

## [0.1.1] - 2026-07-06

### Fixed

- Fixed parsing for `terragrunt plan -no-color | tfexplain` when Terragrunt prefixes Terraform output lines.
- Added support for OpenTofu human-readable plan markers.

### Changed

- Documented Terragrunt pipe and JSON workflows.

## [0.1.0] - 2026-07-05

### Added

- Initial open-source release.
- Terraform code analysis.
- Terraform JSON plan and saved `tfplan` analysis.
- Pipe support for `terraform plan -no-color | tfexplain`.
- Risk scoring and `--fail-on` support for CI/CD guardrails.
- GitHub PR comment output format.
- Module docs generation.
- Resource graph output in text, ASCII, Mermaid, DOT, and JSON formats.
- Optional AI-assisted explanations for OpenAI, Claude, Azure OpenAI, and Ollama.
- Sample Terraform code and plan fixtures.
- PyPI package `bna-tfexplain`.
