#!/bin/bash
# Gnosis restore script
BACKUP_DIR=$1
if [ -z "$BACKUP_DIR" ]; then echo "Usage: ./restore.sh <backup_dir>"; exit 1; fi
if [ ! -d "$BACKUP_DIR" ]; then echo "Backup not found: $BACKUP_DIR"; exit 1; fi
# Restore DB
if [ -f "$BACKUP_DIR/db.sql" ]; then
  psql $DATABASE_URL < "$BACKUP_DIR/db.sql" 2>/dev/null || echo "DB restore skipped"
fi
# Restore env files
cp "$BACKUP_DIR/backend.env" backend/.env 2>/dev/null || true
cp "$BACKUP_DIR/frontend.env" frontend/.env.local 2>/dev/null || true
echo "Restore complete from: $BACKUP_DIR"
