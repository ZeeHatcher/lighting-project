#!/bin/bash
yum update -y
yum install -y git

cd /home/ec2-user/

git clone https://github.com/ZeeHatcher/lighting-project.git
rm -fr www
mkdir www
cp -r lighting-project/web_app/ www/app/
rm -fr lighting-project

mkdir .venv
python3 -m venv .venv/flask-app
source .venv/flask-app/bin/activate
python -m pip install -r www/app/requirements.txt
deactivate

tee /etc/systemd/system/flask-app.service > /dev/null <<EOT
[Unit]
Description=Flask Web Application Server using Gunicorn
After=network.target

[Service]
User=ec2-user
Group=ec2-user
WorkingDirectory=/home/ec2-user/www/app
Environment="PATH=/home/ec2-user/.venv/flask-app/bin"
Environment="AWS_DEFAULT_REGION=ap-southeast-1"
Environment="S3_BUCKET=<S3_BUCKET>"
Environment="COGNITO_USER_CLIENT_ID=<CLIENT_ID>"
Environment="USERPOOL_ID=<USERPOOL_ID>"
ExecStart=/bin/bash -c 'source /home/ec2-user/.venv/flask-app/bin/activate; gunicorn --bind 0.0.0.0:5000 wsgi:app'
Restart=always

[Install]
WantedBy=multi-user.target
EOT
mkdir /tmp/flask-app
systemctl enable flask-app --now
