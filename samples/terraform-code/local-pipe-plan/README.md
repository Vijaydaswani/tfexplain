# Local Pipe Plan Sample

This sample is meant for testing:

```bash
terraform plan -no-color | tfexplain
```

It uses Terraform's built-in `terraform_data` resource only. No cloud credentials, Kubernetes cluster, or external provider download should be required.

From this directory:

```bash
terraform init -backend=false
terraform plan -no-color | PYTHONPATH=../../../src python3 -m tfexplain
```

For richer field-level analysis, use Terraform JSON:

```bash
terraform plan -out=tfplan
terraform show -json tfplan | PYTHONPATH=../../../src python3 -m tfexplain plan -
```
