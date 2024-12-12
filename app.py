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
CORS(app, resources={r"/*": {"origins": "*"}})  # CORS設定を更新

# ログ設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

# Google Sheets API設定
SERVICE_ACCOUNT_FILE = 'service_account.json'
SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']
SHEET_ID = '13W3SPt7KrGnYCLzC8DQ0QyoNhFFs8CEd4faHBhUSDww'
SHEET_RANGE = 'DB!A:AC'

# Google Sheets API認証
def authenticate_google_services():
    try:
        credentials = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE, scopes=SCOPES
        )
        logging.info("Google Sheets API認証に成功しました。")
        return credentials
    except Exception as e:
        logging.error(f"Google Sheets API認証に失敗しました: {e}")
        raise

# Google Sheetsからデータを取得
def get_spreadsheet_data():
    try:
        credentials = authenticate_google_services()
        service = build('sheets', 'v4', credentials=credentials)
        sheet = service.spreadsheets()
        result = sheet.values().get(spreadsheetId=SHEET_ID, range=SHEET_RANGE).execute()
        rows = result.get('values', [])
        if rows:
            headers = rows[0]
            data = rows[1:]
            logging.info(f"スプレッドシートから{len(data)}行のデータを取得しました。")
            return data, headers
        logging.warning("スプレッドシートにデータが存在しません。")
        return [], []
    except Exception as e:
        logging.error(f"スプレッドシートデータの取得に失敗しました: {e}")
        return [], []

# SQLite3データベースを初期化
def init_db(recreate=False):
    try:
        conn = sqlite3.connect('example.db')
        c = conn.cursor()
        if recreate:
            c.execute('DROP TABLE IF EXISTS restaurants')
            logging.info("既存のテーブルを削除しました。")
        c.execute('''
            CREATE TABLE IF NOT EXISTS restaurants (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                address TEXT,
                phone_number TEXT,
                tabelog_rating REAL,
                tabelog_review_count INTEGER,
                tabelog_link TEXT,
                google_rating REAL,
                google_review_count INTEGER,
                google_link TEXT,
                opening_hours TEXT,
                course TEXT,
                menu TEXT,
                drink_menu TEXT,
                store_top_image TEXT,
                description TEXT,
                longitude REAL,
                latitude REAL,
                area TEXT,
                nearest_station TEXT,
                directions TEXT,
                capacity INTEGER,
                category TEXT,
                budget_min INTEGER,
                budget_max INTEGER,
                has_private_room TEXT,
                has_drink_all_included TEXT,
                detail_image1 TEXT,
                detail_image2 TEXT,
                detail_image3 TEXT
            )
        ''')
        conn.commit()
        logging.info("データベースを初期化しました。")
    except sqlite3.Error as e:
        logging.error(f"データベース初期化中にエラーが発生しました: {e}")
    finally:
        conn.close()

# SQLite3にデータを挿入
def insert_data_to_db(data, headers):
    try:
        conn = sqlite3.connect('example.db')
        c = conn.cursor()
        for row in data:
            if len(row) < 29:
                row += [''] * (29 - len(row))
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
        logging.info(f"データベースに{len(data)}行のデータを挿入しました。")
    except sqlite3.Error as e:
        logging.error(f"データ挿入中にエラーが発生しました: {e}")
    finally:
        conn.close()

# エンドポイント
@app.route('/', methods=['GET'])
def home():
    return jsonify({"message": "データがデータベースに保存されました。"})

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

@app.route('/results', methods=['GET'])
def results_restaurants():
    try:
        area = request.args.get('area', '')
        guests = request.args.get('guests', None, type=int)
        genre = request.args.get('genre', '')
        budget_min = request.args.get('budgetMin', None, type=int)
        budget_max = request.args.get('budgetMax', None, type=int)
        private_room = request.args.get('privateRoom', '').lower()
        drink_included = request.args.get('drinkIncluded', '').lower()

        query = "SELECT * FROM restaurants WHERE 1=1"
        params = []

        if area:
            query += " AND area = ?"
            params.append(area)
        if guests is not None:
            query += " AND capacity >= ?"
            params.append(guests)
        if genre:
            query += " AND category LIKE ?"
            params.append(f"%{genre}%")
        if budget_min is not None:
            query += " AND budget_min >= ?"
            params.append(budget_min)
        if budget_max is not None:
            query += " AND budget_max <= ?"
            params.append(budget_max)
        if private_room in ['yes', 'no']:
            query += " AND has_private_room = ?"
            params.append(private_room)
        if drink_included in ['yes', 'no']:
            query += " AND has_drink_all_included = ?"
            params.append(drink_included)

        conn = sqlite3.connect('example.db')
        cursor = conn.cursor()
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        if not rows:
            return jsonify({"message": "条件に一致するレストランが見つかりませんでした。", "results": []}), 200

        result = [
            {
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
            for row in rows
        ]
        return jsonify({"results": result}), 200

    except sqlite3.Error as e:
        logging.error(f"Database error: {e}")
        return jsonify({"error": "データベースエラーが発生しました。"}), 500

@app.route('/api/restaurants', methods=['GET', 'POST'])
def get_restaurants():
    conn = sqlite3.connect('example.db')
    c = conn.cursor()

    if request.method == 'POST':
        filters = request.json  # POSTリクエストのボディを取得
        area = filters.get('area', '').strip()
        genre = filters.get('genre', '').strip()
        people = filters.get('people', 0)

        # SQLクエリの構築
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

        try:
            c.execute(query, params)
            rows = c.fetchall()
        except sqlite3.Error as e:
            conn.close()
            return jsonify({'error': f'Database error: {str(e)}'}), 500
        finally:
            conn.close()

        # レスポンス用の整形
        if not rows:
            return jsonify({'restaurants': []}), 200  # 結果がない場合

        column_names = [desc[0] for desc in c.description]
        restaurants = [dict(zip(column_names, row)) for row in rows]
        return jsonify({'restaurants': restaurants}), 200

    # GETメソッドの処理
    try:
        c.execute('SELECT * FROM restaurants')
        rows = c.fetchall()
    except sqlite3.Error as e:
        conn.close()
        return jsonify({'error': f'Database error: {str(e)}'}), 500
    finally:
        conn.close()

    if not rows:
        return jsonify({'restaurants': []}), 200

    column_names = [desc[0] for desc in c.description]
    restaurants = [dict(zip(column_names, row)) for row in rows]
    return jsonify({'restaurants': restaurants}), 200

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

@app.route('/list-endpoints', methods=['GET'])
def list_endpoints():
    return jsonify([str(rule) for rule in app.url_map.iter_rules()])

if __name__ == '__main__':
    # DBの初期化（再作成オプションを指定）
    init_db(recreate=True)

    # Google Sheetsからデータを取得してDBに保存
    data, headers = get_spreadsheet_data()
    if data:
        insert_data_to_db(data, headers)
    else:
        logging.warning("挿入可能なデータがありませんでした。")
        
    port = int(os.environ.get('PORT', 8000))  # 環境変数PORTが設定されていない場合、デフォルトで8000を使用
    app.run(host='0.0.0.0', port=port)
