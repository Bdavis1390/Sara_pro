# WORLD CONTROLLER — GPT Account / Project Import Guide

This importer is local-first. It does **not** log into OpenAI and does **not** scrape a remote ChatGPT account. It ingests files already present on the Lenovo machine.

## What it imports

1. Current GPT-session files packaged with this patch.
2. ChatGPT/OpenAI data-export ZIPs found in:
   - `~/Downloads`
   - `~/Documents`
   - `~/ChatGPT_Exports`
   - `~/GPT_Exports`
3. Loose local project documents found in:
   - `~/Worldshepherd`
   - `~/worldshepherd`
   - roots listed in `WORLD_PROJECT_ROOTS`

## Strong rule

For "all projects in this account," use ChatGPT's export/download function and place the resulting ZIPs or downloaded project files in one of the scan folders. WORLD CONTROLLER can ingest local evidence; it cannot silently reach into a remote ChatGPT account.

## Re-run import

```bash
cd ~/Sara_pro
./scripts/world_ingest_all_gpt_and_projects.sh
```

Then boot the UI:

```bash
cd ~/Sara_pro && ./scripts/world_boot.sh
```

Open:

```text
http://127.0.0.1:9530/world/ui
```

## Evidence locations

```text
~/Sara_pro/world_documents/gpt_session/current
~/Sara_pro/world_documents/gpt_exports
~/Sara_pro/world_documents/account_projects_loose
~/Sara_pro/world_documents/GPT_ACCOUNT_IMPORT_MANIFEST.json
```
