from flask import Flask, jsonify, request
from flask_cors import CORS
import os
from google.cloud import translate_v2 as translate
import logging

# ログ設定
logging.basicConfig(level=logging.INFO)

# FlaskとCORSの設定
app = Flask(__name__)
CORS(app, resources={
    r"/api/*": {
        "origins": [
            "https://tech0-gen-8-step3-testapp-node2-19.azurewebsites.net",
            "http://localhost:3000"
        ]
    }
})

# 翻訳クライアントの初期化
translate_client = translate.Client()

@app.route('/', methods=['GET'])
def hello():
    return jsonify({'message': 'Flask start!'})

@app.route('/api/hello', methods=['GET'])
def hello_world():
    return jsonify(message='Hello World by Flask')

@app.route('/api/multiply/<int:id>', methods=['GET'])
def multiply(id):
    try:
        logging.info(f"Request to multiply: id={id}")
        doubled_value = id * 2
        return jsonify({"doubled_value": doubled_value})
    except Exception as e:
        logging.error(f"Error in multiply: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/echo', methods=['POST'])
def echo():
    try:
        data = request.get_json()
        message = data.get('message', 'No message provided')
        return jsonify({"message": f"echo: {message}"})
    except Exception as e:
        logging.error(f"Error in echo: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/translate', methods=['POST'])
def translate_text():
    try:
        data = request.get_json()
        text_to_translate = data['text']
        result = translate_client.translate(text_to_translate, target_language='en')
        return jsonify({"translated_text": result['translatedText']})
    except Exception as e:
        logging.error(f"Error in translate_text: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))  # Azure設定に合わせる
    app.run(host='0.0.0.0', port=port)
