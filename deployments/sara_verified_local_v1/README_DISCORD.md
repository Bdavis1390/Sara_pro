# Discord notification quick reference

Worldshepherd's first Discord integration is outbound-only and notification-only.

Dry run:

```bash
ws-discord-notify \
  --event-class WORKFLOW_STATUS \
  --title 'Example status' \
  --summary 'Dry-run validation only.' \
  --status ACTIVE \
  --priority P2 \
  --dry-run
```

For controlled live delivery, configure `WORLDSHEPHERD_DISCORD_WEBHOOK_URL` in the runtime environment. Never commit or pass the webhook URL as a CLI argument.

See `../../docs/DISCORD_INTEGRATION_RUNBOOK.md` for the complete security and validation boundary.
