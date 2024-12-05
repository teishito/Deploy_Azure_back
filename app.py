from flask import Flask, render_template, request, jsonify
from google.oauth2 import service_account
from googleapiclient.discovery import build
import pandas as pd
import json

app = Flask(__name__)

# サービスアカウント認証情報
SERVICE_ACCOUNT_FILE = 'service_account.json'
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

# スプレッドシートの設定
DB_ID = '13W3SPt7KrGnYCLzC8DQ0QyoNhFFs8CEd4faHBhUSDww'
DB_RANGE = 'DB!A:AE'

# Google API認証
def authenticate_google_services():
    with open(SERVICE_ACCOUNT_FILE, 'r') as f:
        service_account_info = json.load(f)
    credentials = service_account.Credentials.from_service_account_info(
        service_account_info, scopes=SCOPES
    )
    return credentials

# スプレッドシートからデータを取得する関数
def get_spreadsheet_data(sheet_id, range_):
    try:
        credentials = authenticate_google_services()
        sheets_service = build('sheets', 'v4', credentials=credentials)
        sheet = sheets_service.spreadsheets()
        result = sheet.values().get(spreadsheetId=sheet_id, range=range_).execute()
        rows = result.get('values', [])
        if rows:
            headers = rows[0]
            data = pd.DataFrame(rows[1:], columns=headers)
            return data
        else:
            return pd.DataFrame()
    except Exception as e:
        print(f"Error retrieving spreadsheet data: {e}")
        return pd.DataFrame()

@app.route('/')
def index():
    df = get_spreadsheet_data(DB_ID, DB_RANGE)

    if df.empty:
        return "スプレッドシートのデータが見つかりません。"

    # NaNを空文字に置き換え
    df = df.fillna("")
    df["食べログ点数"] = pd.to_numeric(df["食べログ点数"], errors='coerce')
    df["Google点数"] = pd.to_numeric(df["Google点数"], errors='coerce')

    # HTMLテンプレートにデータを渡す
    return render_template('index.html', areas=df["エリア"].unique(), df=df.to_dict(orient='records'))

@app.route('/search', methods=['POST'])
def search():
    df = get_spreadsheet_data(DB_ID, DB_RANGE)

    if df.empty:
        return jsonify({"error": "スプレッドシートのデータが見つかりません。"}), 400

    df = df.fillna("")
    df["食べログ点数"] = pd.to_numeric(df["食べログ点数"], errors='coerce')
    df["Google点数"] = pd.to_numeric(df["Google点数"], errors='coerce')

    data = request.json
    area = data.get("area", "")
    private_room = data.get("private_room", "指定なし")
    budget_min = int(data.get("budget_min", 0))
    budget_max = int(data.get("budget_max", 10000))

    filtered_df = df[
        (df["エリア"].str.contains(area)) &
        (df["食べログ点数"].notna()) &
        (df["Google点数"].notna()) &
        (df["予算"].apply(lambda x: budget_min <= float(x) <= budget_max))
    ]

    if private_room != "指定なし":
        filtered_df = filtered_df[filtered_df["個室"] == private_room]

    sorted_df = filtered_df.sort_values(
        by=["食べログ点数", "Google点数"], ascending=[False, False]
    )

    return jsonify(sorted_df.to_dict(orient="records"))

if __name__ == '__main__':
    app.run(debug=True)
