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

@app.route('/api/restaurants/<int:restaurant_id>', methods=['GET'])
def get_restaurant_details(restaurant_id):
    """
    指定されたレストランIDの詳細情報を取得するエンドポイント。
    """
    conn = sqlite3.connect('example.db')
    c = conn.cursor()

    # 特定のレストランを取得
    c.execute('SELECT * FROM restaurants WHERE id = ?', (restaurant_id,))
    row = c.fetchone()
    conn.close()

    if row:
        # カラム名をキーとして辞書形式に変換
        column_names = [desc[0] for desc in c.description]
        restaurant = dict(zip(column_names, row))
        return jsonify(restaurant)
    else:
        return jsonify({'error': '指定されたレストランが見つかりませんでした。'}), 404

@app.route('/api/search', methods=['GET'])
def search_restaurants():
    # クエリパラメータを取得
    area = request.args.get('area', '')  # エリア
    guests = request.args.get('guests', None, type=int)  # 人数
    genre = request.args.get('genre', '')  # ジャンル
    budget_min = request.args.get('budgetMin', None, type=int)  # 予算の下限
    budget_max = request.args.get('budgetMax', None, type=int)  # 予算の上限
    private_room = request.args.get('privateRoom', '')  # 個室の希望
    drink_included = request.args.get('drinkIncluded', '')  # 飲み放題の希望

    # SQLクエリの構築
    query = "SELECT * FROM restaurants WHERE 1=1"
    params = []

    # エリアは必須条件
    if area:
        query += " AND area = ?"
        params.append(area)
    
    # その他の条件は任意
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
    if private_room:
        query += " AND has_private_room = ?"
        params.append(private_room)
    if drink_included:
        query += " AND has_drink_all_included = ?"
        params.append(drink_included)

    # データベース接続とクエリの実行
    conn = sqlite3.connect('example.db')
    cursor = conn.cursor()
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    # データを整形して返却
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
    return jsonify(result)

if __name__ == '__main__':
    init_db()  # アプリ起動時にDBを初期化
    port = int(os.environ.get('PORT', 8000))  # 環境変数PORTが設定されていない場合、デフォルトで8000を使用
    app.run(host='0.0.0.0', port=port)
