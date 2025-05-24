# Martin Standalone



## Creation Prompt
Write me a python flask app that will run in Heroku and is password protected this app should allow me to interact with AWS Bedrock large language models. All necessary files should be created to support direct deployment into heroku. The app should use bootstrap 5.3 for look and feel, it should retain chat history using a SQLite DB. I want it to use us-east-1 as the region and use Anthropic Claude 4 as the main model. I want to set the key and secret in as a heroku environment variable. I want the site to have an option to add more models by defining name and the model ARN.