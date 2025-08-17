import { useState } from "react";
import './App.css';

// TypeScriptの型定義: AIが返す旅行プランデータの型
type ItineraryItem = {
  day: number;
  title: string;
  description: string;
};
type TravelPlan = {
  title: string;
  summary: string;
  itinerary: ItineraryItem[];
};

function App() {
  // -- State(コンポーネントが持つ状態)の定義 --
  // ユーザーが入力した要望テキスト
  const [prompt, setPrompt] = useState('');
  // AIから返ってきた旅行プラン
  const [plan, setPlan] = useState<TravelPlan | null>(null);
  // 通信中かどうかの状態（ローディング表示用）
  const [isLoading, setIsLoading] = useState(false);
  // エラーメッセージ
  const [error, setError] = useState('');

  // -- 関数の定義 --
  // フォームが送信されたときに実行される関数
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault(); // フォーム送信時のページリロードを防止
    setIsLoading(true); // ローディング開始
    setError('');
    setPlan(null);

    try {
      // バックエンドAPIにPOSTリクエストを送信
      const response = await fetch('http://127.0.0.1:5001/api/travel-plan', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt }), // ユーザーの入力をJSONにして送信
      });

      if (!response.ok) {
        throw new Error('APIリクエストに失敗しました');
      }

      const data: TravelPlan = await response.json();
      setPlan(data); // 受け取ったプランをStateに保存

    } catch (err) {
      setError('プランの生成に失敗しました');
      console.error(err); 
    } finally {
      setIsLoading(false); // ローディング終了
    }
  };

  // -- 表示内容（JSX）の定義
  return (
    <div className="container">
      <div className="header">
        <h1>旅のAIコンシェルジュ ✈</h1>
        <p>あなたの「したい」を伝えるだけで、AIが旅行プランを提案します。</p>
      </div>
      {/* 入力フォーム */}
      <form className="prompt-form" onSubmit={handleSubmit}>
        <textarea
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          placeholder="例:10月の連休に、東京から電車で2時間以内の温泉に行きたい。カップル2人で、予算は1人4万円。静かで落ち着いた雰囲気の旅館がいい。"
        />
        <button type="submit" disabled={isLoading}>
          {isLoading ? 'プランを生成中…' : 'AIにプランを提案してもらう'}
        </button>
      </form>

      {/* ローディング表示 */}
      {isLoading && <p className="loading">AIが最高のプランを考えています…</p>}

      {/* エラー表示 */}
      {error && <p className="error">{error}</p>}

      {/* 結果表示 */}
      {plan && (
        <div className="result-container">
          <h2 className="result-title">{plan.title}</h2>
          <p className="result-summary">{plan.summary}</p>
          <hr />
          <h3>旅程</h3>
          {plan.itinerary.map((item) => (
            <div key={item.day} className="itinerary-item">
              <h4>{item.day}: {item.title}</h4>
              <p>{item.description}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default App;