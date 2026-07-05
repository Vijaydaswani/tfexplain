#!/usr/bin/env bash
set -uo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

DEMO_PAUSE_SECONDS="${DEMO_PAUSE_SECONDS:-2}"
DEMO_WAIT_FOR_ENTER="${DEMO_WAIT_FOR_ENTER:-0}"
DEMO_CLEAR_ON_ENTER="${DEMO_CLEAR_ON_ENTER:-1}"
DEMO_TMP_DIR="${DEMO_TMP_DIR:-/tmp/tfexplain-demo}"
DEMO_TFPLAN="$DEMO_TMP_DIR/local-pipe-plan.tfplan"
DEMO_INIT_DIR="$DEMO_TMP_DIR/init"

mkdir -p "$DEMO_TMP_DIR" "$DEMO_INIT_DIR"

usage() {
  cat <<'USAGE'
Usage: ./demo.sh [options]

Options:
  --enter        Wait for Enter between demo steps and clear the screen.
  --no-clear     Do not clear the screen when using --enter.
  --pause SEC    Sleep SEC seconds between demo steps. Default: 2.
  --skip-ai      Skip the OpenAI demo step.
  -h, --help     Show this help.

Environment:
  DEMO_WAIT_FOR_ENTER=1     Same as --enter.
  DEMO_CLEAR_ON_ENTER=0     Same as --no-clear.
  DEMO_PAUSE_SECONDS=1      Set timed pause seconds.
  SKIP_AI=1                 Skip the OpenAI demo step.
USAGE
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --enter)
      DEMO_WAIT_FOR_ENTER=1
      ;;
    --no-clear)
      DEMO_CLEAR_ON_ENTER=0
      ;;
    --pause)
      shift
      if [ "$#" -eq 0 ]; then
        printf 'Missing value for --pause.\n' >&2
        exit 1
      fi
      DEMO_PAUSE_SECONDS="$1"
      ;;
    --skip-ai)
      SKIP_AI=1
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      printf 'Unknown option: %s\n\n' "$1" >&2
      usage >&2
      exit 1
      ;;
  esac
  shift
done

if ! command -v tfexplain >/dev/null 2>&1; then
  tfexplain() {
    PYTHONPATH="$ROOT_DIR/src${PYTHONPATH:+:$PYTHONPATH}" python3 -m tfexplain "$@"
  }
fi

bold="$(printf '\033[1m')"
dim="$(printf '\033[2m')"
green="$(printf '\033[32m')"
blue="$(printf '\033[34m')"
yellow="$(printf '\033[33m')"
reset="$(printf '\033[0m')"

pause_demo() {
  if [ "$DEMO_WAIT_FOR_ENTER" = "1" ]; then
    printf '\n'
    read -r -p "Press Enter to continue..."
    if [ "$DEMO_CLEAR_ON_ENTER" = "1" ]; then
      clear
    fi
  elif [ "$DEMO_PAUSE_SECONDS" != "0" ]; then
    sleep "$DEMO_PAUSE_SECONDS"
  fi
}

title() {
  printf '\n%s%s%s\n' "$bold" "$1" "$reset"
  printf '%s\n' "============================================================"
}

run() {
  local note="$1"
  local command="$2"

  printf '\n%s%s%s\n' "$blue" "$note" "$reset"
  printf '%s$ %s%s\n\n' "$dim" "$command" "$reset"

  eval "$command"
  local status=$?
  if [ "$status" -ne 0 ]; then
    printf '\n%sCommand failed with exit code %s.%s\n' "$yellow" "$status" "$reset" >&2
    exit "$status"
  fi

  pause_demo
}

run_optional() {
  local note="$1"
  local command="$2"

  printf '\n%s%s%s\n' "$blue" "$note" "$reset"
  printf '%s$ %s%s\n\n' "$dim" "$command" "$reset"

  eval "$command"
  local status=$?
  if [ "$status" -ne 0 ]; then
    printf '\n%sOptional demo step failed with exit code %s; continuing.%s\n' "$yellow" "$status" "$reset" >&2
  fi

  pause_demo
}

run_expect_exit() {
  local note="$1"
  local command="$2"
  local expected="$3"

  printf '\n%s%s%s\n' "$blue" "$note" "$reset"
  printf '%s$ %s%s\n\n' "$dim" "$command" "$reset"

  eval "$command"
  local status=$?

  if [ "$status" -ne "$expected" ]; then
    printf '\n%sExpected exit code %s but got %s.%s\n' "$yellow" "$expected" "$status" "$reset" >&2
    exit "$status"
  fi

  printf '\n%sExpected CI signal: command exited with code %s.%s\n' "$green" "$status" "$reset"
  pause_demo
}

title "tfexplain demo"
if [ "$DEMO_WAIT_FOR_ENTER" = "1" ] && [ "$DEMO_CLEAR_ON_ENTER" = "1" ]; then
  clear
fi
printf '%sTerraform plans are powerful but noisy. tfexplain turns them into reviewer-ready summaries, risk signals, graphs, docs, CI output, and optional AI explanations.%s\n' "$green" "$reset"
pause_demo

run "Start with package and Build & Automate metadata." \
  "tfexplain version"

run "Show the CLI help and available commands." \
  "tfexplain --help"

title "1. From noisy plan data to clear risk"

run "First, show how noisy Terraform JSON plan data looks to a reviewer." \
  "python3 -m json.tool samples/plans/02-aws-rds-replace.json | sed -n '1,90p'"

run "Now collapse that noise into actions, risk, replacement causes, and changed field paths." \
  "tfexplain plan samples/plans/02-aws-rds-replace.json --show-fields"

run "Show the same value on a mixed multi-cloud plan grouped by risk." \
  "tfexplain plan samples/plans/12-mixed-multicloud-module.json --group-by risk"

run "Highlight destructive changes quickly for reviewers." \
  "tfexplain risk samples/plans/04-azurerm-keyvault-delete.json"

run_expect_exit "Use tfexplain as a CI/CD guardrail: fail when delete, replace, or critical risk appears." \
  "tfexplain plan samples/plans/02-aws-rds-replace.json --fail-on delete,replace,critical" \
  "2"

title "2. Explain Terraform code before review"

run "Scan Terraform code for providers, resources, module quality, missing validation, and review findings." \
  "tfexplain code samples/terraform-code/aws-webapp"

run "Show another provider: Azure AKS code analysis in markdown." \
  "tfexplain code samples/terraform-code/azurerm-aks --format markdown"

run "Produce JSON output for automation and downstream tools." \
  "tfexplain code samples/terraform-code/random-tls-module --format json"

title "3. Reviewer and PR value"

run "Combine code context and plan context into one explanation." \
  "tfexplain explain --code samples/terraform-code/azurerm-aks --plan samples/plans/03-azurerm-aks-update.json --format markdown"

run "Generate GitHub PR comment markdown that can be posted by CI." \
  "tfexplain review --code samples/terraform-code/aws-webapp --plan samples/plans/02-aws-rds-replace.json --format github"

title "4. Docs and graph from Terraform code"

run "Generate module documentation without hand-writing a README section." \
  "tfexplain docs samples/terraform-code/aws-webapp --format text"

run "Visualize provider-to-resource relationships directly in the terminal." \
  "tfexplain graph samples/terraform-code/azurerm-aks --format ascii"

run "Export the graph as Mermaid for docs, pull requests, and diagrams." \
  "tfexplain graph samples/terraform-code/azurerm-aks --format mermaid"

title "5. Local config"

run "Create a local tfexplain config file in a temporary demo directory." \
  "tfexplain init \"$DEMO_INIT_DIR\" --force"

run "Show the generated config file." \
  "sed -n '1,120p' \"$DEMO_INIT_DIR/.tfexplain.json\""

title "6. Real Terraform pipe workflow"

if command -v terraform >/dev/null 2>&1; then
  run "Initialize the local-only Terraform sample with no cloud provider." \
    "terraform -chdir=samples/terraform-code/local-pipe-plan init -backend=false"

  run "This is the headline workflow: pipe raw terraform plan text straight into tfexplain." \
    "terraform -chdir=samples/terraform-code/local-pipe-plan plan -no-color | tfexplain"

  run "Save a binary tfplan file for richer field-level analysis." \
    "terraform -chdir=samples/terraform-code/local-pipe-plan plan -out=\"$DEMO_TFPLAN\""

  run "Explain the saved tfplan file directly." \
    "tfexplain plan \"$DEMO_TFPLAN\" --show-fields"

  run "Stream Terraform JSON into tfexplain through stdin." \
    "terraform -chdir=samples/terraform-code/local-pipe-plan show -json \"$DEMO_TFPLAN\" | tfexplain plan -"
else
  printf '\n%sTerraform is not installed, so the live pipe workflow is skipped.%s\n' "$yellow" "$reset"
  printf '%sInstall Terraform and rerun demo.sh to show: terraform plan -no-color | tfexplain%s\n' "$dim" "$reset"
  pause_demo
fi

title "7. AI-assisted explanation"

if [ "${SKIP_AI:-0}" = "1" ]; then
  printf '\n%sSKIP_AI=1 is set, so the AI step is skipped.%s\n' "$yellow" "$reset"
elif [ -n "${OPENAI_API_KEY:-}" ]; then
  run_optional "Ask OpenAI for a plain-English explanation on top of the local deterministic analysis." \
    "tfexplain plan samples/plans/12-mixed-multicloud-module.json --ai --provider openai --format markdown"
else
  printf '\n%sOPENAI_API_KEY is not set, so the AI step is skipped.%s\n' "$yellow" "$reset"
  printf '%sSet OPENAI_API_KEY and rerun demo.sh to include the AI section.%s\n' "$dim" "$reset"
fi

title "Demo complete"
printf '%sInstall command for viewers:%s pip install bna-tfexplain\n' "$green" "$reset"
printf '%sRun command:%s tfexplain --help\n' "$green" "$reset"
