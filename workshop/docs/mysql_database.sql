-- MySQL Database Setup for Flughafen DB
CREATE DATABASE IF NOT EXISTS flughafendb CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS 'flughafen_user'@'localhost' IDENTIFIED BY 'your_secure_password';
GRANT ALL PRIVILEGES ON flughafendb.* TO 'flughafen_user'@'localhost';
FLUSH PRIVILEGES;