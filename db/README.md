# Database
Version: MariaDB 10.3.27

## Setup
1. Run `sudo mysql -u root` command in terminal to start up MySQL CLI
1. In MySQL CLI:
  1. Create new database using `CREATE DATABASE <DB_NAME>;`
  1. If no existing database user, create new user with `CREATE USER '<USERNAME>'@'localhost';`
  1. Grant privileges to user with `GRANT ALL PRIVILEGES ON <DB_NAME>.* TO '<USERNAME>'@'localhost';`
  1. Flush privileges with `FLUSH PRIVILEGES;`
1. Run `mysql -u <USERNAME> <DB_NAME> < setup.sql` command in terminal

## Cleanup
1. Run `mysql -u <USERNAME> <DB_NAME> < clean.sql` command in terminal
