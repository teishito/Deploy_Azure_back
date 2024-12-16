from flask import Flask, jsonify, request
from flask_cors import CORS
import os
import sqlite3
import json
import logging

logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "https://tech0-gen-8-step3-app-py-10.azurewebsites.net"}})  # CORS設定を更新

@app.before_request
def log_request_info():
    logging.debug("Request Headers: %s", request.headers)
    logging.debug("Request Body: %s", request.get_data())

@app.route('/api/hello', methods=['GET'])
def hello_world():
    return jsonify(message='Hello World by Flask')

@app.route('/api/check-db', methods=['GET'])
def check_db():
    try:
        conn = sqlite3.connect('example.db')
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM restaurants LIMIT 5")
        rows = cursor.fetchall()
        conn.close()
        return jsonify(rows)
    except sqlite3.Error as e:
        logging.error(f"Error reading database: {e}")
        return jsonify({"error": "データベースエラーが発生しました。"}), 500

@app.route('/api/restaurants', methods=['GET', 'POST'])
def get_restaurants():
    if request.method == 'POST':
        filters = request.json  # POSTリクエストのボディを取得
        area = filters.get('area', '')
        genre = filters.get('genre', '')
        people = filters.get('people', 0)

        # データベースクエリに基づいてフィルタリング
        query = 'SELECT * FROM restaurants WHERE 1=1'
        params = []

        if area:
            query += ' AND area = ?'
            params.append(area)
        if genre:
            query += ' AND category LIKE ?'
            params.append(f'%{genre}%')
        if people:
            query += ' AND capacity >= ?'
            params.append(people)

        conn = sqlite3.connect('example.db')
        c = conn.cursor()
        c.execute(query, params)
        rows = c.fetchall()
        conn.close()

        # レスポンス用にデータを整形
        column_names = [desc[0] for desc in c.description]
        restaurants = [dict(zip(column_names, row)) for row in rows]
        return jsonify({'restaurants': restaurants})

    # GETメソッド用の処理
    conn = sqlite3.connect('example.db')
    c = conn.cursor()
    c.execute('SELECT * FROM restaurants')
    rows = c.fetchall()
    conn.close()

    column_names = [desc[0] for desc in c.description]
    restaurants = [dict(zip(column_names, row)) for row in rows]
    return jsonify({'restaurants': restaurants})

@app.route('/results', methods=['GET', 'POST'])
def get_results():
    try:
        # リクエスト情報をログに出力
        logging.debug(f"HTTP Method: {request.method}")
        logging.debug(f"Request Headers: {json.dumps(dict(request.headers), ensure_ascii=False)}")
        if request.method == 'POST':
            filters = request.json
            logging.debug(f"Received JSON: {json.dumps(filters, ensure_ascii=False)}")

            # フィルタ条件
            area = filters.get('area', '').strip()
            genre = filters.get('genre', '').strip()
            guests = filters.get('people', 0)
            budget_min = filters.get('budgetMin', None)
            budget_max = filters.get('budgetMax', None)
            private_room = filters.get('privateRoom', '').strip()
            drink_included = filters.get('drinkIncluded', '').strip()

            # SQLクエリ構築
            query = 'SELECT * FROM restaurants WHERE 1=1'
            params = []

            if area:
                query += ' AND area = ?'
                params.append(area)
            if genre:
                query += ' AND category LIKE ?'
                params.append(f'%{genre}%')
            if guests:
                query += ' AND capacity >= ?'
                params.append(guests)
            if budget_min is not None:
                query += ' AND budget_min >= ?'
                params.append(budget_min)
            if budget_max is not None:
                query += ' AND budget_max <= ?'
                params.append(budget_max)
            if private_room in ['有', '無']:
                query += ' AND has_private_room = ?'
                params.append(private_room)
            if drink_included in ['有', '無']:
                query += ' AND has_drink_all_included = ?'
                params.append(drink_included)

            # データベースクエリ
            conn = sqlite3.connect('example.db')
            cursor = conn.cursor()
            logging.debug(f"Executing Query: {query} with Params: {params}")
            cursor.execute(query, params)
            rows = cursor.fetchall()
            column_names = [desc[0] for desc in cursor.description]
            conn.close()

            # 結果をJSONに変換
            result_dict_list = [dict(zip(column_names, row)) for row in rows]
            result_json = json.dumps(result_dict_list, ensure_ascii=False)
            logging.debug(f"Query Result: {result_json}")

            return jsonify({'restaurants': result_dict_list}), 200

        elif request.method == 'GET':
            logging.debug("GETリクエスト受信")
            conn = sqlite3.connect('example.db')
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM restaurants')
            rows = cursor.fetchall()
            column_names = [desc[0] for desc in cursor.description]
            conn.close()

            result_dict_list = [dict(zip(column_names, row)) for row in rows]
            return jsonify({'restaurants': result_dict_list}), 200

    except Exception as e:
        logging.error(f"エラーが発生しました: {str(e)}")
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
        
    port = int(os.environ.get('PORT', 8000))  # 環境変数PORTが設定されていない場合、デフォルトで8000を使用
    app.run(host='0.0.0.0', port=port)
