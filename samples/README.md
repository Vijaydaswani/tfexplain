# tfexplain Samples

This directory contains deterministic fixtures for exercising `tfexplain`.

## Terraform Code

`samples/terraform-code/` includes small Terraform projects for multiple providers:

- `aws-webapp`
- `azurerm-aks`
- `google-cloudrun`
- `kubernetes-helm`
- `cloudflare-dns`
- `random-tls-module`
- `local-pipe-plan`

These examples are intentionally compact. They are meant for parser and output testing, not direct deployment.

`local-pipe-plan` uses only Terraform's built-in `terraform_data` resource and is the easiest sample for testing:

```bash
cd samples/terraform-code/local-pipe-plan
terraform init -backend=false
terraform plan -no-color | PYTHONPATH=../../../src python3 -m tfexplain
```

## Terraform Plans

`samples/plans/` includes Terraform `show -json` style plan fixtures with different providers and action mixes:

- create-heavy plans
- in-place updates
- replacements caused by immutable fields
- deletes for CI `--fail-on` checks
- module-addressed resources
- mixed-provider changes

## Saved tfplan Generator

`samples/tfplans/` contains a local generator for real binary `.tfplan` samples:

```bash
./samples/tfplans/generate.sh
PYTHONPATH=src python3 -m tfexplain plan samples/tfplans/generated/terraform-data/create.tfplan
PYTHONPATH=src python3 -m tfexplain plan samples/tfplans/generated/terraform-data/update-replace.tfplan --show-fields
```

Generated `.tfplan` files are intentionally ignored by Git because Terraform plan binaries are version-sensitive and can contain sensitive data.

Run all sample checks with:

```bash
python3 -m unittest discover -s tests
```

Try individual samples:

```bash
PYTHONPATH=src python3 -m tfexplain code samples/terraform-code/aws-webapp
PYTHONPATH=src python3 -m tfexplain plan samples/plans/02-aws-rds-replace.json --show-fields
PYTHONPATH=src python3 -m tfexplain explain --code samples/terraform-code/azurerm-aks --plan samples/plans/03-azurerm-aks-update.json --format markdown
PYTHONPATH=src python3 -m tfexplain review --code samples/terraform-code/local-pipe-plan --plan samples/plans/12-mixed-multicloud-module.json
PYTHONPATH=src python3 -m tfexplain docs samples/terraform-code/local-pipe-plan
PYTHONPATH=src python3 -m tfexplain graph samples/terraform-code/local-pipe-plan --format ascii
PYTHONPATH=src python3 -m tfexplain graph samples/terraform-code/local-pipe-plan --format mermaid
```

AI-assisted sample with a local Ollama model:

```bash
PYTHONPATH=src python3 -m tfexplain code samples/terraform-code/local-pipe-plan --ai --provider ollama --model llama3.1
```

For real saved Terraform plans, pass the binary plan file directly:

```bash
terraform plan -out=tfplan
PYTHONPATH=src python3 -m tfexplain plan tfplan
```

Binary `tfplan` support requires the `terraform` executable because `tfexplain` converts the file locally with `terraform show -json`.

You can also stream Terraform JSON through stdin:

```bash
terraform show -json tfplan | PYTHONPATH=src python3 -m tfexplain plan -
```

You can pipe raw Terraform plan text for a lightweight resource/action summary:

```bash
terraform plan -no-color | PYTHONPATH=src python3 -m tfexplain
```
