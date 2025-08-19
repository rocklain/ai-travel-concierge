import { useState } from 'react';
import './App.css';
import MapComponent from './components/MapComponent.tsx';

// --- TypeScriptの型定義 ---
type LocationDetail = {
  name: string;
  address: string;
  rating: number | string;
  lat: number;
  lng: number;
  photo_urls: (string | null)[];
};
type ItineraryItem = {
  day: number;
  title: string;
  description: string;
  locations: LocationDetail[];
};
type TravelPlan = {
  title: string;
  summary: string;
  itinerary: ItineraryItem[];
};


function App() {
  const [prompt, setPrompt] = useState('');
  const [plan, setPlan] = useState<TravelPlan | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError('');
    setPlan(null);

    try {
      const response = await fetch('http://127.0.0.1:5001/api/travel-plan', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt }),
      });

      if (!response.ok) {
        throw new Error('APIリクエストに失敗しました');
      }

      const data: TravelPlan = await response.json();
      setPlan(data);

    } catch (err) {
      setError('プランの生成に失敗しました。');
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="container">
      <div className="header">
        <h1>旅のAIコンシェルジュ ✈️</h1>
        <p>あなたの「したい」を伝えるだけで、AIが旅行プランを提案します。</p>
      </div>

      <form className="prompt-form" onSubmit={handleSubmit}>
        <textarea
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          placeholder="例：10月の連休に、東京から電車で2時間以内の温泉に行きたい..."
        />
        <button type="submit" disabled={isLoading}>
          {isLoading ? 'プランを生成中…' : 'AIにプランを提案してもらう'}
        </button>
      </form>

      {isLoading && <p className="loading">AIが最高のプランを考えています…</p>}
      {error && <p className="error">{error}</p>}

      {/* ★★★ ここから下の「結果表示」ブロックを修正 ★★★ */}
      {plan && (
        <div className="result-container">
          <h2 className="result-title">{plan.title}</h2>
          <p className="result-summary">{plan.summary}</p>
          <hr />
          <h3>旅程</h3>

          {/* --- ここからが大元のループ --- */}
          {/* plan.itineraryの各要素(item)に対して、以下の表示を繰り返す */}
          {Array.isArray(plan.itinerary) && plan.itinerary.map((item, index) => (
            <div key={`${item.day}-${index}`} className="itinerary-item">
              <h4>{item.day}日目: {item.title}</h4>
              <p dangerouslySetInnerHTML={{ __html: item.description.replace(/\n/g, '<br />') }} />

              {/* --- ここからが写真と地図の表示ブロック --- */}
              {/* 各itemにlocationsがあれば、写真と地図を表示する */}
              {Array.isArray(item.locations) && (
                <div>
                  <div className="photo-gallery">
                    {/* 各場所(loc)のphoto_urls配列をループ処理 */}
                    {item.locations.map(loc =>
                      loc.photo_urls.map(url =>
                        url && <img key={url} src={url} alt={loc.name} className="location-photo" />
                      )
                    )}
                  </div>
                  <MapComponent locations={item.locations} />
                </div>
              )}
              {/* --- ここまでが写真と地図の表示ブロック --- */}

            </div>
          ))}
          {/* --- ここまでが大元のループ --- */}

        </div>
      )}
    </div>
  );
}