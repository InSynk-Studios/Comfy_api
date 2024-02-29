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
import mimetypes
from v2.routes.app import app as app_v2
from routes.scrape import scrape
from dotenv import load_dotenv
import boto3

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
register_heif_opener()

@app.route('/', methods=['GET'])
def hello():
    return "Hello, welcome to the server!"

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

        file_extension = os.path.splitext(filename)[1]
        print(file_extension)

        if file_extension.lower() == '.png':
            image.save(save_path, format='PNG')
        else:
            # rgb_im = image.convert('RGB')
            # Save the image in the desired format
            new_filename = os.path.splitext(filename)[0] + '.png'
            save_path = os.path.join('../ComfyUI/input', new_filename)
            image.save(save_path, format='PNG')
            
        # file.save(save_path)
        return jsonify({"success": "Image successfully uploaded and saved"}), 200
    else:
        return jsonify({"error": "Allowed image types are - png, jpg, jpeg, webp"}), 400

DEFAULT_EXTERNAL_API_URL = 'https://zypr91htxji6wc-3000.proxy.runpod.net'
@app.route('/prompt', methods=['POST'])
def call_external_api():
    external_api_url = request.args.get('url', DEFAULT_EXTERNAL_API_URL)

    incoming_data = request.json
    print(incoming_data)
    external_api_url = f"{external_api_url}/prompt"

    try:
        response = requests.post(external_api_url, json=incoming_data)

        return jsonify(response.json()), response.status_code
    except requests.RequestException as e:
        print(e)
        return jsonify({"error": str(e)}), 500

def allowed_file(filename):
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)