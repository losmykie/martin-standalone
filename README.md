# AWS Bedrock Chat

A password-protected Flask web application for interacting with AWS Bedrock large language models. This application is designed to be deployed on Heroku and uses Bootstrap 5.3 for a modern, responsive user interface.

## Features

- **Password Protection**: Secure access to the application
- **AWS Bedrock Integration**: Interact with various AWS Bedrock LLMs
- **Chat History**: Persistent chat history stored in SQLite database
- **Model Management**: Add and manage different LLM models
- **Responsive Design**: Bootstrap 5.3 for a clean, modern UI
- **Heroku Ready**: Configured for easy deployment to Heroku

## Prerequisites

- Python 3.11+
- AWS account with Bedrock access
- AWS Access Key and Secret Key with Bedrock permissions
- Heroku account (for deployment)

## Local Development Setup

1. Clone the repository:
   ```
   git clone <repository-url>
   cd aws-bedrock-chat
   ```

2. Create a virtual environment and install dependencies:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. Create a `.env` file based on the example:
   ```
   cp .env.example .env
   ```

4. Edit the `.env` file with your AWS credentials and desired admin password:
   ```
   SECRET_KEY=your_random_secret_key
   AWS_ACCESS_KEY_ID=your_aws_access_key
   AWS_SECRET_ACCESS_KEY=your_aws_secret_key
   ADMIN_USERNAME=admin
   ADMIN_PASSWORD=your_secure_password
   ```

5. Run the application:
   ```
   python app.py
   ```

6. Access the application at `http://localhost:5000`

## Deploying to Heroku

1. Create a new Heroku app:
   ```
   heroku create your-app-name
   ```

2. Set the required environment variables:
   ```
   heroku config:set SECRET_KEY=your_random_secret_key
   heroku config:set AWS_ACCESS_KEY_ID=your_aws_access_key
   heroku config:set AWS_SECRET_ACCESS_KEY=your_aws_secret_key
   heroku config:set ADMIN_USERNAME=admin
   heroku config:set ADMIN_PASSWORD=your_secure_password
   ```

3. Deploy the application:
   ```
   git push heroku main
   ```

4. Open the application:
   ```
   heroku open
   ```

## Usage

1. **Login**: Access the application using the admin credentials set in the environment variables.

2. **Chat**: Start a new chat session and interact with the default LLM (Claude 3.5 Sonnet).

3. **Models**: Add new models by providing a name and the AWS Bedrock model ARN.

4. **Chat History**: All conversations are saved and can be accessed from the sidebar.

## Available AWS Bedrock Models

The application comes pre-configured with Claude 3.5 Sonnet as the default model, but you can add other models such as:

- Claude 3 Opus: `anthropic.claude-3-opus-20240229-v1:0`
- Claude 3 Sonnet: `anthropic.claude-3-sonnet-20240229-v1:0`
- Claude 3 Haiku: `anthropic.claude-3-haiku-20240307-v1:0`
- Claude 2.1: `anthropic.claude-v2:1`

## Security Notes

- The application uses environment variables for sensitive information
- Password is stored using secure hashing
- For production use, consider using a more robust database solution
- Ensure your AWS credentials have appropriate permissions

## License

This project is licensed under the MIT License - see the LICENSE file for details.