import os
import json
import re
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
        - 必ずJSON形式で出力してください。
        - JSONのキーは "title", "summary", "itinerary" としてください。
        - "title": 旅行プランのタイトル (例: 「海の幸と絶景温泉を巡る伊豆週末旅行」)
        - "summary": 2-3行の魅力的な概要説明文
        - "itinerary": 旅程の配列。各要素は "day", "title", "description" をキーに持つオブジェクト。

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
        for item in plan_data.get('itinerary',[]):
            # 旅程項目で登場した場所のリスト
            locations_in_item = []
            
            # descriptionsから「○○」という場所名を探す
            found_names = re.findall(r'「(.*?)」', item['description'])

            # 見つからなかった場所名でGoogle Mapで情報補強
            for loc_name in found_names:
                # Places APIで場所を検索
                places_result = gmaps.places(query=loc_name, language='ja')

                # 検索結果があればdescriptionを具体的な場所に置き換える
                if places_result.get('status') == 'OK' and places_result['results']:
                    place = places_result['results'][0]  # とりあえず最初の1件を取得
                    
                    # 写真URLを格納する空のリストを準備
                    photo_urls = []
                    # もし写真情報があればループ処理を開始する
                    for photo in place.get('photos',[]):
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
                        'rating': place.get('rating','評価なし'),
                        'lat': lat,
                        'lng': lng,
                        'photo_urls': photo_urls 
                    }
                    locations_in_item.append(location_detail)
                    
                    # 旅程項目に補強した場所情報のリストを追加
                    item['locations'] = locations_in_item
                    
            # --- ステップ3: フロントエンドに完成版プランを返す ---
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
