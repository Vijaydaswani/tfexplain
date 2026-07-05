# CI And PR Review

`tfexplain` is designed to make Terraform plan review easier in pull requests.

## PR Comment Format

```bash
tfexplain review --code . --plan tfplan --format github > tfexplain-review.md
```

This produces markdown designed for GitHub PR comments.

## Risk Gate

```bash
tfexplain plan tfplan --fail-on delete,replace,critical
```

Exit codes:

- `0`: analysis completed and no configured risk gate matched.
- `1`: command or analysis error.
- `2`: analysis completed and `--fail-on` matched.

## GitHub Actions Example

```yaml
name: tfexplain

on:
  pull_request:

jobs:
  review:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      pull-requests: write
    steps:
      - uses: actions/checkout@v4
      - uses: hashicorp/setup-terraform@v3

      - name: Install tfexplain
        run: python -m pip install bna-tfexplain

      - name: Terraform plan
        run: |
          terraform init
          terraform plan -out=tfplan

      - name: Generate tfexplain PR comment
        run: |
          tfexplain review --code . --plan tfplan --format github > tfexplain-review.md

      - name: Comment on PR
        uses: actions/github-script@v7
        with:
          script: |
            const fs = require('fs');
            const body = fs.readFileSync('tfexplain-review.md', 'utf8');
            await github.rest.issues.createComment({
              owner: context.repo.owner,
              repo: context.repo.repo,
              issue_number: context.issue.number,
              body,
            });
```

