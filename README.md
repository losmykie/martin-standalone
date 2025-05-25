# AWS Bedrock Chat Application

A Flask-based web application for interacting with AWS Bedrock large language models, specifically designed to work with Anthropic Claude 4.

## Features

- Password-protected access
- Chat interface with AWS Bedrock models
- Chat history stored in SQLite database
- Support for multiple models
- Bootstrap 5.3 UI
- Docker and Docker Compose support

## Setup and Installation

### Local Development

1. Clone this repository
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Run the application:
   ```
   python app.py
   ```

### Using Docker Compose

1. Update the environment variables in `docker-compose.yml` with your AWS credentials
2. Run the application:
   ```
   docker-compose up --build
   ```
3. Access the application at http://localhost:5004

## Environment Variables

- `SECRET_KEY`: Flask secret key for session security
- `ADMIN_PASSWORD`: Password for the admin user
- `AWS_ACCESS_KEY_ID`: AWS access key with Bedrock permissions
- `AWS_SECRET_ACCESS_KEY`: AWS secret key

## Default Login

- Username: `admin`
- Password: Value of `ADMIN_PASSWORD` environment variable (default: `password`)

## Adding Models

You can add additional AWS Bedrock models through the Models page in the application. The default model is Claude 4, but you can add others like Claude 3 Haiku or Claude 3 Opus.

## License

MIT