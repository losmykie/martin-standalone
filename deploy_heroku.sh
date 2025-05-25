#!/bin/bash

# Heroku deployment script for AWS Bedrock Chat application

# Check if Heroku CLI is installed
if ! command -v heroku &> /dev/null; then
    echo "Heroku CLI is not installed. Please install it first:"
    echo "https://devcenter.heroku.com/articles/heroku-cli"
    exit 1
fi

# Check if logged in to Heroku
heroku whoami &> /dev/null
if [ $? -ne 0 ]; then
    echo "You are not logged in to Heroku. Please login first:"
    heroku login
fi

# Ask for app name
read -p "Enter your Heroku app name (leave blank to create a random name): " app_name

# Create Heroku app
if [ -z "$app_name" ]; then
    echo "Creating Heroku app with random name..."
    heroku create
    app_name=$(heroku apps:info --json | jq -r '.app.name')
else
    echo "Creating Heroku app: $app_name"
    heroku create $app_name
fi

# Set environment variables
echo "Setting up environment variables..."

# Generate random secret key
secret_key=$(openssl rand -hex 16)
heroku config:set SECRET_KEY=$secret_key --app $app_name

# AWS credentials
read -p "Enter your AWS Access Key ID: " aws_access_key
read -p "Enter your AWS Secret Access Key: " aws_secret_key
heroku config:set AWS_ACCESS_KEY_ID=$aws_access_key --app $app_name
heroku config:set AWS_SECRET_ACCESS_KEY=$aws_secret_key --app $app_name

# Admin credentials
read -p "Enter admin username (default: admin): " admin_username
admin_username=${admin_username:-admin}
read -s -p "Enter admin password: " admin_password
echo ""
heroku config:set ADMIN_USERNAME=$admin_username --app $app_name
heroku config:set ADMIN_PASSWORD=$admin_password --app $app_name

# Add PostgreSQL addon
echo "Adding PostgreSQL database..."
heroku addons:create heroku-postgresql:mini --app $app_name

# Deploy to Heroku
echo "Deploying to Heroku..."
git push heroku main

# Run database initialization script
echo "Initializing database..."
heroku run python init_db.py --app $app_name

# Open the app
heroku open --app $app_name

echo ""
echo "Deployment complete! Your app is now running on Heroku."
echo "Login with:"
echo "  Username: $admin_username"
echo "  Password: (the password you entered)"