import os
import json
import re
from flask import Flask, request, jsonify
from dotenv import load_dotenv
import google.generativeai as genai
from flask_cors import CORS

# .envから環境変数を読み込む
load_dotenv()

# Flaskアプリのセットアップ
app = Flask(__name__)
# CORSを有効にしフロントエンドからのアクセスを許可
CORS(app)

# Gemini APIキーを設定
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

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

    try:
        # AIに指示を送りプランを作成させる
        response = model.generate_content(prompt_for_ai)

        # AIが実際に返したデータをターミナルで確認
        print("--- AIからの返答 ---")
        print(response.text)
        print("-------------------")

        # AIからの返答テキストからJSON部分だけを正規表現で抽出
        # re.search()は文字列の中からパターンに一致する最初の部分を見つけ出す命令
        # '{'で始まり'}'で終わる、改行を含むあらゆる文字列(.*)にマッチさせる
        match = re.search(r'\{.*\}', response.text, re.DOTALL)
        
        # JSON部分が見つかった場合のみ処理を続ける
        if match:
            json_text = match.group(0)
            plan_data = json.loads(json_text)
            return jsonify(plan_data)
        else:
            # JSON部分が見つからなかった場合はエラーを返す
            raise ValueError("AIの応答からJSONデータを抽出できませんでした。")

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
