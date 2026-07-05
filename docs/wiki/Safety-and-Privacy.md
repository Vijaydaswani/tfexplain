# Safety And Privacy

`tfexplain` is intentionally local-first.

## Defaults

- No AI calls unless `--ai` is passed.
- No `terraform apply`.
- No cloud changes.
- Plan and code analysis runs locally.
- Secrets are redacted before AI requests.

## Terraform Commands

When a saved binary `tfplan` is provided, `tfexplain` uses local Terraform to convert it:

```bash
terraform show -json tfplan
```

It does not run:

```bash
terraform apply
```

## AI Mode

AI mode is opt-in:

```bash
tfexplain plan tfplan --ai --provider openai
```

Before sending content to an AI provider, `tfexplain` redacts common secret-like values.

## Security Reports

Please report suspected security issues privately through Build & Automate:

- Website: [buildnautomate.com](https://buildnautomate.com)
- Community: [Build & Automate Slack](https://join.slack.com/share/enQtMTE1MTg1ODM3NDgyNTctYjczZWU2MDkxZWJhNWUyZTNjYTAxYzE1ZWJlMWQ0NDhmNTQ1YmM4YTM0MTc1YzA3NDJiM2FjZjA1ZjMxOGEzZg?entry_point=redirect_flow)

