from flask import Flask, render_template, jsonify, request
import redis
import requests
from datetime import datetime
app = Flask(__name__)
r = redis.Redis(host='localhost', port=6379, db=0)
conversation_logs=[]
user_ID="haikuLover"
ia_Assistant_ID="AssistantAgent"

def log_to_redis(agent, message):
    timestamp = datetime.now().isoformat()
    log_entry = {'timestamp': timestamp, 'agent': agent, 'message': message}
    r.lpush('conversation_logs', str(log_entry))


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/logs', methods=['GET'])
def get_logs():
    logs = [eval(log.decode()) for log in r.lrange('conversation_logs', 0, -1)]
    return jsonify(logs)

@app.route('/clearlog', methods=['POST'])
def ClearLogs():
    data = request.json  
    action = data.get('action')
    results=r.flushall()
    if results: 
        return jsonify({"Action": "log cleared"}), 200
    else:
        return jsonify({"Action": "log clear error"}), 400
   

@app.route('/start', methods=['POST'])
def start_communication():
    user_message = request.json['message']
    print(f"user_message:{user_message}")
    log_to_redis(f'{user_ID}', user_message)
    user_prompt = f'From {user_ID}: ' + user_message
    r.lpush(f'{ia_Assistant_ID}_queue', user_prompt)    
    return jsonify({'status': 'AIQuery'})
    
@app.route('/log', methods=['POST'])
def log_message():
    data = request.get_json()
    conversation_logs.append(data)
    return jsonify({'status': 'logged'})


if __name__ == '__main__':
    app.run(port=5002)
