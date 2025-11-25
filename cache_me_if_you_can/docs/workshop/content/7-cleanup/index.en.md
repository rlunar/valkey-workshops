# Module 7: Clean Up

## Overview

This module guides you through cleaning up the resources created during the workshop.

## Cleanup Steps

### 1. Stop Running Services

Stop any running services from the workshop:

```bash
# Stop the Airport App
# Stop Valkey instance (if running locally)
# Stop any demo scripts
```

### 2. Clear Valkey Data

If you want to clear all workshop data from Valkey:

```bash
# Connect to Valkey
valkey-cli

# Flush all data (use with caution!)
FLUSHALL

# Or selectively delete workshop keys
SCAN 0 MATCH workshop:*
# Then delete matched keys
```

### 3. Remove Local Files (Optional)

If you created any temporary files or logs:

```bash
# Remove logs
rm -rf logs/*

# Remove temporary files
rm -rf tmp/*
```

### 4. Database Cleanup (Optional)

If you want to reset the database to its original state:

```bash
# Restore from backup or re-run setup scripts
```

### 5. Environment Variables

Remove or reset any environment variables set for the workshop:

```bash
# Edit your .env file or unset variables
unset VALKEY_HOST
unset VALKEY_PORT
# etc.
```

## Verification

Verify cleanup was successful:

```bash
# Check Valkey is empty (if you flushed)
valkey-cli DBSIZE

# Check no workshop processes are running
ps aux | grep workshop
```

## Keep Learning

Even though the workshop is complete, you can:
- Keep the code for reference
- Experiment with different configurations
- Apply patterns to your own projects
- Revisit modules as needed

## Feedback

We'd love to hear your feedback on this workshop:
- What worked well?
- What could be improved?
- What additional topics would you like to see?

Thank you for participating in "Cache me if you can, Valkey edition"!
