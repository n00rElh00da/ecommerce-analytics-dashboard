import { useEffect, useRef, useState } from 'react';
import { api } from './api';
import { initMotion } from './motion.jsx';
import Admin from './Admin.jsx';
import Customer from './Customer.jsx';

const GOOGLE_CLIENT_ID = (import.meta.env.VITE_GOOGLE_CLIENT_ID || '').trim();

function GoogleButton({ onLogin, onError }) {
  const ref = useRef();
  useEffect(() => {
    if (!GOOGLE_CLIENT_ID) {
      onError('Google Sign-In is not configured. Set VITE_GOOGLE_CLIENT_ID in frontend/.env, then restart Vite.');
      return undefined;
    }
    const timer = setInterval(() => {
      if (!window.google) return;
      clearInterval(timer);
      window.google.accounts.id.initialize({
        client_id: GOOGLE_CLIENT_ID,
        callback: async (r) => {
          try { onLogin(await api('/auth/google', { method: 'POST', body: JSON.stringify({ credential: r.credential }) })); }
          catch (e) { onError(e.message); }
        },
      });
      window.google.accounts.id.renderButton(ref.current, { theme: 'outline', size: 'large', text: 'signin_with' });
    }, 100);
    return () => clearInterval(timer);
  }, [onError, onLogin]);
  return <div ref={ref} />;
}

function Landing({ onLogin }) {
  const [err, setErr] = useState(null);
  return (
    <main className="hero">
      <h1>What shoppers looked at, carted, and bought</h1>
      <p>Behavioural analytics for one October 2019 sample from a multi-category online store. Sign in to explore it.</p>
      <GoogleButton onLogin={onLogin} onError={setErr} />
      {err && <p role="alert" className="error">{err}</p>}
    </main>
  );
}

export default function App() {
  const [me, setMe] = useState(undefined);
  useEffect(() => initMotion(), []);
  useEffect(() => { api('/auth/me').then(setMe).catch(() => setMe(null)); }, []);
  if (me === undefined) return <p className="center" role="status">Loading…</p>;
  if (!me) return <Landing onLogin={setMe} />;
  const signOut = async () => { await api('/auth/logout', { method: 'POST' }); setMe(null); };
  return (
    <>
      <header className="bar">
        <strong>Shopper Signals</strong>
        <span>{me.name} ({me.role})</span>
        <button className="ghost" onClick={signOut}>Sign out</button>
      </header>
      {me.role === 'admin' ? <Admin /> : <Customer />}
    </>
  );
}
