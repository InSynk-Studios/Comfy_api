from flask import Blueprint

app = Blueprint('app', __name__)

@app.route('/api/v2/prompt', methods=['GET'])
def prompt():
    return "Hello, welcome to the server!"