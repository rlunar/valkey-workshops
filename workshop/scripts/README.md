# Database Backup and Restore Scripts

This directory contains enhanced scripts for backing up and restoring the FlughafenDB database, supporting both MySQL/MariaDB and PostgreSQL.

## Scripts Overview

### `backup.sh`
Creates a backup of the FlughafenDB database based on the configuration in `.env`.

**Features:**
- Supports MySQL, MariaDB, and PostgreSQL
- Automatic database type detection from `.env`
- Connection testing before backup
- Automatic compression with gzip
- Timestamped backup files
- Automatic cleanup of old backups (>7 days)
- Colored output for better readability
- Error handling and validation

### `restore.sh`
Restores the FlughafenDB database from a backup file.

**Features:**
- Interactive backup file selection
- Support for compressed (.gz) backup files
- Database connection testing
- Confirmation prompts for safety
- Support for both MySQL/MariaDB and PostgreSQL
- Colored output and progress indicators

### `test-backup.sh`
Tests the backup configuration without performing an actual backup.

**Features:**
- Validates `.env` configuration
- Checks for required database client tools
- Tests database connectivity
- Lists existing backups
- Provides installation instructions for missing tools

## Prerequisites

### For MySQL/MariaDB
```bash
# Ubuntu/Debian
sudo apt-get install mysql-client

# macOS
brew install mysql-client

# CentOS/RHEL
sudo yum install mysql
```

### For PostgreSQL
```bash
# Ubuntu/Debian
sudo apt-get install postgresql-client

# macOS
brew install postgresql

# CentOS/RHEL
sudo yum install postgresql
```

## Configuration

1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` with your database credentials:
   ```bash
   # Database type: mysql, mariadb, postgresql, or postgres
   DB_TYPE=mysql
   
   # Database connection details
   DB_HOST=localhost
   DB_PORT=3306
   DB_NAME=flughafendb
   DB_USER=your_username
   DB_PASSWORD=your_password
   ```

## Usage

### Test Configuration
Before running backups, test your configuration:
```bash
./scripts/test-backup.sh
```

### Create Backup
```bash
./scripts/backup.sh
```

This will:
- Create a timestamped backup file in `./backups/`
- Compress the backup with gzip
- Clean up old backups (>7 days)

### Restore Database

#### Interactive Mode (Recommended)
```bash
./scripts/restore.sh
```

This will show available backups and let you select one.

#### Direct File Restore
```bash
./scripts/restore.sh backups/flughafendb_backup_20231028_143022.sql.gz
```

## Backup File Format

Backup files are named with the following pattern:
```
flughafendb_backup_YYYYMMDD_HHMMSS.sql[.gz]
```

Examples:
- `flughafendb_backup_20231028_143022.sql.gz` (compressed)
- `flughafendb_backup_20231028_143022.sql` (uncompressed)

## Directory Structure

```
scripts/
├── README.md           # This file
├── backup.sh          # Main backup script
├── restore.sh         # Main restore script
└── test-backup.sh     # Configuration test script

backups/               # Created automatically
├── flughafendb_backup_20231028_143022.sql.gz
├── flughafendb_backup_20231027_120000.sql.gz
└── ...
```

## Automation

### Cron Job Example
To run daily backups at 2 AM:

```bash
# Edit crontab
crontab -e

# Add this line
0 2 * * * cd /path/to/valkey-caching-workshop && ./scripts/backup.sh >> /var/log/flughafendb-backup.log 2>&1
```

### Systemd Timer Example
Create `/etc/systemd/system/flughafendb-backup.service`:

```ini
[Unit]
Description=FlughafenDB Backup
After=network.target

[Service]
Type=oneshot
User=your_user
WorkingDirectory=/path/to/valkey-caching-workshop
ExecStart=/path/to/valkey-caching-workshop/scripts/backup.sh
```

Create `/etc/systemd/system/flughafendb-backup.timer`:

```ini
[Unit]
Description=Run FlughafenDB backup daily
Requires=flughafendb-backup.service

[Timer]
OnCalendar=daily
Persistent=true

[Install]
WantedBy=timers.target
```

Enable and start:
```bash
sudo systemctl enable flughafendb-backup.timer
sudo systemctl start flughafendb-backup.timer
```

## Troubleshooting

### Common Issues

1. **"mysql client not found"**
   - Install MySQL client tools (see Prerequisites)

2. **"Connection failed"**
   - Check database server is running
   - Verify credentials in `.env`
   - Check firewall settings

3. **"Permission denied"**
   - Make scripts executable: `chmod +x scripts/*.sh`
   - Check backup directory permissions

4. **"Backup file is empty"**
   - Check database user permissions
   - Verify database name exists
   - Check disk space

### Debug Mode
Run scripts with debug output:
```bash
bash -x ./scripts/backup.sh
```

### Manual Testing
Test database connection manually:

**MySQL:**
```bash
mysql -h $DB_HOST -P $DB_PORT -u $DB_USER -p$DB_PASSWORD $DB_NAME -e "SELECT COUNT(*) FROM airport;"
```

**PostgreSQL:**
```bash
PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c "SELECT COUNT(*) FROM airport;"
```

## Security Considerations

1. **Password Security**: The `.env` file contains sensitive credentials. Ensure it's:
   - Not committed to version control (included in `.gitignore`)
   - Has restricted permissions: `chmod 600 .env`

2. **Backup Security**: Backup files may contain sensitive data:
   - Store in secure location
   - Consider encryption for long-term storage
   - Implement proper access controls

3. **Network Security**: For remote databases:
   - Use SSL/TLS connections when possible
   - Consider VPN for database access
   - Restrict database access by IP

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Run `./scripts/test-backup.sh` to validate configuration
3. Check database server logs
4. Verify network connectivity and credentials