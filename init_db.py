#!/usr/bin/env python3
"""
Database initialization script for AWS Bedrock Chat application.
This script can be run separately to initialize the database before starting the application.
"""

import os
import sys
from app import app, db, User, Model, DEFAULT_MODEL, DEFAULT_MODEL_NAME
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def init_database():
    """Initialize the database with tables and default data."""
    print("Initializing database...")
    
    try:
        # Create all tables
        db.create_all()
        print("Tables created successfully.")
        
        # Create admin user if it doesn't exist
        admin_username = os.environ.get('ADMIN_USERNAME', 'admin')
        admin_password = os.environ.get('ADMIN_PASSWORD')
        
        if not admin_password:
            print("Warning: ADMIN_PASSWORD environment variable not set.")
            if input("Do you want to continue with default password 'password'? (y/n): ").lower() == 'y':
                admin_password = 'password'
            else:
                print("Aborting admin user creation.")
                admin_password = None
        
        if admin_password:
            admin = User.query.filter_by(username=admin_username).first()
            if not admin:
                admin = User(username=admin_username)
                admin.set_password(admin_password)
                db.session.add(admin)
                db.session.commit()
                print(f"Admin user '{admin_username}' created successfully.")
            else:
                print(f"Admin user '{admin_username}' already exists.")
        
        # Add default model if no models exist
        if Model.query.count() == 0:
            default_model = Model(
                name=DEFAULT_MODEL_NAME,
                model_arn=DEFAULT_MODEL,
                is_default=True
            )
            db.session.add(default_model)
            db.session.commit()
            print(f"Default model '{DEFAULT_MODEL_NAME}' created successfully.")
        else:
            print("Models already exist in the database.")
        
        print("Database initialization completed successfully.")
        return True
        
    except Exception as e:
        print(f"Error initializing database: {str(e)}")
        db.session.rollback()
        return False

if __name__ == "__main__":
    with app.app_context():
        success = init_database()
        sys.exit(0 if success else 1)