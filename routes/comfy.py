from flask import Blueprint, request, jsonify, send_file
from pydantic import ValidationError
from dotenv import load_dotenv
import jwt
import json
import random
import os
import requests
from dto.apparel_background_change_request import ApparelBackgroundChangeRequest
from dto.product_background_change_request import ProductBackgroundChangeRequest
from dto.description_generator_request import DescriptionGeneratorRequest
from dto.magic_fix_request import MagicFixRequest

load_dotenv()
comfy = Blueprint('comfy', __name__)

@comfy.route('/api/image-generation/apparel', methods=['POST'])
def apparelBackgroundChange():
    try:
        authenticate(request.headers.get('Authorization'))
        shouldUseLora = request.args.get('lora', False).lower() == 'true'
        client_id = request.args.get('clientId', None)
        request_data = ApparelBackgroundChangeRequest.parse_obj(request.json)
        
        if not request_data.seed:
            request_data.seed = random.randint(1, 1_500_000)
        
        workflow = None
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        if shouldUseLora:
            file_path = os.path.join(base_dir, "workflow", "apparel_background_change", "bg_change_with_background_lora.json")
        else:          
            file_path = os.path.join(base_dir, "workflow", "apparel_background_change", "bg_change_gaussian_blur.json")
            
        with open(file_path, "r") as f:
            workflow = json.load(f)        
        
        workflow["3"]["inputs"]["seed"] = request_data.seed
        workflow["70"]["inputs"]["seed"] = request_data.seed
        
        workflow["6"]["inputs"]["text"] = request_data.positivePrompt
        workflow["7"]["inputs"]["text"] = request_data.negativePrompt
        workflow["70"]["inputs"]["wildcard"] = request_data.faceDetailerPrompt
        
        if shouldUseLora:
            workflow["193"]["inputs"]["lora_name"] = request_data.backgroundLora.name
            workflow["193"]["inputs"]["strength_model"] = request_data.backgroundLora.strength_model
            workflow["193"]["inputs"]["strength_clip"] = request_data.backgroundLora.strength_clip
        
        workflow["128"]["inputs"]["image"] = request_data.inputMaskImagePath
        workflow["134"]["inputs"]["image"] = request_data.inputImagePath
        workflow["139"]["inputs"]["image"] = request_data.inputFocusImagePath
        
        workflow["115"]["inputs"]["amount"] = request_data.outputCount
        workflow["45"]["inputs"]["filename_prefix"] = request_data.outputFileName
        
        data = {
            "prompt": workflow,
            "client_id": client_id
        }
        
        try:
            comfy_url = f'{os.getenv("COMFY_URL")}/prompt'
            response = requests.post(comfy_url, json=data)
            
            return jsonify(response.json()), response.status_code
        except requests.RequestException as e:
            return jsonify({"error": str(e)}), 400
        
    except Exception as e:
        return jsonify({"error": str(e)}), 400
  
@comfy.route('/api/image-generation/product', methods=['POST'])
def productBackgroundChange():
    try:
        authenticate(request.headers.get('Authorization'))
        client_id = request.args.get('clientId', None)
        request_data = ProductBackgroundChangeRequest.parse_obj(request.json)
        
        if not request_data.seed:
            request_data.seed = random.randint(1, 1_500_000)
        
        workflow = None
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        file_path = os.path.join(base_dir, "workflow", "product_background_change", "bg_change_product.json")
            
        with open(file_path, "r") as f:
            workflow = json.load(f)        
        
        workflow["41"]["inputs"]["seed"] = request_data.seed
        
        workflow["144"]["inputs"]["prompt"] = request_data.prompt
        workflow["121"]["inputs"]["weight"] = request_data.renderStrength
        
        workflow["94"]["inputs"]["image"] = request_data.inputProductImagePath
        workflow["124"]["inputs"]["image"] = request_data.backgroundRefImagePath
        workflow["131"]["inputs"]["image"] = request_data.inputFocusImagePath
        workflow["156"]["inputs"]["image"] = request_data.inputBlackAndWhiteImagePath
        
        workflow["106"]["inputs"]["filename_prefix"] = request_data.outputFileName
        
        data = {
            "prompt": workflow,
            "client_id": client_id
        }
        
        try:
            comfy_url = f'{os.getenv("COMFY_URL")}/prompt'
            response = requests.post(comfy_url, json=data)
            
            return jsonify(response.json()), response.status_code
        except requests.RequestException as e:
            return jsonify({"error": str(e)}), 400   
        
    except Exception as e:
        return jsonify({"error": str(e)}), 400  
  
@comfy.route('/api/text-generation/description', methods=['POST'])
def descriptionGeneration():
    try:
        authenticate(request.headers.get('Authorization'))
        target = request.args.get('target', None)
        request_data = DescriptionGeneratorRequest.parse_obj(request.json)
    
        workflow = None
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        if target == "product":
            file_path = os.path.join(base_dir, "workflow", "product_background_change", "generate_description.json")
        elif target == "apparel":
            file_path = os.path.join(base_dir, "workflow", "apparel_background_change", "generate_description.json")
        else:
            return jsonify({"error": "Invalid target"}), 400
            
        with open(file_path, "r") as f:
            workflow = json.load(f)        
        
        workflow["5"]["inputs"]["image"] = request_data.inputImagePath
        workflow["20"]["inputs"]["filename_prefix"] = request_data.outputFileName
        
        data = {
            "prompt": workflow,
            "front": True
        }
        
        try:
            comfy_url = f'{os.getenv("COMFY_URL")}/prompt'
            response = requests.post(comfy_url, json=data)
            
            return jsonify(response.json()), response.status_code
        except requests.RequestException as e:
            return jsonify({"error": str(e)}), 400
        
    except Exception as e:
        return jsonify({"error": str(e)}), 400
 
@comfy.route('/api/image-generation/magic-fix', methods=['POST'])
def magicFix():
    try:
        authenticate(request.headers.get('Authorization'))
        client_id = request.args.get('clientId', None)
        request_data = MagicFixRequest.parse_obj(request.json)

        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        file_path = os.path.join(base_dir, "workflow", "apparel_background_change", "magic_fix.json")
            
        with open(file_path, "r") as f:
            workflow = json.load(f)  
        
        workflow["2"]["inputs"]["image"] = request_data.inputImagePath
        workflow["7"]["inputs"]["image"] = request_data.inputMaskImagePath
        workflow["1"]["inputs"]["image"] = request_data.inputGeneratedImagePath
        workflow["11"]["inputs"]["filename_prefix"] = request_data.outputFileName
        
        data = {
            "prompt": workflow,
            "client_id": client_id,
            "front": True
        }
        
        try:
            comfy_url = f'{os.getenv("COMFY_URL")}/prompt'
            response = requests.post(comfy_url, json=data)
            
            return jsonify(response.json()), response.status_code
        except requests.RequestException as e:
            return jsonify({"error": str(e)}), 400
        
    except Exception as e:
        return jsonify({"error": str(e)}), 400


def authenticate(token):
    if not token:
        return jsonify({"error": "Unauthorized"}), 401
    
    try:
        data = jwt.decode(token, 'secretkey', algorithms=['HS256'])
    except jwt.ExpiredSignatureError:
        return jsonify({"error": "Token is expired"}), 401
    except jwt.InvalidTokenError:
        return jsonify({"error": "Token is invalid"}), 401

    return data