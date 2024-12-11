from flask import Flask, jsonify, request
from flask_cors import CORS
import os
import sqlite3
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})  # CORS設定を更新

@app.route('/', methods=['GET'])
def hello():
    return jsonify({'message': 'Flask start!'})

@app.route('/api/hello', methods=['GET'])
def hello_world():
    return jsonify(message='Hello World by Flask')

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


@app.route('/search', methods=['GET'])
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
    
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8000))  # 環境変数PORTが設定されていない場合、デフォルトで8000を使用
    app.run(host='0.0.0.0', port=port)
