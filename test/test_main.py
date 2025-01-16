import pytest
from flask import session
import importlib
import sys
import os
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# Add the parent directory to the sys.path to ensure the app module can be found
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import and reload the app module
app_module = importlib.import_module('app')
importlib.reload(app_module)

# Access app and models dynamically
app = app_module.app
db = app_module.db
User = app_module.Users

@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:///:memory:"  # Use in-memory SQLite for testing
    with app.test_client() as client:
        with app.app_context():
            db.create_all()
        yield client

def test_index(client):
    logging.debug("Starting test_index")
    response = client.get('/')
    assert response.status_code == 302  # Redirect to login if not logged in
    logging.debug("Finished test_index")

def test_login(client):
    logging.debug("Starting test_login")
    response = client.get('/login')
    assert response.status_code == 302  # Redirect to OIDC provider
    logging.debug("Finished test_login")


def test_save_score(client):
    logging.debug("Starting test_save_score")
    with app.app_context():
        user = User(username='testuser', email='testuser@example.com', password='Password123', highest_score=0)
        db.session.add(user)
        db.session.commit()

    with client.session_transaction() as sess:
        sess['username'] = 'testuser'

    response = client.post('/save_score', json={'score': 50})
    assert response.status_code == 200
    assert response.get_json()['message'] == "Score saved successfully"

    with app.app_context():
        user = User.query.filter_by(username='testuser').first()
        assert user.highest_score == 50

        db.session.delete(user)
        db.session.commit()

    logging.debug("Finished test_save_score")

def test_leaderboard(client):
    logging.debug("Starting test_leaderboard")
    with app.app_context():
        user1 = User(username='user1', email='user1@example.com', password='Password123', highest_score=100)
        user2 = User(username='user2', email='user2@example.com', password='Password123', highest_score=200)
        db.session.add_all([user1, user2])
        db.session.commit()

    response = client.get('/leaderboard')
    assert response.status_code == 200
    assert b"user2" in response.data
    assert b"user1" in response.data

    with app.app_context():
        db.session.delete(user1)
        db.session.delete(user2)
        db.session.commit()
        
    logging.debug("Finished test_leaderboard")

def test_delete_user(client):
    logging.debug("Starting test_delete_user")
    with app.app_context():
        user = User(username='testuser', email='testuser@example.com', password='Password123')
        db.session.add(user)
        db.session.commit()

        user = User.query.filter_by(username='testuser').first()
        assert user is not None

        db.session.delete(user)
        db.session.commit()

        user = User.query.filter_by(username='testuser').first()
        assert user is None
    logging.debug("Finished test_delete_user")