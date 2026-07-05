# Commands

## Version

```bash
tfexplain version
tfexplain --version
```

## Plan

```bash
tfexplain plan <plan.json|tfplan|->
```

Useful options:

```bash
tfexplain plan tfplan --show-fields
tfexplain plan tfplan --group-by risk
tfexplain plan tfplan --format markdown
tfexplain plan tfplan --fail-on delete,replace,critical
```

## Risk

```bash
tfexplain risk <plan.json|tfplan|->
```

## Code

```bash
tfexplain code <directory>
tfexplain code . --format json
```

## Explain

```bash
tfexplain explain --code <directory> --plan <plan.json|tfplan|->
```

## Review

```bash
tfexplain review --code . --plan tfplan --format github
```

## Docs

```bash
tfexplain docs . --output TERRAFORM.md
```

## Graph

```bash
tfexplain graph . --format ascii
tfexplain graph . --format mermaid
tfexplain graph . --format dot
```

## Init

```bash
tfexplain init
tfexplain init --force
```

