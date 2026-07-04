# Contributing

Thanks for contributing to `bna-tools/tfexplain`.

For discussion, questions, and early roadmap feedback, join the Build & Automate Slack:
[Join Slack](https://join.slack.com/share/enQtMTE1MTg1ODM3NDgyNTctYjczZWU2MDkxZWJhNWUyZTNjYTAxYzE1ZWJlMWQ0NDhmNTQ1YmM4YTM0MTc1YzA3NDJiM2FjZjA1ZjMxOGEzZg?entry_point=redirect_flow)

## Development Setup

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e .
```

Run tests:

```bash
python3 -m unittest discover -s tests
python3 -m compileall -q src tests
```

## Contribution Guidelines

- Keep deterministic analysis working without AI.
- Do not add behavior that runs `terraform apply`.
- Do not send plan or code content to AI unless `--ai` is explicitly passed.
- Add focused tests for parser, renderer, and CLI changes.
- Prefer dependency-free standard-library code unless a dependency clearly earns its cost.

## Good First Areas

- Provider-aware risk rules.
- More sample plans.
- CI output formats.
- Documentation polish.
