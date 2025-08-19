import os
import json
import re
import requests
from flask import Flask, request, jsonify
from dotenv import load_dotenv
import google.generativeai as genai
from flask_cors import CORS
import googlemaps

# .envから環境変数を読み込む
load_dotenv()

# Flaskアプリのセットアップ
app = Flask(__name__)
# CORSを有効にしフロントエンドからのアクセスを許可
CORS(app)

# Gemini APIキーを設定
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# Google Mapsのクライアントを初期化
gmaps = googlemaps.Client(key=os.getenv("GOOGLE_MAPS_API_KEY"))

# 楽天ホテル検索関数


def search_rakuten_hotels(keyword, checkin_date, checkout_date):
    # --- ステップ1: キーワードでホテルを検索 ---
    KEYWORD_SEARCH_ENDPOINT = "https://app.rakuten.co.jp/services/api/Travel/KeywordHotelSearch/20170426"
    keyword_params = {
        "applicationId": os.getenv("RAKUTEN_APP_ID"),
        "affiliateId": os.getenv("RAKUTEN_AFFILIATE_ID"),
        "format": "json",
        "hits": 3, # 候補となるホテルを3つ取得
        "keyword": keyword
    }
    
    try:
        response = requests.get(KEYWORD_SEARCH_ENDPOINT, params=keyword_params)
        response.raise_for_status()
        keyword_data = response.json()
        
        if not keyword_data.get("hotels"):
            return [] # 候補ホテルが見つからなければ終了

        # --- ステップ2: 各ホテルの空室を検索 ---
        VACANT_SEARCH_ENDPOINT = "https://app.rakuten.co.jp/services/api/Travel/VacantHotelSearch/20170426"
        available_hotels = []

        for hotel_data in keyword_data["hotels"]:
            hotel_info = hotel_data['hotel'][0]['hotelBasicInfo']
            hotel_no = hotel_info.get('hotelNo')

            if not hotel_no:
                continue

            vacant_params = {
                "applicationId": os.getenv("RAKUTEN_APP_ID"),
                "affiliateId": os.getenv("RAKUTEN_AFFILIATE_ID"),
                "format": "json",
                "checkinDate": checkin_date,
                "checkoutDate": checkout_date,
                "hotelNo": hotel_no # ★★★ ホテルIDでピンポイント検索 ★★★
            }
            
            vacant_response = requests.get(VACANT_SEARCH_ENDPOINT, params=vacant_params)
            # 空室がない場合は404エラーが返ることがあるので、ここではエラーを無視
            if vacant_response.status_code == 200:
                vacant_data = vacant_response.json()
                if vacant_data.get("hotels"):
                    # 空室があったホテルの情報をリストに追加
                    hotel_data = vacant_data["hotels"][0]
                    hotel = hotel_data['hotel'][0]['hotelBasicInfo']
                    charge_info = hotel_data['hotel'][1].get('hotelRatingInfo')
                    
                    available_hotels.append({
                        "name": hotel.get('hotelName'),
                        "hotelImageUrl": hotel.get('hotelImageUrl'),
                        "planListUrl": hotel.get('planListUrl'),
                        "reviewAverage": hotel.get('reviewAverage'),
                        "charge": charge_info.get('salesPrice') if charge_info else None
                    })
        
        return available_hotels

    except requests.exceptions.RequestException as e:
        print(f"楽天APIリクエストエラー: {e}")
        return []

# APIエンドポイントを定義
@app.route("/api/travel-plan", methods=["POST"])
def create_travel_plan():
    data = request.get_json()
    user_prompt = data.get("prompt")
    checkin_date = data.get("checkinDate")
    checkout_date = data.get("checkoutDate")

    if not user_prompt:
        return jsonify({"error": "リクエスト内容が空です。"}), 400

    try:
        # --- ステップ1: AIにプランの骨子を作成させる ---
        model = genai.GenerativeModel('gemini-2.5-pro')
        prompt_for_ai = f"""
        あなたはプロの旅行プランナーです。
        ユーザーからの以下の要望に基づいて、魅力的で具体的な旅行プランを1つ提案してください。
        # 出力形式のルール
        - 必ずJSON形式のみを出力してください。
        - JSON以外の余計な文章（挨拶など）は一切含めないでください。
        - JSONのキーは "title", "summary", "itinerary" としてください。
        - "title": 旅行プランのタイトル。必ず「」で主要な地名一つだけを囲んでください。(例: 「箱根」で過ごす癒しの温泉旅)
        - "summary": 2-3行の概要説明文
        - "itinerary": 旅程の配列。各要素は "day", "title", "description" をキーに持つオブジェクト。descriptionには「」で具体的な施設名や場所名を複数含めてください。
        # ユーザーの要望
        {user_prompt}
        """
        response = model.generate_content(prompt_for_ai)
        match = re.search(r'\{.*\}', response.text, re.DOTALL)
        if not match:
            raise ValueError("AIの応答からJSONデータを抽出できませんでした。")
        plan_data = json.loads(match.group(0))

        # --- ステップ2: Google Mapsで情報補強 ---
        for item in plan_data.get('itinerary', []):
            locations_in_item = []
            found_names = re.findall(r'「(.*?)」', item['description'])
            
            for loc_name in found_names:
                places_result = gmaps.places(query=loc_name, language='ja')
                
                if places_result.get('status') == 'OK' and places_result.get('results'):
                    place = places_result['results'][0]
                    photo_urls = []
                    for photo in place.get('photos', []):
                        photo_ref = photo['photo_reference']
                        photo_url = f"https://maps.googleapis.com/maps/api/place/photo?maxwidth=400&photoreference={photo_ref}&key={os.getenv('GOOGLE_MAPS_API_KEY')}"
                        photo_urls.append(photo_url)
                        if len(photo_urls) >= 2:
                            break
                    
                    lat = place['geometry']['location']['lat']
                    lng = place['geometry']['location']['lng']
                    
                    location_detail = {
                        'name': place.get('name'),
                        'address': place.get('formatted_address'),
                        'rating': place.get('rating', '評価なし'),
                        'lat': lat,
                        'lng': lng,
                        'photo_urls': photo_urls
                    }
                    locations_in_item.append(location_detail)
            item['locations'] = locations_in_item
        
        # --- ステップ3: 楽天APIでホテル情報を取得 ---
        # ★★★ 呼び出し方をキーワード検索に戻す ★★★
        match_location = re.search(r'「(.*?)」', plan_data.get('title', ''))
        search_keyword = None
        if match_location:
            search_keyword = match_location.group(1).split('・')[0]
        
        hotel_suggestions = []
        if search_keyword and checkin_date and checkout_date:
            hotel_suggestions = search_rakuten_hotels(search_keyword, checkin_date, checkout_date)
        
        plan_data['hotel_suggestions'] = hotel_suggestions

        # --- ステップ4: フロントエンドに完成版プランを返す ---
        return jsonify(plan_data)

    except Exception as e:
        print(f"エラーが発生しました: {e}")
        return jsonify({"error": "プランの生成に失敗しました"}), 500

# 動作確認用のページ
@app.route('/')
def index():
    return "旅のAIコンシェルジュ　APIサーバー"


# サーバーを起動
if __name__ == '__main__':
    app.run(debug=True, port=5001)
