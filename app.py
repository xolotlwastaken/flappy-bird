from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from authlib.integrations.flask_client import OAuth
from dotenv import load_dotenv
import os
import boto3
from botocore.exceptions import ClientError
import secrets  # Import the secrets module from the standard library
import logging
import json

# Load environment variables from .env file
load_dotenv()

def get_secret():
    secret_name = "flappybird-secrets"
    region_name = "ap-southeast-1"

    # Create a Secrets Manager client
    session = boto3.session.Session()
    client = session.client(
        service_name='secretsmanager',
        region_name=region_name
    )

    try:
        get_secret_value_response = client.get_secret_value(
            SecretId=secret_name
        )
    except ClientError as e:
        raise e

    secret = get_secret_value_response['SecretString']
    return json.loads(secret)

secrets_all = get_secret()

app = Flask(__name__)
app.secret_key = secrets_all['SECRET_KEY']
app.config['SQLALCHEMY_DATABASE_URI'] = secrets_all['SQLALCHEMY_DATABASE_URI']
db = SQLAlchemy(app)

# Configure logging
logging.basicConfig(level=logging.DEBUG)

oauth = OAuth(app)
oauth.register(
    name='oidc',
    client_id=secrets_all['APP_CLIENT_ID'],
    client_secret=secrets_all['APP_CLIENT_SECRET'],
    server_metadata_url=f"https://cognito-idp.{secrets_all['AWS_REGION']}.amazonaws.com/{secrets_all['USER_POOL_ID']}/.well-known/openid-configuration",
    client_kwargs={'scope': 'email openid phone profile'}
)

class Users(db.Model):
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
    redirect_uri = url_for('https://p3pusciccd.ap-southeast-1.awsapprunner.com/auth', _external=True)
    return oauth.oidc.authorize_redirect(redirect_uri, nonce=nonce)

@app.route("/auth")
def auth():
    token = oauth.oidc.authorize_access_token()
    nonce = session.pop('nonce', None)
    user_info = oauth.oidc.parse_id_token(token, nonce=nonce)
    session['username'] = user_info['email']
    
    # Check if the user exists in the local database
    user = Users.query.filter_by(email=user_info['email']).first()
    if not user:
        # Use email as username if preferred_username is not available
        username = user_info.get('preferred_username', user_info['email'])
        # Create a new user in the local database
        new_user = Users(username=username, email=user_info['email'], password='')  # Password can be empty or set to a default value
        db.session.add(new_user)
        db.session.commit()
        logging.debug(f"User {username} added to the local database.")
    
    return redirect(url_for('index'))

@app.route("/logout")
def logout():
    session.pop('username', None)
    return redirect(url_for("index"))

cognito_client = boto3.client('cognito-idp', region_name=secrets_all['AWS_REGION'])

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        email = request.form["email"]
        password = request.form["password"]
        try:
            response = cognito_client.sign_up(
                ClientId=secrets_all['APP_CLIENT_ID'],
                Username=username,
                Password=password,
                UserAttributes=[
                    {'Name': 'email', 'Value': email},
                ],
            )
            logging.debug(f"User {username} registered successfully with Cognito.")
            # Save the user in the local database
            new_user = Users(username=username, email=email, password=password)
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
    user = Users.query.filter_by(username=session['username']).first()
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
    top_users = Users.query.order_by(Users.highest_score.desc()).limit(10).all()
    return render_template("leaderboard.html", users=top_users)

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True, host='0.0.0.0', port=5000)