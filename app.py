from flask import Flask, jsonify, request
from flask_cors import CORS
import os
import sqlite3
import json
import logging

logging.basicConfig(level=logging.DEBUG)

@app.before_request
def log_request_info():
    logging.debug("Request Headers: %s", request.headers)
    logging.debug("Request Body: %s", request.get_data())

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "https://tech0-gen-8-step3-app-py-10.azurewebsites.net"}})  # CORS設定を更新

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
        
@app.route('/api/areas', methods=['GET'])
def get_areas():
    conn = sqlite3.connect('example.db')
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT area FROM restaurants")
    rows = cursor.fetchall()
    conn.close()
    areas = [row[0] for row in rows]
    return jsonify(areas)

@app.route('/api/genres', methods=['GET'])
def get_genres():
    conn = sqlite3.connect('example.db')
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT category FROM restaurants")
    rows = cursor.fetchall()
    conn.close()
    genres = [row[0] for row in rows]
    return jsonify(genres)

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

@app.route('/api/detailrestaurants', methods=['GET', 'POST'])
def get_detailed_restaurants():
    if request.method == 'POST':
        filters = request.json  # POSTリクエストのボディを取得
        area = filters.get('area', '')
        genre = filters.get('genre', '')
        people = filters.get('people', 0)
        private_room = filters.get('privateRoom', '')  # 個室フィルター
        drink_included = filters.get('drinkIncluded', '')  # 飲み放題フィルター
        budget_min = filters.get('budgetMin', None)
        budget_max = filters.get('budgetMax', None)

        # データベースクエリに基づいてフィルタリング
        query = 'SELECT * FROM restaurants WHERE 1=1'
        params = []

        # フィルタ条件の構築
        if area:
            query += ' AND area = ?'
            params.append(area)
        if genre:
            query += ' AND category LIKE ?'
            params.append(f'%{genre}%')
        if people:
            query += ' AND capacity >= ?'
            params.append(people)
        if private_room in ['有', '無']:
            query += ' AND has_private_room = ?'
            params.append(private_room)
        if drink_included in ['有', '無']:
            query += ' AND has_drink_all_included = ?'
            params.append(drink_included)
        if budget_min is not None:
            query += ' AND budget_min >= ?'
            params.append(budget_min)
        if budget_max is not None:
            query += ' AND budget_max <= ?'
            params.append(budget_max)

        # データベース接続
        conn = sqlite3.connect('example.db')
        c = conn.cursor()
        c.execute(query, params)
        rows = c.fetchall()
        conn.close()

        # レスポンス用にデータを整形
        if rows:
            column_names = [desc[0] for desc in c.description]
            restaurants = [dict(zip(column_names, row)) for row in rows]
            return jsonify({'restaurants': restaurants}), 200
        else:
            return jsonify({'message': '条件に一致するレストランが見つかりませんでした。', 'restaurants': []}), 200

    # GETメソッド用の処理（全データ取得）
    conn = sqlite3.connect('example.db')
    c = conn.cursor()
    c.execute('SELECT * FROM restaurants')
    rows = c.fetchall()
    conn.close()

    column_names = [desc[0] for desc in c.description]
    restaurants = [dict(zip(column_names, row)) for row in rows]
    return jsonify({'restaurants': restaurants}), 200

def fetch_from_db(query, params):
    """データベースから指定クエリでデータを取得する関数"""
    conn = sqlite3.connect('example.db')
    cursor = conn.cursor()
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return rows

@app.route('/results', methods=['GET', 'POST'])
def get_results():
    """
    検索条件に基づくレストラン情報を取得するエンドポイント
    GET: 全レストランデータを取得
    POST: 条件に基づいてフィルタリングされたデータを取得
    """
    try:
        if request.method == 'POST':
            # POSTリクエストのボディからフィルタ条件を取得
            filters = request.json
            area = filters.get('area', '').strip()
            genre = filters.get('genre', '').strip()
            guests = filters.get('people', 0)
            private_room = filters.get('privateRoom', '')  # 個室フィルター
            drink_included = filters.get('drinkIncluded', '')  # 飲み放題フィルター
            budget_min = filters.get('budgetMin', None)
            budget_max = filters.get('budgetMax', None)

            # SQLクエリの構築
            query = 'SELECT * FROM restaurants WHERE 1=1'
            params = []

            # フィルタ条件の追加
            if area:
                query += ' AND area = ?'
                params.append(area)
            if genre:
                query += ' AND category LIKE ?'
                params.append(f'%{genre}%')
            if guests:
                query += ' AND capacity >= ?'
                params.append(guests)
            if private_room in ['有', '無']:
                query += ' AND has_private_room = ?'
                params.append(private_room)
            if drink_included in ['有', '無']:
                query += ' AND has_drink_all_included = ?'
                params.append(drink_included)
            if budget_min is not None:
                query += ' AND budget_min >= ?'
                params.append(budget_min)
            if budget_max is not None:
                query += ' AND budget_max <= ?'
                params.append(budget_max)

            # データベース接続とクエリ実行
            conn = sqlite3.connect('example.db')
            cursor = conn.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()
            column_names = [desc[0] for desc in cursor.description]
            conn.close()

            # データ整形とレスポンス
            restaurants = [dict(zip(column_names, row)) for row in rows]
            return jsonify({'restaurants': restaurants}), 200

        # GETリクエストの場合（全データ取得）
        conn = sqlite3.connect('example.db')
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM restaurants')
        rows = cursor.fetchall()
        column_names = [desc[0] for desc in cursor.description]
        conn.close()

        # 全データを整形してレスポンス
        restaurants = [dict(zip(column_names, row)) for row in rows]
        return jsonify({'restaurants': restaurants}), 200

    except sqlite3.Error as db_error:
        # データベースエラー処理
        return jsonify({'error': f'Database error: {db_error}'}), 500

    except Exception as e:
        # その他のエラー処理
        return jsonify({'error': f'An error occurred: {e}'}), 500

if __name__ == '__main__':
        
    port = int(os.environ.get('PORT', 8000))  # 環境変数PORTが設定されていない場合、デフォルトで8000を使用
    app.run(host='0.0.0.0', port=port)
