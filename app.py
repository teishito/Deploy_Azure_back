from flask import Flask, jsonify, request
from urllib.parse import unquote
from flask_cors import CORS
import os
import sqlite3
import json
import logging

logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})  # 全エンドポイントでCORSを許可

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

@app.before_request
def log_request_info():
    logging.debug("Request Headers: %s", request.headers)
    logging.debug("Request Body: %s", request.get_data(as_text=True))


@app.route('/results', methods=['POST'])
def get_results():
    try:
        if request.method != 'POST':
            logging.warning("不正なリクエストメソッド: %s", request.method)
            return jsonify({'error': '405 Method Not Allowed'}), 405

        # クエリパラメータの取得とデコード
        filters = request.json
        logging.debug(f"受信したフィルタ: {filters}")

        area = unquote(filters.get('area', '').strip()) or None
        genre = unquote(filters.get('genre', '').strip()) or None
        guests = filters.get('guests', 0)
        budget_min = filters.get('budgetMin', None)
        budget_max = filters.get('budgetMax', None)
        private_room = unquote(filters.get('privateRoom', '').strip()) or None
        drink_included = unquote(filters.get('drinkIncluded', '').strip()) or None

        logging.debug(f"デコード後のフィルタ: area={area}, genre={genre}, guests={guests}, "
                      f"budget_min={budget_min}, budget_max={budget_max}, "
                      f"private_room={private_room}, drink_included={drink_included}")

        # SQLクエリの構築
        query = 'SELECT * FROM restaurants WHERE 1=1'
        params = []

        if area:
            query += ' AND area = ?'
            params.append(area)
        if genre:
            query += ' AND category LIKE ?'
            params.append(f"%{genre}%")
        if guests:
            query += ' AND capacity >= ?'
            params.append(guests)
        if budget_min:
            query += ' AND budget_min >= ?'
            params.append(budget_min)
        if budget_max:
            query += ' AND budget_max <= ?'
            params.append(budget_max)
        if private_room in ['有', '無']:
            query += ' AND has_private_room = ?'
            params.append(private_room)
        if drink_included in ['有', '無']:
            query += ' AND has_drink_all_included = ?'
            params.append(drink_included)

        logging.debug(f"実行クエリ: {query} パラメータ: {params}")

        # データベースクエリ実行
        conn = sqlite3.connect('example.db')
        cursor = conn.cursor()
        cursor.execute(query, params)
        rows = cursor.fetchall()
        column_names = [desc[0] for desc in cursor.description]
        conn.close()

        # 結果整形
        restaurants = [dict(zip(column_names, row)) for row in rows]
        logging.debug(f"取得したデータ: {restaurants}")

        return jsonify({'restaurants': restaurants}), 200

    except Exception as e:
        logging.error(f"エラー発生: {str(e)}")
        return jsonify({'error': 'サーバー内部エラー', 'details': str(e)}), 500

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

@app.route('/restaurant/<int:id>/menu', methods=['GET'])
def get_menu_details(id):
    try:
        # データベース接続
        conn = sqlite3.connect('example.db')
        cursor = conn.cursor()

        # メニューとドリンクメニューを取得
        cursor.execute("SELECT menu, drink_menu FROM restaurants WHERE id = ?", (id,))
        row = cursor.fetchone()
        conn.close()

        # データが見つからない場合
        if not row:
            return jsonify({"error": "Menu not found"}), 404

        # データ形式の処理
        food_menu = row[0]
        drink_menu = row[1]

        # JSON文字列で保存されている場合
        try:
            food_menu = json.loads(food_menu) if food_menu else []
            drink_menu = json.loads(drink_menu) if drink_menu else []
        except json.JSONDecodeError:
            # カンマ区切りの場合
            food_menu = food_menu.split(",") if food_menu else []
            drink_menu = drink_menu.split(",") if drink_menu else []

        # メニューを返却
        return jsonify({
            "foodMenu": food_menu,
            "drinkMenu": drink_menu,
        }), 200

    except sqlite3.Error as e:
        # データベースエラー時の処理
        return jsonify({"error": "Database error", "details": str(e)}), 500

    except Exception as e:
        # その他の例外処理
        return jsonify({"error": "Internal server error", "details": str(e)}), 500


if __name__ == '__main__':
        
    port = int(os.environ.get('PORT', 8000))  # 環境変数PORTが設定されていない場合、デフォルトで8000を使用
    app.run(host='0.0.0.0', port=port)
