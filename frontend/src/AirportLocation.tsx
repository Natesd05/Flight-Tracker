import { useState } from 'react';
import type { Airport } from './types';
import { coordinates } from './airportCoordinates';
export function distanceMiles(lat: number, lon: number, code: string) {
  const point = coordinates[code];
  if (!point) return Infinity;
  const rad = Math.PI / 180;
  const a = Math.sin((point[1]-lat)*rad/2)**2 + Math.cos(lat*rad)*Math.cos(point[1]*rad)*Math.sin((point[0]-lon)*rad/2)**2;
  return 3958.8 * 2 * Math.asin(Math.sqrt(Math.min(1, a)));
}
export function AirportLocation({airports, home, onSelect}: {airports: Airport[]; home: string; onSelect: (code: string) => void}) {
  const [location, setLocation] = useState<{lat: number; lon: number} | null>(null);
  const [message, setMessage] = useState('');
  const [busy, setBusy] = useState(false);
  const nearest = location ? airports.filter(a => coordinates[a.code]).sort((a,b) => distanceMiles(location.lat, location.lon,a.code)-distanceMiles(location.lat,location.lon,b.code))[0] : null;
  return <div className="location-panel"><button type="button" className="button secondary" disabled={busy} onClick={() => {
    if (!navigator.geolocation) {setMessage('Location is unavailable in this browser. Choose your airport above.'); return;}
    setBusy(true); setMessage('');
    navigator.geolocation.getCurrentPosition(p => {setLocation({lat:p.coords.latitude,lon:p.coords.longitude});setBusy(false);}, e => {setMessage(e.code === 1 ? 'Location permission denied. Choose your airport manually, or enable location access and try again.' : 'Could not find your location. Try again or choose your airport manually.');setBusy(false);}, {timeout:15000, maximumAge:300000});
  }}>{busy ? 'Finding location…' : 'Use my location'}</button>
  <p className="helper">Find your distance to your home airport and the nearest major airport in our supported catalog. Your coordinates stay in this browser tab.</p>
  <div aria-live="polite">{message}{location && nearest && <><p>{home}: {Math.round(distanceMiles(location.lat,location.lon,home))} miles from your current location.</p><p>Closest supported major airport: <strong>{nearest.name} ({nearest.code})</strong> · {Math.round(distanceMiles(location.lat,location.lon,nearest.code))} miles.</p>{nearest.code !== home && <button type="button" className="button secondary" onClick={() => onSelect(nearest.code)}>Use {nearest.code} as home airport</button>}<p className="helper">Straight-line distances, not driving distances. Save preferences to keep your airport choice. Set transit time separately.</p></>}</div>
  </div>;
}
