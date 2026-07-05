# Getting Started

## Install From PyPI

```bash
pip install bna-tfexplain
```

Verify the install:

```bash
tfexplain version
tfexplain --help
```

## Explain A Terraform Plan

Pipe raw Terraform plan text:

```bash
terraform plan -no-color | tfexplain
```

For richer field-level details, use a saved plan:

```bash
terraform plan -out=tfplan
tfexplain plan tfplan --show-fields
```

Or stream Terraform JSON:

```bash
terraform show -json tfplan | tfexplain plan -
```

## Explain Terraform Code

```bash
tfexplain code .
```

This reports providers, resources, modules, variables, outputs, backend settings, module quality, and review findings.

## Local Development

```bash
git clone https://github.com/Vijaydaswani/tfexplain.git
cd tfexplain
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e .
python3 -m unittest discover -s tests
```

