# Security Policy

## Reporting a Vulnerability

Please report suspected security issues privately by emailing Vijay Daswani at [vijay.daswani@gmail.com](mailto:vijay.daswani@gmail.com).

For non-sensitive security questions, roadmap discussion, and community support, join the Build & Automate Slack:
[Join Slack](https://join.slack.com/share/enQtMTE1MTg1ODM3NDgyNTctYjczZWU2MDkxZWJhNWUyZTNjYTAxYzE1ZWJlMWQ0NDhmNTQ1YmM4YTM0MTc1YzA3NDJiM2FjZjA1ZjMxOGEzZg?entry_point=redirect_flow)

Do not open a public issue for secrets exposure, credential handling bugs, or vulnerabilities that could affect users' infrastructure workflows.

## Safety Model

- `tfexplain` never runs `terraform apply`.
- `tfexplain` does not modify cloud resources.
- Plan and code analysis runs locally by default.
- AI calls are opt-in with `--ai`.
- Content is redacted before AI requests.

## Sensitive Data

Terraform plan files can contain secrets. Avoid committing generated `.tfplan`, `terraform.tfstate`, or unredacted plan JSON files.
