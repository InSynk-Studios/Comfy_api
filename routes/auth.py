import os
from flask import Blueprint, request, jsonify
from flask_bcrypt import Bcrypt
from pymongo import MongoClient
import jwt
from dotenv import load_dotenv
from datetime import datetime, timedelta

auth = Blueprint('auth', __name__)
load_dotenv()

bcrypt = Bcrypt()
password = os.getenv('MONGO_PASSWORD')
client = MongoClient(f"mongodb+srv://hom:{password}@cluster0.lq59o75.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")

db = client['hom'] 
accounts = db['accounts']

@auth.route('/api/auth/create', methods=['POST'])
def createUser():
  print(accounts)
  email = request.json.get('email')
  password = request.json.get('password')

  if not email or not password:
    return jsonify({"error": "Email and password required"}), 400

  hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

  user = {
    'email': email,
    'password': hashed_password
  }

  accounts.insert_one(user)

  return jsonify({"success": "User created successfully"}), 200

@auth.route('/api/auth/login', methods=['POST'])
def login():
  email = request.json.get('email')
  password = request.json.get('password')

  if not email or not password:
    return jsonify({"error": "Email and password required"}), 400

  user = accounts.find_one({'email': email})

  if not user:
    return jsonify({"error": "Invalid email or password"}), 401

  if bcrypt.check_password_hash(user['password'], password):
    payload = {
            'exp': datetime.utcnow() + timedelta(days=1),
            'iat': datetime.utcnow(),
            'sub': user['_id']
        }
    token = jwt.encode(payload, 'secretkey', algorithm='HS256')

    return jsonify({"token": token.decode('UTF-8')}), 200
  else:
    return jsonify({"error": "Invalid email or password"}), 401