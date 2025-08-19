import { APIProvider, Map, AdvancedMarker } from '@vis.gl/react-google-maps';

// このコンポーネントが受け取るデータ（props）の型定義
type Location = {
    name: string;
    lat: number;
    lng: number;
};
type Props = {
    locations: Location[];
};

const MapComponent = ({ locations }: Props) => {
    // 表示する場所がない場合は何も表示しない
    if (!locations || locations.length === 0) {
        return null;
    }

    // 地図の中心を最初の場所の緯度・経度に設定
    const position = { lat: locations[0].lat, lng: locations[0].lng };

    return (
        // Google Maps APIのプロバイダー。APIキーをここで指定します。
        <APIProvider apiKey={import.meta.env.VITE_GOOGLE_MAPS_API_KEY}>
            <div style={{ height: '400px', width: '100%', marginTop: '1rem', borderRadius: '8px', overflow: 'hidden' }}>
                <Map
                    defaultCenter={position}
                    defaultZoom={14}
                    mapId="TRAVEL_CONCIERGE_MAP"
                >
                    {/* locationsの配列をループして場所ごとにマーカーを設置 */}
                    {locations.map((loc) => (
                        <AdvancedMarker
                            key={loc.name}
                            position={{ lat: loc.lat, lng: loc.lng }}
                            title={loc.name}
                        />
                    ))}
                </Map>
            </div>
        </APIProvider>
    )
}

export default MapComponent;