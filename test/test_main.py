import pytest
from app import app, db
from app.models import User
from flask import session

@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:///:memory:"
    with app.test_client() as client:
        with app.app_context():
            db.create_all()
        yield client
        with app.app_context():
            db.session.remove()
            db.drop_all()

def test_login(client):
    # Test the login page loads
    response = client.get('/login')
    assert response.status_code == 200

    # Simulate OAuth login
    with client.session_transaction() as sess:
        sess['username'] = 'testuser@example.com'
    
    response = client.get('/')
    assert response.status_code == 200
    assert b"Welcome" in response.data

def test_register(client):
    # Test the registration form loads
    response = client.get('/register')
    assert response.status_code == 200

    # Test user registration
    response = client.post('/register', data={
        'username': 'testuser',
        'email': 'testuser@example.com',
        'password': 'Password123'
    }, follow_redirects=True)

    assert response.status_code == 200
    assert User.query.filter_by(username='testuser').first() is not None

def test_save_score(client):
    # Add a test user
    user = User(username='testuser', email='testuser@example.com', password='Password123', highest_score=0)
    db.session.add(user)
    db.session.commit()

    # Simulate login
    with client.session_transaction() as sess:
        sess['username'] = 'testuser'

    # Save a new score
    response = client.post('/save_score', json={'score': 50})
    assert response.status_code == 200
    assert response.get_json()['message'] == "Score saved successfully"

    # Verify the score was updated in the database
    user = User.query.filter_by(username='testuser').first()
    assert user.highest_score == 50

def test_leaderboard(client):
    # Add test users
    user1 = User(username='user1', email='user1@example.com', password='Password123', highest_score=100)
    user2 = User(username='user2', email='user2@example.com', password='Password123', highest_score=200)
    db.session.add_all([user1, user2])
    db.session.commit()

    # Access the leaderboard
    response = client.get('/leaderboard')
    assert response.status_code == 200
    assert b"user2" in response.data  # user2 has the highest score
    assert b"user1" in response.data
