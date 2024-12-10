from flask import Flask, jsonify, request
from flask_cors import CORS
import os
import sqlite3
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build

app = Flask(__name__)
#CORS(app, resources={r"/api/*": {"origins": "https://tech0-gen-8-step3-app-py-10.azurewebsites.net"}})  # CORS設定を更新
CORS(app, resources={r"/api/*": {"origins": "*"}})  # CORS設定を許可する

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
            headers = rows[0]
            data = rows[1:]
            return data, headers
        return [], []
    except Exception as e:
        app.logger.error(f"Failed to fetch data from Google Sheets: {e}")
        return [], []

def init_db():
    try:
        conn = sqlite3.connect('example.db')
        c = conn.cursor()

        # 既存のテーブルを削除
        c.execute('DROP TABLE IF EXISTS restaurants')

        # 新しいテーブルを作成
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
    finally:
        conn.close()

def insert_data_to_db(data, headers):
    try:
        conn = sqlite3.connect('example.db')
        c = conn.cursor()

        # データを挿入
        for row in data:
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
    finally:
        conn.close()

@app.route('/api/areas', methods=['GET'])
def get_areas():
    try:
        conn = sqlite3.connect('example.db')
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT area FROM restaurants")
        rows = cursor.fetchall()
        conn.close()
        areas = [row[0] for row in rows]
        return jsonify(areas)
    except sqlite3.Error as e:
        app.logger.error(f"Database error in /api/areas: {e}")
        return jsonify({"error": "Failed to fetch areas"}), 500

@app.route('/api/genres', methods=['GET'])
def get_genres():
    try:
        conn = sqlite3.connect('example.db')
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT category FROM restaurants")
        rows = cursor.fetchall()
        conn.close()
        genres = [row[0] for row in rows]
        return jsonify(genres)
    except sqlite3.Error as e:
        app.logger.error(f"Database error in /api/genres: {e}")
        return jsonify({"error": "Failed to fetch genres"}), 500

@app.route('/api/search', methods=['GET'])
def search_restaurants():
    try:
        area = request.args.get('area', '')
        guests = request.args.get('guests', None, type=int)
        genre = request.args.get('genre', '')
        budget_min = request.args.get('budgetMin', None, type=int)
        budget_max = request.args.get('budgetMax', None, type=int)
        private_room = request.args.get('privateRoom', '')
        drink_included = request.args.get('drinkIncluded', '')

        query = "SELECT * FROM restaurants WHERE 1=1"
        params = []

        if area:
            query += " AND area = ?"
            params.append(area)
        if guests:
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
        if private_room:
            query += " AND has_private_room = ?"
            params.append(private_room)
        if drink_included:
            query += " AND has_drink_all_included = ?"
            params.append(drink_included)

        conn = sqlite3.connect('example.db')
        cursor = conn.cursor()
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        result = [
            {desc[0]: row[idx] for idx, desc in enumerate(cursor.description)}
            for row in rows
        ]
        return jsonify(result)
    except sqlite3.Error as e:
        app.logger.error(f"Database error in /api/search: {e}")
        return jsonify({"error": "Failed to search restaurants"}), 500
    except Exception as e:
        app.logger.error(f"Unexpected error in /api/search: {e}")
        return jsonify({"error": "Unexpected error occurred"}), 500

if __name__ == '__main__':
    init_db()  # アプリ起動時にDBを初期化
    port = int(os.environ.get('PORT', 8000))  # 環境変数PORTが設定されていない場合、デフォルトで8000を使用
    app.run(host='0.0.0.0', port=port)
