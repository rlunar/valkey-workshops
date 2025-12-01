FROM mariadb:10.11

# Build argument for the SQL dump file path (relative to build context)
ARG DUMP_FILE=data/flughafendb_large_20251127_150159.sql.gz

# Environment variables
ENV MYSQL_ROOT_PASSWORD=flughafendb_password
ENV MYSQL_DATABASE=flughafendb_large
ENV BAKED_DATADIR=/var/lib/mysql_baked

# Copy the database dump into the image temp space
COPY ${DUMP_FILE} /tmp/flughafendb_dump.sql.gz

# The "Baking" Process:
# 1. Create custom directory (bypassing default VOLUME)
# 2. Initialize DB
# 3. Start DB
# 4. Import Local Data
# 5. Shutdown
RUN mkdir -p $BAKED_DATADIR && \
    chown -R mysql:mysql $BAKED_DATADIR && \
    # Initialize the database files in the custom directory
    mysql_install_db --user=mysql --datadir=$BAKED_DATADIR && \
    # Start MariaDB in background (skip networking for speed/security during build)
    mysqld --user=mysql --datadir=$BAKED_DATADIR --skip-networking & \
    PID=$! && \
    # Wait for DB to start
    sleep 10 && \
    # Create DB and Import dump file
    mysql -u root --socket=/run/mysqld/mysqld.sock -e "CREATE DATABASE IF NOT EXISTS flughafendb_large;" && \
    echo "Importing database dump..." && \
    gunzip -c /tmp/flughafendb_dump.sql.gz | mysql -u root --socket=/run/mysqld/mysqld.sock flughafendb_large && \
    # Grant remote access for root user
    echo "Granting remote access..." && \
    mysql -u root --socket=/run/mysqld/mysqld.sock -e "GRANT ALL PRIVILEGES ON *.* TO 'root'@'%' IDENTIFIED BY 'flughafendb_password' WITH GRANT OPTION;" && \
    mysql -u root --socket=/run/mysqld/mysqld.sock -e "FLUSH PRIVILEGES;" && \
    # Clean Shutdown
    mysqladmin -u root --socket=/run/mysqld/mysqld.sock shutdown && \
    # Remove source files to keep image smaller
    rm /tmp/flughafendb_dump.sql.gz

# Configure MariaDB to read from the baked directory and bind to all interfaces
# Add performance tuning for better query performance
RUN echo "[mysqld]\n\
datadir=$BAKED_DATADIR\n\
bind-address=0.0.0.0\n\
# Performance tuning\n\
innodb_buffer_pool_size=1G\n\
innodb_log_file_size=256M\n\
innodb_flush_log_at_trx_commit=2\n\
innodb_flush_method=O_DIRECT\n\
max_connections=200\n\
query_cache_size=0\n\
query_cache_type=0" > /etc/mysql/conf.d/baked_data.cnf

CMD ["mysqld"]