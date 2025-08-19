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

// ホテルの型
type HotelSuggestion = {
  name: string;
  hotelImageUrl: string;
  planListUrl: string;
  reviewAverage: string;
  charge: number | null;
}

// 旅行計画の型
type TravelPlan = {
  title: string;
  summary: string;
  itinerary: ItineraryItem[];
  hotel_suggestions: HotelSuggestion[];
};


function App() {
  const [prompt, setPrompt] = useState('');
  const [checkinDate, setCheckinDate] = useState('')
  const [checkoutDate, setCheckoutDate] = useState('')

  const [plan, setPlan] = useState<TravelPlan | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!checkinDate || !checkoutDate) {
      setError('チェックイン日とチェックアウト日を入力してください。');
      return;
    }
    setIsLoading(true);
    setError('');
    setPlan(null);

    try {
      const response = await fetch('http://127.0.0.1:5001/api/travel-plan', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          prompt,
          checkinDate,
          checkoutDate
        }),
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
        {/* 日付入力フォーム */}
        <div className="date-picker-wrapper">
          <div className="date-input-group">
            <label htmlFor="checkin">チェックイン</label>
            <input id="checkin" type="date" value={checkinDate} onChange={e => setCheckinDate(e.target.value)} />
          </div>
          <div className="date-input-group">
            <label htmlFor="checkout">チェックアウト</label>
            <input id="checkout" type="date" value={checkoutDate} onChange={e => setCheckoutDate(e.target.value)} />
          </div>
        </div>

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

      {plan && (
        <div className="result-container">
          <h2 className="result-title">{plan.title}</h2>
          <p className="result-summary">{plan.summary}</p>
          <hr />
          <h3>旅程</h3>

          {Array.isArray(plan.itinerary) && plan.itinerary.map((item, index) => (
            <div key={`${item.day}-${index}`} className="itinerary-item">
              <h4>{item.day}日目: {item.title}</h4>
              <p dangerouslySetInnerHTML={{ __html: item.description.replace(/\n/g, '<br />') }} />

              {Array.isArray(item.locations) && (
                <div>
                  <div className="photo-gallery">
                    {item.locations.map(loc =>
                      loc.photo_urls.map(url =>
                        url && <img key={url} src={url} alt={loc.name} className="location-photo" />
                      )
                    )}
                  </div>
                  <MapComponent locations={item.locations} />
                </div>
              )}
            </div>
          ))}

          {Array.isArray(plan.hotel_suggestions) && plan.hotel_suggestions.length > 0 && (
            <div className="hotel-container">
              <hr />
              <h3>🏨 おすすめの宿泊先</h3>
              {plan.hotel_suggestions.map(hotel => (
                <div key={hotel.name} className="hotel-card">
                  <img src={hotel.hotelImageUrl} alt={hotel.name} className="hotel-photo" />
                  <div className="hotel-info">
                    <div className="hotel-name">{hotel.name}</div>
                    <div className="hotel-rating">評価: {hotel.reviewAverage}</div>
                  </div>
                  <div className="hotel-booking">
                    <div className="hotel-price">
                      {hotel.charge ? `￥${hotel.charge.toLocaleString()}～/人` : '料金要確認'}
                    </div>
                    <a href={hotel.planListUrl} target="_blank" rel="noopener noreferrer" className="booking-button">
                      予約サイトへ
                    </a>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default App;