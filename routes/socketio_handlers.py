from app import socketio, clients, generations, DEFAULT_EXTERNAL_API_URL, SELF_URL
from flask import request
import time
import requests
import threading
import websocket
import json
from flask_socketio import emit

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
    emit('heartbeat_response', {'data': 'Heartbeat received'})          
            
def check_for_generations_ws():
    while True:
        ws = websocket.WebSocket()
        ws.connect("ws://4.227.147.49:8188/ws")
        for client in clients:
            if client not in generations or not generations[client]:
                continue
            print('Checking for generations...')
            print(generations)
            for generation in generations[client]:
                out = ws.recv()
                print(out)
                print(isinstance(out, str))
                if isinstance(out, str):
                    message = json.loads(out)
                    print(message)
                    if message['type'] == 'executing':
                        data = message['data']
                        print("================")
                        print(data)
                        print(generation)
                        print("================")
                        if data['node'] is None and data['prompt_id'] == generation:
                            emit('generations', {'data': generation})
                            generations.pop(generation, None)
        socketio.sleep(5)

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

def emit_queue_length():
    while True:
        try:
            if not clients:
                socketio.sleep(5)
                continue
            url = f"{DEFAULT_EXTERNAL_API_URL}/queue"
            response = requests.get(url)
            queue_data = response.json()
            running_executions = queue_data['queue_running']                
            pending_executions = queue_data['queue_pending']      
            queueSize = len(running_executions) + len(pending_executions)          
            print('Queue Size: ', queueSize)
            socketio.emit('queue_length', {'count': queueSize})
            socketio.sleep(3)
        except Exception as e:
            print(f"Error in emit_queue_length: {e}")
            socketio.sleep(5)

socketio.start_background_task(emit_queue_length)
