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


def search_rakuten_hotels(keyword):
    RAKUTEN_ENDPOINT = "https://app.rakuten.co.jp/services/api/Travel/VacantHotelSearch/20170426"

    params = {
        "applicationId": os.getenv("RAKUTEN_APP_ID"),
        "affiliateId": os.getenv("RAKUTEN_AFFILIATE_ID"),
        "format": "json",
        "searchRadius": 3,  # 検索範囲（km）
        "hits": 3,  # 取得件数
        "keyword": keyword
    }

    try:
        response = requests.get(RAKUTEN_ENDPOINT, params=params)
        response.raise_for_status()  # エラーがあれば例外を発生
        data = response.json()

        hotels = []
        if "hotels" in data and data["hotels"]:
            for hotel_data in data["hotels"]:
                hotel = hotel_data['hotel'][0]['hotelBasicInfo']
                # 料金情報があるかチェック
                charge_info = hotel_data['hotel'][1].get('hotelRatingInfo')

                hotels.append({
                    "name": hotel.get('hotelName'),
                    "hotelImageUrl": hotel.get('hotelImageUrl'),
                    "planListUrl": hotel.get('planListUrl'),
                    "reviewAverage": hotel.get('reviewAverage'),
                    # 料金、なければNone
                    "charge": charge_info.get('salesPrice') if charge_info else None
                })
        return hotels
    except requests.exceptions.RequestException as e:
        print(f"楽天APIリクエストエラー: {e}")
        return []

# APIエンドポイントを定義


@app.route("/api/travel-plan", methods=["POST"])
def create_travel_plan():
    # フロントエンドから送られてきたJSONデータを取得
    data = request.get_json()
    # ユーザーからの旅行に関する要望テキスト
    user_prompt = data.get("prompt")

    # 入力内容がエラーの場合はエラーを返す
    if not user_prompt:
        return jsonify({"error": "リクエスト内容が空です。"}), 400

    try:
        # --- ステップ1: AIにプランの骨子を作成させる ---
        # Gemini 2.5 Proモデルを使用
        model = genai.GenerativeModel('gemini-2.5-pro')

        # Geminiへの指示（プロンプト）を作成
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
        # AIに指示を送りプランを作成させる
        response = model.generate_content(prompt_for_ai)

        # AIからの返答テキストからJSON部分だけを正規表現で抽出
        # re.search()は文字列の中からパターンに一致する最初の部分を見つけ出す命令
        # '{'で始まり'}'で終わる、改行を含むあらゆる文字列(.*)にマッチさせる
        match = re.search(r'\{.*\}', response.text, re.DOTALL)
        if not match:
            raise ValueError("AIの応答からJSONデータを抽出できませんでした。")

        plan_data = json.loads(match.group(0))

        # --- ステップ2: プラン内容を元にGoogle Mapsで情報補強 ---
        # plan_data['itinerary']の各要素をループ処理
        for item in plan_data.get('itinerary', []):
            # 旅程項目で登場した場所のリスト
            locations_in_item = []

            # descriptionsから「○○」という場所名を探す
            found_names = re.findall(r'「(.*?)」', item['description'])

            # 見つかった場所名でGoogle Mapで情報補強
            for loc_name in found_names:
                # Places APIで場所を検索
                places_result = gmaps.places(
                    query=loc_name,
                    language='ja',
                    # fields=['name', 'formatted_address', 'rating', 'geometry', 'photos']
                )

                # 検索結果があればdescriptionを具体的な場所に置き換える
                if places_result.get('status') == 'OK' and places_result.get('results'):
                    place = places_result['results'][0]  # とりあえず最初の1件を取得

                    # 写真URLを格納する空のリストを準備
                    photo_urls = []
                    # もし写真情報があればループ処理を開始する
                    for photo in place.get('photos', []):
                        photo_ref = photo['photo_reference']
                        photo_url = f"https://maps.googleapis.com/maps/api/place/photo?maxwidth=400&photoreference={photo_ref}&key={os.getenv('GOOGLE_MAPS_API_KEY')}"
                        photo_urls.append(photo_url)
                        # とりあえず2枚目まで取得する
                        if len(photo_urls) >= 2:
                            break

                    # 経度・緯度を取得
                    lat = place['geometry']['location']['lat']
                    lng = place['geometry']['location']['lng']

                    # 必要な情報を辞書としてまとめる
                    location_detail = {
                        'name': place.get('name'),
                        'address': place.get('formatted_address'),
                        'rating': place.get('rating', '評価なし'),
                        'lat': lat,
                        'lng': lng,
                        'photo_urls': photo_urls
                    }
                    locations_in_item.append(location_detail)

            # 旅程項目に補強した場所情報のリストを追加
            item['locations'] = locations_in_item

        # --- ステップ3: 楽天APIでホテル情報を取得 ---
        # 旅行プランのタイトルから地名らしきものを抽出する
        search_keyword = None  # デフォルト値
        # タイトルから「」で囲まれた地名を探す
        match_location = re.search(r'「(.*?)」', plan_data.get('title', ''))
        if match_location:
            # 「・」が含まれていたらその前の部分だけを使う
            search_keyword = match_location.group(1).split('・')[0]
        # もしタイトルから地名が見つからなければ、最初の目的地を使う
        if not search_keyword and plan_data.get('itinerary') and plan_data['itinerary'][0].get('locations'):
            search_keyword = plan_data['itinerary'][0]['locations'][0]['name']

        # 楽天APIでホテルを検索
        hotel_suggestions = []
        if search_keyword:
            hotel_suggestions = search_rakuten_hotels(search_keyword)
            
        plan_data['hotel_suggestions'] = hotel_suggestions

        # --- ステップ4: フロントエンドに完成版プランを返す ---
        return jsonify(plan_data)

    except Exception as e:
        # エラーハンドリング
        print(f"エラーが発生しました: {e}")
        return jsonify({"error": "プランの生成に失敗しました"}), 500

# 動作確認用のページ


@app.route('/')
def index():
    return "旅のAIコンシェルジュ　APIサーバー"


# サーバーを起動
if __name__ == '__main__':
    app.run(debug=True, port=5001)
