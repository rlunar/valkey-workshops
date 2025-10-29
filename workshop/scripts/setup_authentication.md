## MySQL Commands

```sql
-- Create user
CREATE USER 'flughafen'@'localhost' IDENTIFIED BY 'flughafen';

-- Grant all privileges on flughafendb database
GRANT ALL PRIVILEGES ON flughafendb.* TO 'flughafen'@'localhost';
GRANT PROCESS ON *.* TO 'flughafen'@'localhost';

-- Apply changes
FLUSH PRIVILEGES;
```

## Update .env file

```env
DB_HOST=localhost
DB_PORT=3306
DB_USER=flughafen
DB_PASSWORD=flughafen
DB_NAME=flughafendb
```

## Execute the SQL commands

```bash
# Connect as root and run the commands
mysql -u root -p -e "
CREATE DATABASE IF NOT EXISTS flughafendb CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS 'flughafen_user'@'localhost' IDENTIFIED BY 'flughafen_password';
GRANT ALL PRIVILEGES ON flughafendb.* TO 'flughafen_user'@'localhost';
GRANT PROCESS ON *.* TO 'flughafen_user'@'localhost';
FLUSH PRIVILEGES;
"
```


## Test the new user

```bash
mycli -u flughafen -pflughafen flughafendb
```

----

## PostgreSQL Commands

```sql
-- Create user
CREATE USER flughafen WITH PASSWORD 'flughafen';

-- Grant all privileges on flughafendb database
GRANT ALL PRIVILEGES ON DATABASE flughafendb TO flughafen;

-- Grant schema privileges (if needed)
GRANT ALL ON SCHEMA public TO flughafen;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO flughafen;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO flughafen;
```

## Update .env file

```env
DB_HOST=localhost
DB_PORT=5432
DB_USER=flughafen
DB_PASSWORD=flughafen
DB_NAME=flughafendb
```

## Execute the SQL commands

```bash
# Connect as postgres user and run the commands
psql -U postgres -c "
CREATE USER flughafen WITH PASSWORD 'flughafen';
GRANT ALL PRIVILEGES ON DATABASE flughafendb TO flughafen;
"
```

# Connect to the database and grant schema privileges

```bash
psql -U postgres -d flughafendb -c "
GRANT ALL ON SCHEMA public TO flughafen;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO flughafen;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO flughafen;
"
```

## Test the new user

```bash
psql -U flughafen -d flughafendb
```
