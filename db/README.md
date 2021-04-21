# Database
Version: MariaDB 10.3.27

## Setup
1. Run `sudo mysql -u root` command in CLI
1. Create **lighting_db** using `CREATE DATABASE lighting_db;`
1. If no existing database user, create new user with `CREATE USER '<USERNAME>'@'localhost';`
1. Grant privileges to user with `GRANT ALL PRIVILEGES ON lighting_db.* TO '<USERNAME>'@'localhost';`
1. Flush privileges with `FLUSH PRIVILEGES;`
1. Run `mysql -u <USERNAME> lighting_db < setup.sql` command in CLI

## Cleanup
1. Run `mysql -u <USERNAME> lighting_db < clean.sql` command in CLI
