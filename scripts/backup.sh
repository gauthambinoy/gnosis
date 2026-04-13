#!/bin/bash
# Gnosis backup script
BACKUP_DIR="./backups/$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"
# Backup PostgreSQL if available
if command -v pg_dump &> /dev/null; then
  pg_dump $DATABASE_URL > "$BACKUP_DIR/db.sql" 2>/dev/null || echo "DB backup skipped"
fi
# Backup .env files
cp backend/.env "$BACKUP_DIR/backend.env" 2>/dev/null || true
cp frontend/.env.local "$BACKUP_DIR/frontend.env" 2>/dev/null || true
# Backup uploaded files if any
tar czf "$BACKUP_DIR/uploads.tar.gz" backend/uploads 2>/dev/null || true
echo "Backup complete: $BACKUP_DIR"
