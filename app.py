import threading
import time
import zipfile
from flask import Flask, send_file, request, jsonify
from werkzeug.utils import secure_filename
from flask_cors import CORS
from pillow_heif import register_heif_opener
import pillow_avif
import os
from PIL import Image
import glob
import requests
from v2.routes.app import app as app_v2
from routes.scrape import scrape
from routes.auth import auth
from dotenv import load_dotenv
import boto3
from flask_socketio import SocketIO, emit
import jwt

DEFAULT_EXTERNAL_API_URL = os.getenv('EXTERNAL_API_URL')
SELF_URL = os.getenv('SELF_URL')

load_dotenv()
s3_client = boto3.client(
    's3',
    aws_access_key_id=os.getenv('AWS_S3_ACCESS_KEY_ID'),
    aws_secret_access_key=os.getenv('AWS_S3_SECRET_ACCESS_KEY'),
    region_name=os.getenv('AWS_S3_REGION')
)

app = Flask(__name__)
CORS(app)
app.register_blueprint(app_v2)
app.register_blueprint(scrape)
app.register_blueprint(auth)
register_heif_opener()

socketio = SocketIO(app, cors_allowed_origins="*")
clients = {}
generations = {}

@app.route('/', methods=['GET'])
def hello():
    return "Hello, welcome to the server!"

@socketio.on('connect')
def connect():
    clients[request.sid] = time.time()
    print('Client connected: ', request.sid)

@socketio.on('disconnect')
def disconnect():
    sid = request.sid
    print(f"Client {sid} has been disconnected due to inactivity")
    url = f"{DEFAULT_EXTERNAL_API_URL}/queue"
    response = requests.get(url)
    queue_data = response.json()
    running_executions = queue_data['queue_running']                
    pending_executions = queue_data['queue_pending']                
    execution_ids = generations[sid] 
    
    for id in execution_ids:
        executions = {'pending': pending_executions, 'running': running_executions}
        thread = threading.Thread(target=delete_and_interrupt, args=(executions, id))
        thread.start()
    
    clients.pop(sid, None)
    print('Client disconnected: ', sid)

@socketio.on('heartbeat')
def handle_heartbeat(message):
    clients[request.sid] = time.time()
    # print('Heartbeat received: ', message)
    # print('Clients: ', clients)
    emit('heartbeat_response', {'data': 'Heartbeat received'})

def delete_and_interrupt(executions, id):
    try:
        for exec in executions['pending']:
            if exec[1] == id:
                response = requests.post(f"{SELF_URL}/delete-queue-item", json={"delete": [id]})
                response.raise_for_status()
        for exec in executions['running']:
            if exec[1] == id:
                response = requests.post(f"${SELF_URL}/interrupt", json={"execution_id": exec[0]})
                response.raise_for_status()
    except requests.exceptions.HTTPError:
        print(f'Deleted/Interrupted: {id}')
    except Exception as err:
        print(f'Other error occurred: {err}')

# def check_heartbeats():
#     print('Checking heartbeats...')
#     while True:
#         for sid, last_heartbeat in list(clients.items()):
#             if time.time() - last_heartbeat > 20:
#                 # clients.pop(sid, None)
#                 print(f"Client {sid} has been disconnected due to inactivity")
#                 url = f"{DEFAULT_EXTERNAL_API_URL}/queue"
#                 response = requests.get(url)
#                 queue_data = response.json()
#                 running_executions = queue_data['queue_running']                
#                 pending_executions = queue_data['queue_pending']                
#                 execution_ids = generations[sid] 
#                 print(f"Execution IDs: {execution_ids}")
                
#                 for id in execution_ids:
#                     for exec in pending_executions:
#                         if exec[1] == id:
#                             requests.post(f"https://genai.houseofmodels.ai/delete-queue-item", json={"delete": [id]})
#                     for exec in running_executions:
#                         if exec[1] == id:
#                             requests.post(f"https://genai.houseofmodels.ai/interrupt", json={"execution_id": exec[0]})
                
#                 clients.pop(sid, None)
#         socketio.sleep(10)

def emit_queue_length():
    while True:
        url = f"{DEFAULT_EXTERNAL_API_URL}/queue"
        response = requests.get(url)
        queue_data = response.json()
        running_executions = queue_data['queue_running']                
        pending_executions = queue_data['queue_pending']                
        socketio.emit('queue_length', {'count': len(running_executions) + len(pending_executions)})
        socketio.sleep(5)

socketio.start_background_task(emit_queue_length)

@app.route('/latest', methods=['GET'])
def get_latest_files():
  image_dir = '../ComfyUI/output/'
  text_dir = '../ComfyUI/output/'
  
  masked = request.args.get('masked', 'false').lower() == 'true'

  # Get the latest image file
  image_files = glob.glob(os.path.join(image_dir, '*.jpg'))
  image_files += glob.glob(os.path.join(image_dir, '*.png'))
  image_files += glob.glob(os.path.join(image_dir, '*.webp'))  

  if masked:
    image_files = [f for f in image_files if 'Masked' in os.path.basename(f)]
  else:
    image_files = [f for f in image_files if 'Final' in os.path.basename(f)]

  latest_image = max(image_files, key=os.path.getctime)

  # Get the latest text file
  text_files = glob.glob(os.path.join(text_dir, '*.txt'))
  latest_text = max(text_files, key=os.path.getctime)

  zip_filename = 'latest_files.zip'
  with zipfile.ZipFile(zip_filename, 'w') as zipf:
    zipf.write(latest_image, os.path.basename(latest_image))
    zipf.write(latest_text, os.path.basename(latest_text))

  return send_file(zip_filename, as_attachment=True)

@app.route('/file', methods=['GET'])
def get_file_by_fileName():
    dir = os.path.join('/home/azureuser/workspace', 'ComfyUI', 'output')
    specific_filename = request.args.get('filename')

    if specific_filename:
        file_paths = glob.glob(os.path.join(dir, '*' + specific_filename + '*'))
        if file_paths:
            return send_file(file_paths[0], as_attachment=True)
        else:
            return "File not found.", 204
    else:
        return "File not found.", 204

@app.route('/file-input', methods=['GET'])
def get_input_file_by_fileName():
    dir = os.path.join('/home/azureuser/workspace', 'ComfyUI', 'input')
    specific_filename = request.args.get('filename')

    if specific_filename:
        file_paths = glob.glob(os.path.join(dir, '*' + specific_filename + '*'))
        if file_paths:
            return send_file(file_paths[0], as_attachment=True)
        else:
            return "File not found.", 204
    else:
        return "File not found.", 204

@app.route('/file/v2', methods=['GET'])
def get_file_by_fileName_v2():
    dir = os.path.join('/home/azureuser/workspace', 'ComfyUI', 'output')
    specific_filename = request.args.get('filename')

    if specific_filename:
        file_paths = glob.glob(os.path.join(dir, '*' + specific_filename + '*'))
        if file_paths:
            s3_file_name = os.path.basename(file_paths[0])
            s3_client.upload_file(file_paths[0], os.getenv('AWS_S3_BUCKET_NAME'), s3_file_name)
            downloadURL = f"https://{os.getenv('AWS_S3_BUCKET_NAME')}.s3.{os.getenv('AWS_S3_REGION')}.amazonaws.com/{s3_file_name}"   
            return {"downloadURL": downloadURL}, 200
        else:
            return "File not found.", 204
    else:
        return "File not found.", 204

@app.route('/latest-tags', methods=['GET'])
def get_latest_tags():
  text_dir = '../ComfyUI/output/'

  # Get the latest text file
  text_files = glob.glob(os.path.join(text_dir, '*.txt'))
  latest_text = max(text_files, key=os.path.getctime)

  zip_filename = 'latest_files.zip'
  with zipfile.ZipFile(zip_filename, 'w') as zipf:
    zipf.write(latest_text, os.path.basename(latest_text))

  return send_file(zip_filename, as_attachment=True)

@app.route('/latest-media', methods=['GET'])
def get_latest_media():
  type = request.args.get('type')
  media_dir = '../ComfyUI/output/'

  # Get the latest text file
  image_files = glob.glob(os.path.join(media_dir, '*.jpg'))
  image_files += glob.glob(os.path.join(media_dir, '*.png'))
  image_files += glob.glob(os.path.join(media_dir, '*.webp'))   
  latest_image = max(image_files, key=os.path.getctime)

    
  video_files = glob.glob(os.path.join(media_dir, '*.mp4'))
  latest_video = max(video_files, key=os.path.getctime)

  zip_filename = 'latest_files.zip'
  with zipfile.ZipFile(zip_filename, 'w') as zipf:
    if type == "video" and latest_video:
        zipf.write(latest_video, os.path.basename(latest_video))
    else:
        zipf.write(latest_image, os.path.basename(latest_image))

  return send_file(zip_filename, as_attachment=True) if (latest_video or latest_image) else "No media files found"

@app.route('/upload-image', methods=['POST'])
def upload_image():
    if 'image' not in request.files:
        return jsonify({"error": "No image part in the request"}), 400

    file = request.files['image']

    if file.filename == '':
        return jsonify({"error": "No image selected for uploading"}), 400

    if file:
        filename = secure_filename(file.filename)
        save_path = os.path.join('../ComfyUI/input', filename)
        image = Image.open(file)
        
        file_ext = os.path.splitext(filename)[1]
        if file_ext.lower() == '.png':
            # Save the image as PNG
            image.save(save_path, format='PNG')
        else:
            rgb_im = image.convert('RGB')
            # Save the image in the desired format
            new_filename = os.path.splitext(filename)[0] + '.jpg'
            save_path = os.path.join('../ComfyUI/input', new_filename)
            rgb_im.save(save_path, format='JPEG')
        
        return jsonify({"success": "Image successfully uploaded and saved"}), 200
    else:
        return jsonify({"error": "Allowed image types are - png, jpg, jpeg, webp"}), 400

@app.route('/prompt', methods=['POST'])
def call_external_api():
    # token = request.headers.get('Authorization')
    # if not token:
    #     return jsonify({"error": "Unauthorized"}), 401
    
    # try:
    #     data = jwt.decode(token, 'secretkey', algorithms=['HS256'])
    # except jwt.ExpiredSignatureError:
    #     return jsonify({"error": "Token is expired"}), 401
    # except jwt.InvalidTokenError:
    #     return jsonify({"error": "Token is invalid"}), 401

    external_api_url = DEFAULT_EXTERNAL_API_URL
    client_id = request.args.get('clientId')

    incoming_data = request.json
    external_api_url = f"{external_api_url}/prompt"

    try:
        response = requests.post(external_api_url, json=incoming_data)
        if client_id not in generations:
            generations[client_id] = []

        generations[client_id].append(response.json().get('prompt_id'))
            
        return jsonify(response.json()), response.status_code
    except requests.RequestException as e:
        print(e)
        return jsonify({"error": str(e)}), 500
    
@app.route('/get-queue', methods=['GET'])
def get_queue():
    external_api_url = DEFAULT_EXTERNAL_API_URL
    external_api_url = f"{external_api_url}/queue"

    try:
        response = requests.get(external_api_url)

        return jsonify(response.json()), response.status_code
    except requests.RequestException as e:
        print(e)
        return jsonify({"error": str(e)}), 500
    
@app.route('/delete-queue-item', methods=['POST'])
def delete_queue_item():
    external_api_url = DEFAULT_EXTERNAL_API_URL
    incoming_data = request.json
    
    external_api_url = f"{external_api_url}/queue"
    try:
        response = requests.post(external_api_url, json=incoming_data)

        return jsonify(response.json()), response.status_code
    except requests.RequestException as e:
        print(e)
        return jsonify({"error": str(e)}), 500
    
# Stops currently running execution
@app.route('/interrupt', methods=['POST'])
def interrupt_execution():
    external_api_url = DEFAULT_EXTERNAL_API_URL

    external_api_url = f"{external_api_url}/interrupt"

    try:
        response = requests.post(external_api_url)

        return jsonify(response.json()), response.status_code
    except requests.RequestException as e:
        print(e)
        return jsonify({"error": str(e)}), 500

def allowed_file(filename):
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


if __name__ == '__main__':
    socketio.run(app)
    app.run(host='0.0.0.0', port=5000, debug=False)