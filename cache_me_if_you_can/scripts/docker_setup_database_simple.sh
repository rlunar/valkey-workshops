# Start container
docker run -d --rm --name flughafendb_mariadb \
  -p 23306:3306 \
  -e MYSQL_ROOT_PASSWORD=flughafendb_password \
  rlunar/flughafendb_mariadb:10.11-20251127

sleep 15

docker ps

# Create database
docker exec flughafendb_mariadb mariadb -u root -pflughafendb_password \
  -e "CREATE DATABASE IF NOT EXISTS flughafendb_large;"

# Create user with '%' wildcard (not '*')
docker exec flughafendb_mariadb mariadb -u root -pflughafendb_password \
  -e "CREATE USER IF NOT EXISTS 'flughafen_user'@'%' IDENTIFIED BY 'flughafen_password';"

# Grant privileges
docker exec flughafendb_mariadb mariadb -u root -pflughafendb_password \
  -e "GRANT ALL PRIVILEGES ON flughafendb_large.* TO 'flughafen_user'@'%';"

docker exec flughafendb_mariadb mariadb -u root -pflughafendb_password \
  -e "GRANT PROCESS ON *.* TO 'flughafen_user'@'%';"

docker exec flughafendb_mariadb mariadb -u root -pflughafendb_password \
  -e "FLUSH PRIVILEGES;"