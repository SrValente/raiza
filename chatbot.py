from flask import Flask, request, jsonify, after_this_request
from flask_cors import CORS
import requests

app = Flask(__name__)
CORS(app)  # Permite CORS para integração com sites

@app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    user_message = data.get('message', '')
    
    # Configuração da API Groq
    groq_response = requests.post(
        'https://api.groq.com/openai/v1/chat/completions',
        headers={
            'Authorization': 'Bearer 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',
            'Content-Type': 'application/json'
        },
        json={
            'model': 'mixtral-8x7b-32768',
            'messages': [{'role': 'user', 'content': user_message}],
            'temperature': 0.5
        }
    )
    
    if groq_response.status_code == 200:
        return jsonify({
            'response': groq_response.json()['choices'][0]['message']['content']
        })
    else:
        return jsonify({'error': 'Erro na API Groq'}), 500

if __name__ == '__main__':
    app.run(debug=False)
