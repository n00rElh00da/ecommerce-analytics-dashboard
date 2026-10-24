export async function api(path, opts = {}) {
  const res = await fetch('/api' + path, { credentials: 'include', headers: { 'Content-Type': 'application/json' }, ...opts });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    const msg = typeof body.detail === 'string' ? body.detail : res.statusText;
    throw Object.assign(new Error(msg || 'Request failed'), { status: res.status });
  }
  return res.status === 204 ? null : res.json();
}
export const qs = (o) => new URLSearchParams(Object.entries(o).filter(([, v]) => v)).toString();
