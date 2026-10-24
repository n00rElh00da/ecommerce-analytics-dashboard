import { useEffect, useRef } from 'react';
import gsap from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';
import Lenis from 'lenis';

gsap.registerPlugin(ScrollTrigger);
export const reduced = () => window.matchMedia('(prefers-reduced-motion: reduce)').matches;

// Lenis driven by the GSAP ticker, with ScrollTrigger updated on every Lenis scroll.
export function initMotion() {
  if (reduced()) return () => {};
  const lenis = new Lenis();
  lenis.on('scroll', ScrollTrigger.update);
  const tick = (t) => lenis.raf(t * 1000);
  gsap.ticker.add(tick);
  gsap.ticker.lagSmoothing(0);
  return () => { gsap.ticker.remove(tick); lenis.destroy(); };
}

// Reveals elements marked data-reveal as they scroll into view; reverted on cleanup.
export function useReveal(ref, dep) {
  useEffect(() => {
    if (reduced() || !ref.current) return;
    const ctx = gsap.context(() => {
      gsap.utils.toArray('[data-reveal]').forEach((n) =>
        gsap.from(n, { opacity: 0, y: 20, duration: 0.5, scrollTrigger: { trigger: n, start: 'top 90%', once: true } }));
    }, ref);
    return () => ctx.revert();
  }, [dep]);
}

export function CountUp({ value, decimals = 0, prefix = '' }) {
  const ref = useRef();
  useEffect(() => {
    const el = ref.current;
    const fmt = (v) => prefix + v.toLocaleString(undefined, { minimumFractionDigits: decimals, maximumFractionDigits: decimals });
    if (reduced()) { el.textContent = fmt(value); return; }
    const o = { v: 0 };
    const tw = gsap.to(o, { v: value, duration: 1, ease: 'power2.out', onUpdate: () => { el.textContent = fmt(o.v); } });
    return () => tw.kill();
  }, [value]);
  return <span ref={ref}>{prefix}0</span>;
}
