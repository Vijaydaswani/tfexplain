#!/usr/bin/env sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
ROOT_DIR=$(CDPATH= cd -- "$SCRIPT_DIR/../.." && pwd)
SOURCE_DIR="$SCRIPT_DIR/source/terraform-data"
OUTPUT_DIR="$SCRIPT_DIR/generated/terraform-data"

mkdir -p "$OUTPUT_DIR"

printf '%s\n' "Initializing sample Terraform project..."
terraform -chdir="$SOURCE_DIR" init -backend=false

printf '%s\n' "Creating clean create plan..."
terraform -chdir="$SOURCE_DIR" plan -out="$OUTPUT_DIR/create.tfplan" -var-file="$SCRIPT_DIR/vars/create.tfvars"
terraform -chdir="$SOURCE_DIR" show -json "$OUTPUT_DIR/create.tfplan" > "$OUTPUT_DIR/create.json"
PYTHONPATH="$ROOT_DIR/src" python3 -m tfexplain plan "$OUTPUT_DIR/create.tfplan" > "$OUTPUT_DIR/create.txt"

printf '%s\n' "Applying base local state for update/replace sample..."
terraform -chdir="$SOURCE_DIR" apply -auto-approve -var-file="$SCRIPT_DIR/vars/base.tfvars"

printf '%s\n' "Creating update/replace plan..."
terraform -chdir="$SOURCE_DIR" plan -out="$OUTPUT_DIR/update-replace.tfplan" -var-file="$SCRIPT_DIR/vars/changed.tfvars"
terraform -chdir="$SOURCE_DIR" show -json "$OUTPUT_DIR/update-replace.tfplan" > "$OUTPUT_DIR/update-replace.json"
PYTHONPATH="$ROOT_DIR/src" python3 -m tfexplain plan "$OUTPUT_DIR/update-replace.tfplan" --show-fields > "$OUTPUT_DIR/update-replace.txt"

printf '%s\n' ""
printf '%s\n' "Saved tfplan samples generated in:"
printf '%s\n' "$OUTPUT_DIR"
printf '%s\n' ""
printf '%s\n' "Try:"
printf '%s\n' "PYTHONPATH=src python3 -m tfexplain plan samples/tfplans/generated/terraform-data/create.tfplan"
printf '%s\n' "PYTHONPATH=src python3 -m tfexplain plan samples/tfplans/generated/terraform-data/update-replace.tfplan --show-fields"
