# Examples

## Pipe Terraform Plan Output

```bash
terraform plan -no-color | tfexplain
```

This gives a concise action and risk summary from human-readable Terraform output.

## Analyze A Saved tfplan

```bash
terraform plan -out=tfplan
tfexplain plan tfplan --show-fields
```

Saved plans provide richer field-level details through local `terraform show -json`.

## Group Changes By Risk

```bash
tfexplain plan samples/plans/12-mixed-multicloud-module.json --group-by risk
```

## Fail CI On Risky Changes

```bash
tfexplain plan tfplan --fail-on delete,replace,critical
```

Exit code `2` means the configured risk gate matched.

## Generate A GitHub PR Comment

```bash
tfexplain review --code . --plan tfplan --format github > tfexplain-review.md
```

## Generate A Graph

```bash
tfexplain graph . --format ascii
tfexplain graph . --format mermaid
```

## Try The Included Samples

```bash
tfexplain code samples/terraform-code/aws-webapp
tfexplain code samples/terraform-code/azurerm-aks
tfexplain plan samples/plans/02-aws-rds-replace.json --show-fields
tfexplain review --code samples/terraform-code/aws-webapp --plan samples/plans/02-aws-rds-replace.json --format github
```

