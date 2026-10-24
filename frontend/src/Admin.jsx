import { useEffect, useRef, useState } from 'react';
import { Bar, BarChart, CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { api, qs } from './api';
import { CountUp, useReveal } from './motion.jsx';

const VIOLET = ['#5b21b6', '#8b5cf6', '#c4b5fd'];
const fmtTime = (s) => (s ? s.replace('T', ' ').slice(0, 16) + ' UTC' : '—');

function Chart({ title, children, note }) {
  return (
    <section className="card" data-reveal>
      <h2>{title}</h2>
      <div className="chart"><ResponsiveContainer width="100%" height="100%">{children}</ResponsiveContainer></div>
      {note && <p className="muted">{note}</p>}
    </section>
  );
}

const Table = ({ rows, cols }) => (
  <div className="scroll"><table>
    <thead><tr>{cols.map(([h]) => <th key={h}>{h}</th>)}</tr></thead>
    <tbody>{rows.map((r, i) => <tr key={i}>{cols.map(([h, k]) => <td key={h}>{r[k] ?? '—'}</td>)}</tr>)}</tbody>
  </table></div>
);

export default function Admin() {
  const [f, setF] = useState({ bucket: 'hour' });
  const [opts, setOpts] = useState({ categories: [], brands: [] });
  const [d, setD] = useState(null);
  const [err, setErr] = useState(null);
  const [loading, setLoading] = useState(true);
  const root = useRef();
  useReveal(root, d);

  useEffect(() => { api('/admin/options').then(setOpts).catch(setErr); }, []);
  useEffect(() => {
    let live = true;
    setLoading(true); setErr(null);
    const q = qs(f), g = (p) => api(`/admin/${p}?${q}`);
    Promise.all(['overview', 'sales', 'products/top', 'products/underperforming', 'categories', 'brands', 'funnel', 'customers/summary'].map(g))
      .then(([overview, sales, top, under, cats, brands, funnel, cust]) => live && setD({ overview, sales, top, under, cats, brands, funnel, cust }))
      .catch((e) => live && setErr(e))
      .finally(() => live && setLoading(false));
    return () => { live = false; };
  }, [f]);

  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });
  const o = d?.overview;
  const kpis = o && [
    ['Total events', o.total_events], ['Product views', o.views], ['Cart additions', o.cart_additions],
    ['Cart removals', o.cart_removals], ['Purchase events', o.purchase_events], ['Active users', o.distinct_active_users],
    ['Purchasing users', o.distinct_purchasing_users], ['Estimated gross purchase value', o.estimated_gross_purchase_value, 2, '$'],
  ];

  return (
    <main ref={root} className="wrap">
      <h1>Admin dashboard</h1>
      <p className="muted">
        {o?.period ? `Reporting period in imported data: ${fmtTime(o.period.first_event)} to ${fmtTime(o.period.last_event)}.` : 'Reporting period: no events match the filters.'}
        {' '}Counts are events, not unique orders.
      </p>
      <form className="filters card" onSubmit={(e) => e.preventDefault()} aria-label="Filters">
        <label>From (UTC)<input type="datetime-local" value={f.date_from || ''} onChange={set('date_from')} /></label>
        <label>To (UTC)<input type="datetime-local" value={f.date_to || ''} onChange={set('date_to')} /></label>
        <label>Category<select value={f.category || ''} onChange={set('category')}><option value="">All</option>{opts.categories.map((c) => <option key={c}>{c}</option>)}</select></label>
        <label>Brand<select value={f.brand || ''} onChange={set('brand')}><option value="">All</option>{opts.brands.map((c) => <option key={c}>{c}</option>)}</select></label>
        <label>Event type<select value={f.event_type || ''} onChange={set('event_type')}><option value="">All</option>{['view', 'cart', 'purchase'].map((c) => <option key={c}>{c}</option>)}</select></label>
        <label>Time bucket<select value={f.bucket} onChange={set('bucket')}><option value="hour">Hour</option><option value="day">Day</option></select></label>
        <button type="button" className="ghost" onClick={() => setF({ bucket: 'hour' })}>Reset</button>
      </form>

      {err && <p role="alert" className="error">Could not load analytics: {err.message}</p>}
      {loading && <p role="status" className="muted">Loading analytics…</p>}
      {d && (
        <div className={loading ? 'dim' : ''}>
          <div className="kpis">{kpis.map(([label, v, dec, pre]) => (
            <div className="card kpi" key={label}><span className="muted">{label}</span><strong><CountUp value={v} decimals={dec} prefix={pre} /></strong></div>))}
          </div>
          <p className="muted">Gross value: {o.gross_purchase_value_definition}{o.cart_removals === 0 && ' No cart-removal events exist in this sample.'}</p>
          <div className="grid">
            <Chart title="Activity over time (UTC)">
              <LineChart data={d.sales}><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="name" /><YAxis /><Tooltip /><Legend />
                <Line dataKey="views" stroke={VIOLET[2]} /><Line dataKey="carts" stroke={VIOLET[1]} /><Line dataKey="purchases" stroke={VIOLET[0]} strokeWidth={2} /></LineChart>
            </Chart>
            <Chart title="Shopping funnel" note="Distinct users who did each action at least once; not a strict sequence.">
              <BarChart data={d.funnel} layout="vertical"><CartesianGrid strokeDasharray="3 3" /><XAxis type="number" /><YAxis type="category" dataKey="stage" width={100} /><Tooltip /><Bar dataKey="users" fill={VIOLET[0]} /></BarChart>
            </Chart>
            <Chart title="Top categories by purchase events">
              <BarChart data={d.cats} layout="vertical"><CartesianGrid strokeDasharray="3 3" /><XAxis type="number" /><YAxis type="category" dataKey="name" width={150} /><Tooltip /><Bar dataKey="purchases" fill={VIOLET[0]} /></BarChart>
            </Chart>
            <Chart title="Brand performance">
              <BarChart data={d.brands} layout="vertical"><CartesianGrid strokeDasharray="3 3" /><XAxis type="number" /><YAxis type="category" dataKey="name" width={110} /><Tooltip /><Legend /><Bar dataKey="views" fill={VIOLET[2]} /><Bar dataKey="purchases" fill={VIOLET[0]} /></BarChart>
            </Chart>
          </div>
          <section className="card" data-reveal><h2>Top products by purchase events</h2>
            <Table rows={d.top} cols={[['Product ID', 'product_id'], ['Brand', 'brand'], ['Category', 'category'], ['Views', 'views'], ['Carts', 'carts'], ['Purchases', 'purchases']]} /></section>
          <section className="card" data-reveal><h2>High views, few purchase events</h2>
            <p className="muted">Products with at least 5 views, lowest purchase-to-view ratio first.</p>
            <Table rows={d.under.map((r) => ({ ...r, purchase_rate: (r.purchase_rate * 100).toFixed(1) + '%' }))} cols={[['Product ID', 'product_id'], ['Brand', 'brand'], ['Views', 'views'], ['Purchases', 'purchases'], ['Rate', 'purchase_rate']]} /></section>
          <section className="card" data-reveal><h2>Repeat purchasing</h2>
            <p><strong>{d.cust.repeat_purchasing_users}</strong> of <strong>{d.cust.purchasing_users}</strong> purchasing users bought in 2+ sessions.</p>
            <p className="muted">{d.cust.definition}</p></section>
          <section className="card" data-reveal><h2>Data quality</h2>
            <p>{o.data_quality.missing_brand ?? 0} events without a brand, {o.data_quality.missing_category ?? 0} without a category, and {o.data_quality.zero_price ?? 0} with a price of 0, out of {o.data_quality.total ?? 0} events matching the filters.</p></section>
        </div>
      )}
    </main>
  );
}
