# Waifu Bot

## Current release setup

This version is intended to run as **one process** per bot copy.
The runtime lock prevents a second instance from starting in the same project folder.

## Logging

Runtime logs are written to:

- `logs/bot.log`
- `logs/errors.log`

## Backup

Create a PostgreSQL backup with:

```bash
python scripts/backup_db.py
```

Optional flags:

- `--output-dir backups`
- `--filename my_backup.sql`

The script uses `pg_dump`, so PostgreSQL client tools must be installed.

## Database index

Added index:

- `categories(parent_id)`

That keeps nested category navigation fast as the catalog grows.
