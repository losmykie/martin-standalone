import os
import json
import boto3
import secrets
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length
from dotenv import load_dotenv

# Load environment variables from .env file if present (for local development)
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', secrets.token_hex(16))
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///bedrock_chat.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# If DATABASE_URL is provided by Heroku (postgres), adjust it for SQLAlchemy
if app.config['SQLALCHEMY_DATABASE_URI'].startswith('postgres://'):
    app.config['SQLALCHEMY_DATABASE_URI'] = app.config['SQLALCHEMY_DATABASE_URI'].replace('postgres://', 'postgresql://', 1)

# Initialize database
db = SQLAlchemy(app)

# Initialize login manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# AWS Configuration
AWS_REGION = 'us-east-1'
DEFAULT_MODEL = 'anthropic.claude-3-5-sonnet-20240620-v1:0'  # Claude 3.5 Sonnet
DEFAULT_MODEL_NAME = 'Claude 3.5 Sonnet'

# Database Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class ChatSession(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(100), default="New Chat")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    messages = db.relationship('Message', backref='chat_session', lazy=True, cascade="all, delete-orphan")

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    chat_session_id = db.Column(db.Integer, db.ForeignKey('chat_session.id'), nullable=False)
    role = db.Column(db.String(10), nullable=False)  # 'user' or 'assistant'
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    model_id = db.Column(db.Integer, db.ForeignKey('model.id'))

class Model(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    model_arn = db.Column(db.String(200), nullable=False)
    is_default = db.Column(db.Boolean, default=False)
    
# Forms
class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

class ChatForm(FlaskForm):
    message = TextAreaField('Message', validators=[DataRequired()])
    submit = SubmitField('Send')

class ModelForm(FlaskForm):
    name = StringField('Model Name', validators=[DataRequired(), Length(min=1, max=100)])
    model_arn = StringField('Model ARN', validators=[DataRequired(), Length(min=1, max=200)])
    submit = SubmitField('Add Model')

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Routes
@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('chat'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('chat'))
    
    form = LoginForm()
    
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        
        if user and user.check_password(form.password.data):
            login_user(user)
            next_page = request.args.get('next')
            return redirect(next_page or url_for('chat'))
        else:
            flash('Invalid username or password', 'danger')
    
    return render_template('login.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/chat', methods=['GET', 'POST'])
@login_required
def chat():
    form = ChatForm()
    
    # Get current chat session or create a new one
    chat_id = request.args.get('chat_id', None)
    
    if chat_id:
        chat_session = ChatSession.query.filter_by(id=chat_id, user_id=current_user.id).first_or_404()
    else:
        chat_session = ChatSession(user_id=current_user.id)
        db.session.add(chat_session)
        db.session.commit()
    
    # Get all chat sessions for the sidebar
    chat_sessions = ChatSession.query.filter_by(user_id=current_user.id).order_by(ChatSession.created_at.desc()).all()
    
    # Get available models
    models = Model.query.all()
    selected_model_id = request.args.get('model_id', None)
    
    if selected_model_id:
        selected_model = Model.query.get(selected_model_id)
    else:
        selected_model = Model.query.filter_by(is_default=True).first()
        if not selected_model and models:
            selected_model = models[0]
    
    if form.validate_on_submit():
        user_message = Message(
            chat_session_id=chat_session.id,
            role='user',
            content=form.message.data,
            model_id=selected_model.id if selected_model else None
        )
        db.session.add(user_message)
        
        # Update chat title if it's the first message
        if len(chat_session.messages) == 0:
            # Use the first few words of the first message as the title
            title_text = form.message.data[:50] + ('...' if len(form.message.data) > 50 else '')
            chat_session.title = title_text
        
        # Get response from AWS Bedrock
        try:
            response = get_bedrock_response(form.message.data, chat_session.messages, selected_model)
            
            assistant_message = Message(
                chat_session_id=chat_session.id,
                role='assistant',
                content=response,
                model_id=selected_model.id if selected_model else None
            )
            db.session.add(assistant_message)
            
        except Exception as e:
            flash(f"Error: {str(e)}", "danger")
            app.logger.error(f"Bedrock API error: {str(e)}")
        
        db.session.commit()
        return redirect(url_for('chat', chat_id=chat_session.id, model_id=selected_model.id if selected_model else None))
    
    return render_template(
        'chat.html', 
        form=form, 
        chat_session=chat_session, 
        chat_sessions=chat_sessions,
        models=models,
        selected_model=selected_model
    )

@app.route('/chat/new')
@login_required
def new_chat():
    chat_session = ChatSession(user_id=current_user.id)
    db.session.add(chat_session)
    db.session.commit()
    return redirect(url_for('chat', chat_id=chat_session.id))

@app.route('/chat/<int:chat_id>/delete', methods=['POST'])
@login_required
def delete_chat(chat_id):
    chat_session = ChatSession.query.filter_by(id=chat_id, user_id=current_user.id).first_or_404()
    db.session.delete(chat_session)
    db.session.commit()
    return redirect(url_for('chat'))

@app.route('/models', methods=['GET', 'POST'])
@login_required
def models():
    form = ModelForm()
    models = Model.query.all()
    
    if form.validate_on_submit():
        model = Model(
            name=form.name.data,
            model_arn=form.model_arn.data,
            is_default=False
        )
        db.session.add(model)
        db.session.commit()
        flash('Model added successfully', 'success')
        return redirect(url_for('models'))
    
    return render_template('models.html', form=form, models=models)

@app.route('/models/<int:model_id>/default', methods=['POST'])
@login_required
def set_default_model(model_id):
    # Reset all models to non-default
    Model.query.update({Model.is_default: False})
    
    # Set the selected model as default
    model = Model.query.get_or_404(model_id)
    model.is_default = True
    
    db.session.commit()
    flash(f'{model.name} set as default model', 'success')
    return redirect(url_for('models'))

@app.route('/models/<int:model_id>/delete', methods=['POST'])
@login_required
def delete_model(model_id):
    model = Model.query.get_or_404(model_id)
    db.session.delete(model)
    db.session.commit()
    flash('Model deleted successfully', 'success')
    return redirect(url_for('models'))

def get_bedrock_response(prompt, message_history, selected_model):
    """Get a response from AWS Bedrock"""
    aws_access_key = os.environ.get('AWS_ACCESS_KEY_ID')
    aws_secret_key = os.environ.get('AWS_SECRET_ACCESS_KEY')
    
    if not aws_access_key or not aws_secret_key:
        raise Exception("AWS credentials not found in environment variables")
    
    # Create a Bedrock client
    bedrock_client = boto3.client(
        service_name='bedrock-runtime',
        region_name=AWS_REGION,
        aws_access_key_id=aws_access_key,
        aws_secret_access_key=aws_secret_key
    )
    
    # Prepare message history for the model
    messages = []
    
    # Add message history
    for msg in message_history:
        if msg.role == 'user':
            messages.append({"role": "user", "content": msg.content})
        elif msg.role == 'assistant':
            messages.append({"role": "assistant", "content": msg.content})
    
    # Add the current prompt
    messages.append({"role": "user", "content": prompt})
    
    model_id = selected_model.model_arn if selected_model else DEFAULT_MODEL
    
    # Determine if this is an Anthropic Claude model
    if "anthropic" in model_id.lower():
        # Claude API format
        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 4096,
            "messages": messages
        }
    else:
        # Generic format for other models (may need adjustment for specific models)
        request_body = {
            "prompt": "\n".join([f"{m['role']}: {m['content']}" for m in messages]),
            "max_tokens": 4096
        }
    
    response = bedrock_client.invoke_model(
        modelId=model_id,
        body=json.dumps(request_body)
    )
    
    response_body = json.loads(response.get('body').read())
    
    # Extract the response text based on model type
    if "anthropic" in model_id.lower():
        return response_body.get('content', [{}])[0].get('text', 'No response')
    else:
        return response_body.get('completion', 'No response')

# Initialize the database and create admin user
def initialize_app():
    # Check if tables exist before creating them
    inspector = db.inspect(db.engine)
    if not inspector.has_table('user'):
        db.create_all()
    
    # Create admin user if it doesn't exist
    admin_username = os.environ.get('ADMIN_USERNAME', 'admin')
    admin_password = os.environ.get('ADMIN_PASSWORD')
    
    if admin_password:
        admin = User.query.filter_by(username=admin_username).first()
        if not admin:
            admin = User(username=admin_username)
            admin.set_password(admin_password)
            db.session.add(admin)
            db.session.commit()
    
    # Add default model if no models exist
    if Model.query.count() == 0:
        default_model = Model(
            name=DEFAULT_MODEL_NAME,
            model_arn=DEFAULT_MODEL,
            is_default=True
        )
        db.session.add(default_model)
        db.session.commit()

# Initialize the app when it starts - only in development
if __name__ == '__main__':
    with app.app_context():
        initialize_app()

# For local development
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        # Create admin user if it doesn't exist
        admin_username = os.environ.get('ADMIN_USERNAME', 'admin')
        admin_password = os.environ.get('ADMIN_PASSWORD', 'password')  # Default for local dev only
        
        admin = User.query.filter_by(username=admin_username).first()
        if not admin:
            admin = User(username=admin_username)
            admin.set_password(admin_password)
            db.session.add(admin)
            
        # Add default model if no models exist
        if Model.query.count() == 0:
            default_model = Model(
                name=DEFAULT_MODEL_NAME,
                model_arn=DEFAULT_MODEL,
                is_default=True
            )
            db.session.add(default_model)
            
        db.session.commit()
        
    app.run(debug=True)