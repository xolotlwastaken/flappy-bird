from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from authlib.integrations.flask_client import OAuth
from dotenv import load_dotenv
import os
import boto3
from botocore.exceptions import ClientError
import secrets  # Import the secrets module from the standard library
import logging

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('SQLALCHEMY_DATABASE_URI')
db = SQLAlchemy(app)

# Configure logging
logging.basicConfig(level=logging.DEBUG)

oauth = OAuth(app)
oauth.register(
    name='oidc',
    client_id=os.getenv('APP_CLIENT_ID'),
    client_secret=os.getenv('APP_CLIENT_SECRET'),
    server_metadata_url=f"https://cognito-idp.{os.getenv('AWS_REGION')}.amazonaws.com/{os.getenv('USER_POOL_ID')}/.well-known/openid-configuration",
    client_kwargs={'scope': 'email openid phone profile'}
)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    highest_score = db.Column(db.Integer, default=0)

@app.route("/")
def index():
    if 'username' not in session:
        return redirect(url_for('login'))
    return render_template("index.html")

@app.route("/login")
def login():
    nonce = secrets.token_urlsafe()
    session['nonce'] = nonce
    redirect_uri = url_for('auth', _external=True)
    return oauth.oidc.authorize_redirect(redirect_uri, nonce=nonce)

@app.route("/auth")
def auth():
    token = oauth.oidc.authorize_access_token()
    nonce = session.pop('nonce', None)
    user_info = oauth.oidc.parse_id_token(token, nonce=nonce)
    session['username'] = user_info['email']
    
    # Check if the user exists in the local database
    user = User.query.filter_by(email=user_info['email']).first()
    if not user:
        # Create a new user in the local database
        new_user = User(username=user_info['preferred_username'], email=user_info['email'], password='')  # Password can be empty or set to a default value
        db.session.add(new_user)
        db.session.commit()
        logging.debug(f"User {user_info['preferred_username']} added to the local database.")
    
    return redirect(url_for('index'))

@app.route("/logout")
def logout():
    session.pop('username', None)
    return redirect(url_for("index"))

cognito_client = boto3.client('cognito-idp', region_name=os.getenv('AWS_REGION'))

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        email = request.form["email"]
        password = request.form["password"]
        try:
            response = cognito_client.sign_up(
                ClientId=os.getenv('APP_CLIENT_ID'),
                Username=username,
                Password=password,
                UserAttributes=[
                    {'Name': 'email', 'Value': email},
                ],
            )
            logging.debug(f"User {username} registered successfully with Cognito.")
            # Save the user in the local database
            new_user = User(username=username, email=email, password=password)
            db.session.add(new_user)
            db.session.commit()
            return redirect(url_for("login"))
        except ClientError as e:
            logging.error(f"Error registering user: {e}")
            return str(e)
    return render_template("register.html")

@app.route("/save_score", methods=["POST"])
def save_score():
    if 'username' not in session:
        return {"error": "User not logged in"}, 401
    data = request.get_json()
    score = data.get('score')
    user = User.query.filter_by(username=session['username']).first()
    if user:
        if score > user.highest_score:
            user.highest_score = score
            db.session.commit()
            logging.debug(f"User {user.username}'s score updated to {score}.")
        return {"message": "Score saved successfully"}
    return {"error": "User not found"}, 404

@app.route("/leaderboard")
def leaderboard():
    # Query the top users by highest score
    top_users = User.query.order_by(User.highest_score.desc()).limit(10).all()
    return render_template("leaderboard.html", users=top_users)

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True, host='localhost')