# AI Mode

AI mode adds a generated explanation after the deterministic local analysis.

AI is disabled by default.

## OpenAI

```bash
export OPENAI_API_KEY=...
tfexplain plan tfplan --ai --provider openai
tfexplain code . --ai --provider openai --model gpt-4o-mini
```

## Claude

```bash
export ANTHROPIC_API_KEY=...
tfexplain review --code . --plan tfplan --ai --provider claude
```

## Azure OpenAI

```bash
export AZURE_OPENAI_API_KEY=...
export AZURE_OPENAI_ENDPOINT=https://example.openai.azure.com
tfexplain plan tfplan --ai --provider azure-openai --model <deployment-name>
```

## Ollama

```bash
ollama serve
tfexplain code . --ai --provider ollama --model llama3.1
```

## Supported Providers

- `openai`
- `claude`
- `azure-openai`
- `ollama`

## Privacy Notes

- AI calls only happen when `--ai` is passed.
- Local analysis still runs first.
- Secret-like values are redacted before AI requests.

