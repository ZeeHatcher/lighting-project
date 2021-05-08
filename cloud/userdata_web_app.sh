#!/bin/bash

# Install dependencies
sudo yum update -y
sudo yum group install -y "Development Tools"
sudo yum install -y python3-devel mariadb mariadb-devel
pip install --user Flask python-dotenv mysql boto3

# Checkout web app files

# Export environment variables
export DB_HOST=
export DB_USERNAME=
export DB_PASSWORD=
export DB_DATABASE=
