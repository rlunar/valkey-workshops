-- PostgreSQL Database Setup for Flughafen DB
CREATE DATABASE flughafendb WITH ENCODING 'UTF8' LC_COLLATE='en_US.UTF-8' LC_CTYPE='en_US.UTF-8';
CREATE USER flughafen_user WITH PASSWORD 'your_secure_password';
GRANT ALL PRIVILEGES ON DATABASE flughafendb TO flughafen_user;