import { useEffect, useRef, useState } from 'react';
import { api, qs } from './api';
import { useReveal } from './motion.jsx';

export default function Customer() {
  const [me, setMe] = useState(null);
  const [favs, setFavs] = useState([]);
  const [items, setItems] = useState([]);
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);
  const [err, setErr] = useState(null);
  const [loading, setLoading] = useState(true);
  const root = useRef();
  useReveal(root, me);

  const loadFavs = () => api('/customer/favorites').then(setFavs).catch(setErr);
  useEffect(() => { api('/customer/me').then(setMe).catch(setErr); loadFavs(); }, []);
  useEffect(() => {
    let live = true;
    setLoading(true);
    api('/customer/products?' + qs({ search, page }))
      .then((r) => live && setItems(r)).catch((e) => live && setErr(e)).finally(() => live && setLoading(false));
    return () => { live = false; };
  }, [search, page]);

  const isFav = (id) => favs.some((f) => f.product_id === id);
  const toggle = async (id) => {
    try {
      if (isFav(id)) await api(`/customer/favorites/${id}`, { method: 'DELETE' });
      else await api('/customer/favorites', { method: 'POST', body: JSON.stringify({ product_id: id }) });
      await loadFavs(); setMe(await api('/customer/me'));
    } catch (e) { setErr(e); }
  };

  return (
    <main ref={root} className="wrap">
      <h1>Your account</h1>
      {err && <p role="alert" className="error">{err.message}</p>}
      {me && (
        <section className="card profile" data-reveal>
          {me.picture && <img src={me.picture} alt="" width="56" height="56" referrerPolicy="no-referrer" />}
          <div><strong>{me.name}</strong><br />{me.email}<br /><span className="muted">{me.favorites_count} favorite products</span></div>
        </section>
      )}
      <section className="card" data-reveal>
        <h2>Order history</h2>
        <p className="muted">No orders created in this app yet. {me?.historical_history_note}</p>
      </section>
      <section className="card" data-reveal>
        <h2>Favorite products</h2>
        {favs.length === 0 ? <p className="muted">Nothing saved yet. Use “Favorite” on any product below.</p> : (
          <ul className="list">{favs.map((p) => (
            <li key={p.product_id}><span>Product {p.product_id} · {p.brand || 'unknown brand'} · {p.category || 'uncategorised'}</span>
              <button className="ghost" onClick={() => toggle(p.product_id)}>Remove</button></li>))}</ul>)}
      </section>
      <section className="card" data-reveal>
        <h2>Discover products</h2>
        <label className="search">Search by brand or category
          <input value={search} onChange={(e) => { setPage(1); setSearch(e.target.value); }} placeholder="e.g. samsung or smartphone" /></label>
        {loading && <p role="status" className="muted">Loading products…</p>}
        {!loading && items.length === 0 && <p className="muted">No products match that search.</p>}
        <ul className="list">{items.map((p) => (
          <li key={p.product_id}>
            <span>Product {p.product_id} · {p.brand || 'unknown brand'} · {p.category || 'uncategorised'}{p.avg_price ? ` · about $${p.avg_price}` : ''} · {p.views} views</span>
            <button className={isFav(p.product_id) ? 'ghost' : ''} onClick={() => toggle(p.product_id)} aria-pressed={isFav(p.product_id)}>{isFav(p.product_id) ? 'Unfavorite' : 'Favorite'}</button>
          </li>))}</ul>
        <div className="pager">
          <button className="ghost" disabled={page === 1} onClick={() => setPage(page - 1)}>Previous</button>
          <span>Page {page}</span>
          <button className="ghost" disabled={items.length < 12} onClick={() => setPage(page + 1)}>Next</button>
        </div>
      </section>
    </main>
  );
}
