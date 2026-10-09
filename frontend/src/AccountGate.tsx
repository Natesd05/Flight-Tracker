import { useEffect, useState, type ReactNode } from 'react';
import { api } from './api';

export function AccountGate({children}: {children: (email: string, logout: () => Promise<void>) => ReactNode}) {
  const [user, setUser] = useState<{email: string} | null>(null);
  const [loading, setLoading] = useState(true);
  const [signup, setSignup] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  useEffect(() => { api<{email: string}>('/auth/me').then(setUser).catch(() => {}).finally(() => setLoading(false)); }, []);
  if (loading) return <main className="auth-page">Loading your account…</main>;
  if (user) return children(user.email, async () => { await api('/auth/logout', 'POST'); setUser(null); setSignup(false); setPassword(''); });
  return <main className="auth-page"><form className="panel auth-card" onSubmit={async (e) => {
    e.preventDefault(); setBusy(true); setError('');
    try { setUser(await api('/auth/' + (signup ? 'signup' : 'login'), 'POST', {email, password})); setPassword(''); }
    catch (e) { setError((e as Error).message); } finally { setBusy(false); }
  }}><span className="eyebrow">FLIGHTPLANNER</span><h1>{signup ? 'Create your account' : 'Welcome back'}</h1>
    <p>Keep your classes, preferences, and saved flights together, every time you log in.</p>
    <label>Email<input type="email" autoComplete="username" required maxLength={254} value={email} onChange={e => setEmail(e.target.value)} /></label>
    <label>Password<input type="password" autoComplete={signup ? 'new-password' : 'current-password'} required minLength={12} maxLength={128} value={password} onChange={e => setPassword(e.target.value)} /></label>
    <small>Use at least 12 characters.</small>
    {error && <p role="alert">{error}</p>}
    <button className="button primary" disabled={busy}>{busy ? 'Please wait…' : signup ? 'Sign up' : 'Log in'}</button>
    <button type="button" className="button secondary" disabled={busy} onClick={() => {setSignup(!signup); setError('');}}>{signup ? 'Already have an account? Log in' : 'New here? Sign up'}</button>
  </form></main>;
}
