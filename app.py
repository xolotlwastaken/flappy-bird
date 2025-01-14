# filepath: /C:/Users/xolot/Desktop/SMU/ACCAD/assessments/ACCAD6/flappy-bird/app.py
from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv
import os

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('SQLALCHEMY_DATABASE_URI')
db = SQLAlchemy(app)

# AWS Cognito configuration
cognito_client = boto3.client('cognito-idp', region_name=os.getenv('AWS_REGION'))
USER_POOL_ID = os.getenv('USER_POOL_ID')
APP_CLIENT_ID = os.getenv('APP_CLIENT_ID')

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    highest_score = db.Column(db.Integer, default=0)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        email = request.form["email"]
        password = request.form["password"]
        try:
            response = cognito_client.sign_up(
                ClientId=APP_CLIENT_ID,
                Username=username,
                Password=password,
                UserAttributes=[
                    {'Name': 'email', 'Value': email},
                ],
            )
            new_user = User(username=username, email=email, password=password)
            db.session.add(new_user)
            db.session.commit()
            return redirect(url_for("login"))
        except ClientError as e:
            return str(e)
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        try:
            response = cognito_client.initiate_auth(
                ClientId=APP_CLIENT_ID,
                AuthFlow='USER_PASSWORD_AUTH',
                AuthParameters={
                    'USERNAME': username,
                    'PASSWORD': password,
                },
            )
            session['username'] = username
            return redirect(url_for("index"))
        except ClientError as e:
            return str(e)
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.pop('username', None)
    return redirect(url_for("index"))

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
        return {"message": "Score saved successfully"}
    return {"error": "User not found"}, 404

if __name__ == "__main__":
    db.create_all()
    app.run(debug=True)