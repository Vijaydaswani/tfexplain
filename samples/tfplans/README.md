# Saved tfplan Samples

Terraform saved plan files are binary, version-sensitive, and can contain sensitive values. This repository does not commit generated `.tfplan` files.

Use `generate.sh` to create local saved-plan samples under `samples/tfplans/generated/`:

```bash
./samples/tfplans/generate.sh
```

The generator creates:

- `generated/terraform-data/create.tfplan`
- `generated/terraform-data/create.json`
- `generated/terraform-data/create.txt`
- `generated/terraform-data/update-replace.tfplan`
- `generated/terraform-data/update-replace.json`
- `generated/terraform-data/update-replace.txt`

Then run `tfexplain` directly against the binary plan:

```bash
PYTHONPATH=src python3 -m tfexplain plan samples/tfplans/generated/terraform-data/create.tfplan
PYTHONPATH=src python3 -m tfexplain plan samples/tfplans/generated/terraform-data/update-replace.tfplan --show-fields
```

The sample Terraform project uses only the built-in `terraform_data` resource. It still requires the `terraform` CLI because `tfexplain` converts binary plans with `terraform show -json`.
