# tfexplain Wiki

`tfexplain` is an open-source Build & Automate CLI for explaining Terraform code, Terraform plans, saved `tfplan` files, and piped plan output.

Terraform plans are powerful but noisy. `tfexplain` turns them into readable summaries for engineers, reviewers, and CI/CD pipelines.

## Quick Links

- [Getting Started](Getting-Started)
- [Commands](Commands)
- [Examples](Examples)
- [CI and PR Review](CI-and-PR-Review)
- [Safety and Privacy](Safety-and-Privacy)
- [AI Mode](AI-Mode)
- [Roadmap](Roadmap)

## Install

```bash
pip install bna-tfexplain
tfexplain --help
```

The PyPI package name is `bna-tfexplain`; the CLI command is `tfexplain`.

## Common Workflows

```bash
terraform plan -no-color | tfexplain
tfexplain plan tfplan --show-fields
tfexplain code .
tfexplain review --code . --plan tfplan --format github
tfexplain graph . --format ascii
```

## Project

- Author: Vijay Daswani
- Company: Build & Automate
- Website: [buildnautomate.com](https://buildnautomate.com)
- Repository: [Vijaydaswani/tfexplain](https://github.com/Vijaydaswani/tfexplain)
- Package shortform: `bna-tools/tfexplain`

