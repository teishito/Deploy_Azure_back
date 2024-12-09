from flask import Flask, jsonify, request
from flask_cors import CORS
import os
import sqlite3
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build

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

def init_db():
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
    conn.close()

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
    data, headers = get_spreadsheet_data()

    if not data:
        return jsonify({'error': 'スプレッドシートのデータが見つかりません。'})

    try:
        # データをSQLiteに保存
        insert_data_to_db(data, headers)
        return jsonify({'message': 'データがデータベースに保存されました。'})
    except Exception as e:
        return jsonify({'error': f'データベース保存中にエラーが発生しました: {str(e)}'})
        

@app.route('/', methods=['GET'])
def hello():
    return jsonify({'message': 'Flask start!'})

@app.route('/api/hello', methods=['GET'])
def hello_world():
    return jsonify(message='Hello World by Flask')


@app.route('/api/restaurants')
def get_restaurants():
    if request.method == 'POST':
        filters = request.json
        area = filters.get('area', '')
        genre = filters.get('genre', '')
        people = filters.get('people', '')

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

        column_names = [desc[0] for desc in c.description]
        restaurants = [dict(zip(column_names, row)) for row in rows]
        return jsonify({'restaurants': restaurants})
    
    # GETメソッドの場合
    conn = sqlite3.connect('example.db')
    c = conn.cursor()
    c.execute('SELECT * FROM restaurants')
    rows = c.fetchall()
    conn.close()

    column_names = [desc[0] for desc in c.description]
    restaurants = [dict(zip(column_names, row)) for row in rows]
    return jsonify({'restaurants': restaurants})


if __name__ == '__main__':
    init_db()  # アプリ起動時にDBを初期化
    port = int(os.environ.get('PORT', 8000))  # 環境変数PORTが設定されていない場合、デフォルトで8000を使用
    app.run(host='0.0.0.0', port=port)
