import os
import unittest
import tempfile
from app import app, db, User, Model

class AppTestCase(unittest.TestCase):
    def setUp(self):
        self.db_fd, app.config['DATABASE'] = tempfile.mkstemp()
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + app.config['DATABASE']
        app.config['WTF_CSRF_ENABLED'] = False
        self.client = app.test_client()
        with app.app_context():
            db.create_all()
            # Create test user
            test_user = User(username='testuser')
            test_user.set_password('testpassword')
            db.session.add(test_user)
            # Create test model
            test_model = Model(
                name='Test Model',
                model_arn='anthropic.claude-3-5-sonnet-20240620-v1:0',
                is_default=True
            )
            db.session.add(test_model)
            db.session.commit()

    def tearDown(self):
        os.close(self.db_fd)
        os.unlink(app.config['DATABASE'])

    def test_login_page(self):
        """Test that login page loads correctly"""
        response = self.client.get('/login')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Login', response.data)

    def test_login_success(self):
        """Test successful login"""
        response = self.client.post('/login', data={
            'username': 'testuser',
            'password': 'testpassword'
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'New Chat', response.data)

    def test_login_failure(self):
        """Test failed login"""
        response = self.client.post('/login', data={
            'username': 'testuser',
            'password': 'wrongpassword'
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Invalid username or password', response.data)

    def test_protected_routes(self):
        """Test that protected routes require login"""
        routes = ['/chat', '/models', '/chat/new']
        for route in routes:
            response = self.client.get(route)
            self.assertEqual(response.status_code, 302)  # Redirect to login
            self.assertIn('/login', response.location)

    def test_models_page(self):
        """Test models page after login"""
        # Login first
        self.client.post('/login', data={
            'username': 'testuser',
            'password': 'testpassword'
        })
        
        # Access models page
        response = self.client.get('/models')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Available Models', response.data)
        self.assertIn(b'Test Model', response.data)

if __name__ == '__main__':
    unittest.main()