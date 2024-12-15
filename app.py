from flask import Flask, jsonify, request
from flask_cors import CORS
import os
import sqlite3
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build
import logging

# ログ設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "https://tech0-gen-8-step3-app-py-10.azurewebsites.net"}})  # CORS設定を更新

# Google Sheets API認証
SERVICE_ACCOUNT_FILE = 'service_account.json'  # サービスアカウントのJSONファイルのパス
SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']

# スプレッドシートの設定
SHEET_ID = '13W3SPt7KrGnYCLzC8DQ0QyoNhFFs8CEd4faHBhUSDww'
SHEET_RANGE = 'DB!A:AC'  # 取得する範囲

def authenticate_google_services():
    credentials = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    return credentials

def get_spreadsheet_data():
    try:
        credentials = authenticate_google_services()
        service = build('sheets', 'v4', credentials=credentials)
        sheet = service.spreadsheets()
        result = sheet.values().get(spreadsheetId=SHEET_ID, range=SHEET_RANGE).execute()
        rows = result.get('values', [])
        if rows:
            logging.info(f"Google Sheetsから{len(rows)}行のデータを取得しました。")
            headers = rows[0]
            data = rows[1:]
            return data, headers
        logging.warning("Google Sheetsにデータが存在しません。")
        return [], []
    except Exception as e:
        logging.error(f"Google Sheets APIエラー: {e}")
        raise

def insert_data_to_db(data, headers):
    conn = sqlite3.connect('example.db')
    c = conn.cursor()

    # データを挿入
    for row in data:
        # 行の長さが29に満たない場合、足りない部分を空文字で補完
        if len(row) < 29:
            row += [''] * (29 - len(row))  # 足りない分を空文字で補完

        c.execute('''
            INSERT INTO restaurants (
                name, address, phone_number, tabelog_rating, tabelog_review_count, tabelog_link, google_rating, 
                google_review_count, google_link, opening_hours, course, menu, drink_menu, store_top_image, 
                description, longitude, latitude, area, nearest_station, directions, capacity, category, 
                budget_min, budget_max, has_private_room, has_drink_all_included, detail_image1, detail_image2, 
                detail_image3
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', tuple(row))

    conn.commit()
    conn.close()

@app.route('/')
def index():
    try:
        data, headers = get_spreadsheet_data()
        if not data:
            logging.error("Google Sheetsからデータが取得できませんでした。")
            return jsonify({'error': 'Google Sheetsからデータが取得できませんでした。'}), 500

        # データベースへのデータ挿入を試行
        try:
            insert_data_to_db(data, headers)
            logging.info("データがデータベースに正常に保存されました。")
            return jsonify({'message': 'データがデータベースに保存されました。'})
        except Exception as db_error:
            logging.error(f"データベース挿入エラー: {db_error}")
            return jsonify({'error': f'データベース保存エラー: {str(db_error)}'}), 500
    except Exception as e:
        logging.error(f"データ処理中にエラーが発生しました: {e}")
        return jsonify({'error': f'サーバー処理中にエラーが発生しました: {str(e)}'}), 500

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

@app.route('/restaurant/<int:id>', methods=['GET'])
def get_restaurant_by_id(id):
    conn = sqlite3.connect('example.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM restaurants WHERE id = ?", (id,))
    row = cursor.fetchone()
    conn.close()

    if row is None:
        print("No data found for this ID")
        return jsonify({'error': 'Restaurant not found'}), 404

    restaurant = {
        "id": row[0],
        "name": row[1],
        "address": row[2],
        "phone_number": row[3],
        "tabelog_rating": row[4],
        "tabelog_review_count": row[5],
        "tabelog_link": row[6],
        "google_rating": row[7],
        "google_review_count": row[8],
        "google_link": row[9],
        "opening_hours": row[10],
        "course": row[11],
        "menu": row[12],
        "drink_menu": row[13],
        "store_top_image": row[14],
        "description": row[15],
        "longitude": row[16],
        "latitude": row[17],
        "area": row[18],
        "nearest_station": row[19],
        "directions": row[20],
        "capacity": row[21],
        "category": row[22],
        "budget_min": row[23],
        "budget_max": row[24],
        "has_private_room": row[25],
        "has_drink_all_included": row[26],
        "detail_image1": row[27],
        "detail_image2": row[28],
        "detail_image3": row[29],
    }
    return jsonify(restaurant)

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

@app.route('/results', methods=['GET'])
def get_detailed_restaurants():
    area = request.args.get('area', '').strip()
    guests = request.args.get('guests', 0, type=int)
    genre = request.args.get('genre', '').strip()
    budget_min = request.args.get('budgetMin', None, type=int)
    budget_max = request.args.get('budgetMax', None, type=int)
    private_room = request.args.get('privateRoom', '').lower()
    drink_included = request.args.get('drinkIncluded', '').lower()

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
    if private_room in ['yes', 'no']:
        query += ' AND has_private_room = ?'
        params.append(private_room)
    if drink_included in ['yes', 'no']:
        query += ' AND has_drink_all_included = ?'
        params.append(drink_included)

    conn = sqlite3.connect('example.db')
    cursor = conn.cursor()
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    if rows:
        column_names = [desc[0] for desc in cursor.description]
        restaurants = [dict(zip(column_names, row)) for row in rows]
        return jsonify({'restaurants': restaurants}), 200
    else:
        return jsonify({'message': '条件に一致するレストランが見つかりませんでした。', 'restaurants': []}), 200

@app.route('/list-endpoints', methods=['GET'])
def list_endpoints():
    return jsonify([str(rule) for rule in app.url_map.iter_rules()])

if __name__ == '__main__':
        
    port = int(os.environ.get('PORT', 8000))  # 環境変数PORTが設定されていない場合、デフォルトで8000を使用
    app.run(host='0.0.0.0', port=port)
