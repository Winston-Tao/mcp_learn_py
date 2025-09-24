#!/bin/bash

# MCP Learning Server Backup Script
# This script can be run standalone or as part of a Docker container

set -euo pipefail

# Configuration
BACKUP_DIR="${BACKUP_DIR:-/backups}"
DATA_DIR="${DATA_DIR:-/data}"
MAX_BACKUPS="${MAX_BACKUPS:-7}"  # Keep last 7 backups
BACKUP_NAME_PREFIX="${BACKUP_NAME_PREFIX:-mcp-backup}"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

log_info() {
    echo -e "[$(date '+%Y-%m-%d %H:%M:%S')] INFO: $1"
}

log_success() {
    echo -e "[$(date '+%Y-%m-%d %H:%M:%S')] ${GREEN}SUCCESS${NC}: $1"
}

log_warning() {
    echo -e "[$(date '+%Y-%m-%d %H:%M:%S')] ${YELLOW}WARNING${NC}: $1"
}

log_error() {
    echo -e "[$(date '+%Y-%m-%d %H:%M:%S')] ${RED}ERROR${NC}: $1"
}

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

# Generate backup filename with timestamp
BACKUP_TIMESTAMP=$(date '+%Y%m%d_%H%M%S')
BACKUP_FILENAME="${BACKUP_NAME_PREFIX}_${BACKUP_TIMESTAMP}.tar.gz"
BACKUP_PATH="$BACKUP_DIR/$BACKUP_FILENAME"

log_info "Starting backup process"
log_info "Backup will be saved to: $BACKUP_PATH"

# Check if data directory exists
if [[ ! -d "$DATA_DIR" ]]; then
    log_warning "Data directory $DATA_DIR does not exist, creating empty backup"
    echo "No data to backup - directory does not exist" > /tmp/backup_note.txt
    tar -czf "$BACKUP_PATH" -C /tmp backup_note.txt
    rm /tmp/backup_note.txt
else
    # Create the backup
    log_info "Creating compressed backup of $DATA_DIR"

    # Change to parent directory to avoid including full path in archive
    PARENT_DIR=$(dirname "$DATA_DIR")
    DATA_DIRNAME=$(basename "$DATA_DIR")

    if tar -czf "$BACKUP_PATH" -C "$PARENT_DIR" "$DATA_DIRNAME" 2>/dev/null; then
        BACKUP_SIZE=$(du -h "$BACKUP_PATH" | cut -f1)
        log_success "Backup created successfully (Size: $BACKUP_SIZE)"
    else
        log_error "Failed to create backup"
        exit 1
    fi
fi

# Verify backup integrity
log_info "Verifying backup integrity"
if tar -tzf "$BACKUP_PATH" >/dev/null 2>&1; then
    log_success "Backup integrity verified"
else
    log_error "Backup integrity check failed"
    rm -f "$BACKUP_PATH"
    exit 1
fi

# Clean up old backups
log_info "Cleaning up old backups (keeping last $MAX_BACKUPS)"

# Find and remove old backups, keeping the most recent ones
OLD_BACKUPS=$(find "$BACKUP_DIR" -name "${BACKUP_NAME_PREFIX}_*.tar.gz" -type f -print0 | \
              xargs -0 ls -t | \
              tail -n +$((MAX_BACKUPS + 1)))

if [[ -n "$OLD_BACKUPS" ]]; then
    echo "$OLD_BACKUPS" | xargs rm -f
    REMOVED_COUNT=$(echo "$OLD_BACKUPS" | wc -l)
    log_info "Removed $REMOVED_COUNT old backup(s)"
else
    log_info "No old backups to remove"
fi

# Display backup statistics
log_info "Backup Statistics:"
echo "=================="
echo "Backup file: $BACKUP_FILENAME"
echo "Backup size: $(du -h "$BACKUP_PATH" | cut -f1)"
echo "Total backups: $(find "$BACKUP_DIR" -name "${BACKUP_NAME_PREFIX}_*.tar.gz" -type f | wc -l)"
echo "Backup directory usage: $(du -sh "$BACKUP_DIR" | cut -f1)"
echo "=================="

# List current backups
log_info "Current backups:"
find "$BACKUP_DIR" -name "${BACKUP_NAME_PREFIX}_*.tar.gz" -type f -exec ls -lh {} \; | \
    sort -k9 -r | \
    head -n "$MAX_BACKUPS"

log_success "Backup process completed successfully"

# Optional: Send notification (uncomment and configure as needed)
# if command -v mail >/dev/null 2>&1; then
#     echo "MCP Server backup completed successfully at $(date)" | \
#         mail -s "MCP Backup Success" admin@your-domain.com
# fi

exit 0