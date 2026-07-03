#!/bin/bash
# Refresh the Grace Drinks host backup (durable safety net on the host bind-mount).
# Run from the host:  docker exec docker-frappe-1 bash /workspace/backup-grace-drinks.sh
set -e
cd /home/frappe/frappe-bench
bench --site hrms.localhost backup --with-files
B=sites/hrms.localhost/private/backups
PRE=$(ls -t "$B"/*-database.sql.gz | head -1 | sed 's/-database.sql.gz//')
STAMP=$(basename "$PRE" | cut -d- -f1)
mkdir -p /workspace/backups/latest "/workspace/backups/$STAMP"
rm -f /workspace/backups/latest/*
cp ${PRE}-* /workspace/backups/latest/
cp ${PRE}-* "/workspace/backups/$STAMP/"
echo "Backup refreshed -> /workspace/backups/latest  (timestamped copy: /workspace/backups/$STAMP)"
ls -lh /workspace/backups/latest/
