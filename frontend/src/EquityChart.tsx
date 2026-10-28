import { useEffect, useRef } from 'react';
import { createChart, ColorType, LineSeries, type UTCTimestamp } from 'lightweight-charts';
import type { Json } from './api';
export default function EquityChart({points}: {points: Json[]}) {
  const host = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!host.current || !points.length) return;
    const chart = createChart(host.current, {height: 280, autoSize: true, layout: {background: {type: ColorType.Solid, color: '#1a1c23'}, textColor: '#9299a8'}, grid: {vertLines: {color: '#252932'}, horzLines: {color: '#252932'}}, timeScale: {timeVisible: true}});
    const equity = chart.addSeries(LineSeries, {color: '#69cbb0', lineWidth: 2, title: 'Equity'});
    const balance = chart.addSeries(LineSeries, {color: '#8795d4', lineWidth: 1, title: 'Balance'});
    const unique = [...new Map(points.map(p => [Math.floor(Date.parse(p.t) / 1000), p])).entries()].sort((a,b) => a[0]-b[0]);
    equity.setData(unique.map(([t,p]) => ({time: t as UTCTimestamp, value: p.equity})));
    balance.setData(unique.map(([t,p]) => ({time: t as UTCTimestamp, value: p.balance})));
    chart.timeScale().fitContent();
    return () => chart.remove();
  }, [points]);
  return points.length ? <div ref={host} aria-label="Recorded account equity and balance chart"/> : <div className="empty chart-empty"><span className="chart-mark">⌁</span><strong>No account observations yet</strong><p>The equity curve will appear after the executor records broker snapshots.</p></div>;
}
