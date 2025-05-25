import os
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import boto3
import json
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'default-dev-key')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///bedrock_chat.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Login manager setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Database models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
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

class Model(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    model_arn = db.Column(db.String(200), nullable=False)
    is_default = db.Column(db.Boolean, default=False)

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# Initialize database and add default model
with app.app_context():
    db.create_all()
    
    # Add default admin user if not exists
    if not User.query.filter_by(username='admin').first():
        admin = User(username='admin')
        admin.set_password(os.environ.get('ADMIN_PASSWORD', 'password'))
        db.session.add(admin)
    
    # Add default Claude 4 model if not exists
    if not Model.query.filter_by(name='Claude 4').first():
        claude_model = Model(
            name='Claude 4',
            model_arn='anthropic.claude-3-sonnet-20240229-v1:0',
            is_default=True
        )
        db.session.add(claude_model)
    
    db.session.commit()

# AWS Bedrock client
def get_bedrock_client():
    return boto3.client(
        service_name='bedrock-runtime',
        region_name='us-east-1',
        aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY')
    )

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
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('chat'))
        else:
            flash('Invalid username or password', 'error')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/chat')
@login_required
def chat():
    chat_sessions = ChatSession.query.filter_by(user_id=current_user.id).order_by(ChatSession.created_at.desc()).all()
    models = Model.query.all()
    default_model = Model.query.filter_by(is_default=True).first()
    
    active_chat_id = request.args.get('chat_id')
    active_chat = None
    messages = []
    
    if active_chat_id:
        active_chat = db.session.get(ChatSession, active_chat_id)
        if active_chat and active_chat.user_id == current_user.id:
            messages = Message.query.filter_by(chat_session_id=active_chat_id).order_by(Message.timestamp).all()
    
    return render_template('chat.html', 
                          chat_sessions=chat_sessions, 
                          active_chat=active_chat,
                          messages=messages,
                          models=models,
                          default_model=default_model)

@app.route('/chat/new', methods=['GET', 'POST'])
@login_required
def new_chat():
    chat = ChatSession(user_id=current_user.id)
    db.session.add(chat)
    db.session.commit()
    return redirect(url_for('chat', chat_id=chat.id))

@app.route('/chat/<int:chat_id>/delete', methods=['POST'])
@login_required
def delete_chat(chat_id):
    chat = ChatSession.query.get(chat_id)
    if not chat:
        flash('Chat not found', 'error')
        return redirect(url_for('chat'))
    
    if chat.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    db.session.delete(chat)
    db.session.commit()
    return redirect(url_for('chat'))

@app.route('/chat/<int:chat_id>/rename', methods=['POST'])
@login_required
def rename_chat(chat_id):
    chat = ChatSession.query.get(chat_id)
    if not chat:
        flash('Chat not found', 'error')
        return redirect(url_for('chat'))
        
    if chat.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    new_title = request.form.get('title')
    if new_title:
        chat.title = new_title
        db.session.commit()
    
    return redirect(url_for('chat', chat_id=chat.id))

@app.route('/api/chat', methods=['POST'])
@login_required
def process_message():
    data = request.json
    chat_id = data.get('chat_id')
    message_content = data.get('message')
    model_id = data.get('model_id')
    
    if not chat_id or not message_content:
        return jsonify({'error': 'Missing required parameters'}), 400
    
    chat = db.session.get(ChatSession, chat_id)
    if not chat or chat.user_id != current_user.id:
        return jsonify({'error': 'Chat not found or unauthorized'}), 404
    
    # Save user message
    user_message = Message(
        chat_session_id=chat_id,
        role='user',
        content=message_content
    )
    db.session.add(user_message)
    
    # Update chat title if it's the first message
    if len(chat.messages) == 0:
        # Use the first ~30 chars of the message as the chat title
        chat.title = message_content[:30] + ('...' if len(message_content) > 30 else '')
    
    db.session.commit()
    
    # Get model to use
    model = None
    if model_id:
        model = db.session.get(Model, model_id)
    if not model:
        model = Model.query.filter_by(is_default=True).first()
    
    if not model:
        return jsonify({'error': 'No model available'}), 500
    
    # Get chat history for context
    history = Message.query.filter_by(chat_session_id=chat_id).order_by(Message.timestamp).all()
    messages = []
    
    for msg in history:
        messages.append({
            "role": msg.role,
            "content": msg.content
        })
    
    try:
        # Call AWS Bedrock
        bedrock_client = get_bedrock_client()
        
        # Check if model is Anthropic (Claude)
        if "anthropic" in model.model_arn.lower():
            # Format request based on Claude's API
            request_body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 4096,
                "messages": messages
            }
            
            # Log the model being used
            logging.info(f"Using Claude model: {model.model_arn}")
        else:
            # Generic format for other models
            request_body = {
                "prompt": "\n\n".join([f"{msg['role']}: {msg['content']}" for msg in messages]),
                "max_tokens": 4096
            }
            
            # Log the model being used
            logging.info(f"Using non-Claude model: {model.model_arn}")
        
        # Try model invocation with inference profile support
        try:
            # First try direct model invocation
            response = bedrock_client.invoke_model(
                modelId=model.model_arn,
                body=json.dumps(request_body)
            )
            response_body = json.loads(response.get('body').read())
        except Exception as invoke_error:
            # If error mentions inference profile, try to extract the model ID
            error_msg = str(invoke_error)
            if "inference profile" in error_msg.lower():
                # Log the error for debugging
                logging.error(f"Inference profile error: {error_msg}")
                
                # Check if the model ARN contains a model ID we can use
                if "anthropic.claude-opus-4" in model.model_arn.lower():
                    # Create an inference profile ARN using the model ID
                    # Format: arn:aws:bedrock:[region]:[account-id]:inference-profile/[profile-name]
                    # For testing, we'll use a placeholder inference profile name
                    inference_profile = f"inference-profile-{model.model_arn.split(':')[-1]}"
                    
                    # Try again with the inference profile
                    response = bedrock_client.invoke_model(
                        modelId=inference_profile,
                        body=json.dumps(request_body)
                    )
                    response_body = json.loads(response.get('body').read())
                else:
                    # Re-raise the original error if we can't handle it
                    raise invoke_error
            else:
                # Re-raise the original error for other types of errors
                raise invoke_error
        
        # Handle different response formats
        if "anthropic" in model.model_arn.lower():
            assistant_response = response_body.get('content')[0].get('text')
        else:
            # Generic handling for other models
            assistant_response = response_body.get('generation', response_body.get('output', response_body.get('text', str(response_body))))
        
        # Save assistant response
        assistant_message = Message(
            chat_session_id=chat_id,
            role='assistant',
            content=assistant_response
        )
        db.session.add(assistant_message)
        db.session.commit()
        
        return jsonify({
            'response': assistant_response,
            'chat_id': chat_id
        })
        
    except Exception as e:
        logging.error(f"Error calling Bedrock: {str(e)}", exc_info=True)
        error_message = str(e)
        
        # Show a more helpful error message for inference profile errors
        if "inference profile" in error_message.lower():
            error_message = "This model (Claude Opus 4) requires an inference profile. Please create an inference profile in the AWS Bedrock console and use the complete inference profile ARN instead of the model ID. Format should be: arn:aws:bedrock:[region]:[account-id]:inference-profile/[profile-name]"
        
        return jsonify({'error': error_message}), 500

@app.route('/models', methods=['GET'])
@login_required
def list_models():
    models = Model.query.all()
    return render_template('models.html', models=models)

@app.route('/models/add', methods=['POST'])
@login_required
def add_model():
    name = request.form.get('name')
    model_arn = request.form.get('model_arn')
    is_default = request.form.get('is_default') == 'on'
    
    if not name or not model_arn:
        flash('Name and Model ARN are required', 'error')
        return redirect(url_for('list_models'))
        
    # Add a warning if adding Claude Opus 4 without an inference profile
    if "claude-opus-4" in model_arn.lower() and "inference-profile" not in model_arn.lower():
        flash('Warning: Claude Opus 4 requires an inference profile. Please use the complete inference profile ARN instead of just the model ID.', 'warning')
    
    # If this model is set as default, unset any existing default
    if is_default:
        Model.query.filter_by(is_default=True).update({'is_default': False})
    
    model = Model(name=name, model_arn=model_arn, is_default=is_default)
    db.session.add(model)
    db.session.commit()
    
    flash(f'Model {name} added successfully', 'success')
    return redirect(url_for('list_models'))

@app.route('/models/<int:model_id>/delete', methods=['POST'])
@login_required
def delete_model(model_id):
    model = Model.query.get(model_id)
    if not model:
        flash('Model not found', 'error')
        return redirect(url_for('list_models'))
    
    # Don't allow deleting the last model
    if Model.query.count() <= 1:
        flash('Cannot delete the last model', 'error')
        return redirect(url_for('list_models'))
    
    # If deleting the default model, set another one as default
    if model.is_default:
        other_model = Model.query.filter(Model.id != model_id).first()
        if other_model:
            other_model.is_default = True
    
    db.session.delete(model)
    db.session.commit()
    
    flash(f'Model {model.name} deleted', 'info')
    return redirect(url_for('list_models'))

@app.route('/models/<int:model_id>/set_default', methods=['POST'])
@login_required
def set_default_model(model_id):
    # Unset current default
    Model.query.filter_by(is_default=True).update({'is_default': False})
    
    # Set new default
    model = Model.query.get(model_id)
    if not model:
        flash('Model not found', 'error')
        return redirect(url_for('list_models'))
        
    model.is_default = True
    db.session.commit()
    
    flash(f'{model.name} set as default model', 'success')
    return redirect(url_for('list_models'))

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5004))
    app.run(host='0.0.0.0', port=port)