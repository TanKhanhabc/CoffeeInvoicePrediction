import { useEffect, useState } from 'react'
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { api, type HistoryRow, type Overview } from './api'

const shifts = ['Night', 'Morning', 'Afternoon', 'Evening']
const today = new Date().toISOString().slice(0, 10)

export default function App() {
  const [overview, setOverview] = useState<Overview | null>(null)
  const [history, setHistory] = useState<HistoryRow[]>([])
  const [date, setDate] = useState(today)
  const [shift, setShift] = useState('Morning')
  const [holiday, setHoliday] = useState(false)
  const [prediction, setPrediction] = useState<number | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  async function loadDashboard() {
    try {
      const [o, h] = await Promise.all([api.get('/api/overview'), api.get('/api/history?limit=30')])
      setOverview(o.data)
      setHistory(h.data)
      setError('')
    } catch {
      setError('Không kết nối được Backend. Hãy chạy FastAPI tại http://127.0.0.1:8000.')
    }
  }
  useEffect(() => { void loadDashboard() }, [])

  async function runPrediction(e: React.FormEvent) {
    e.preventDefault()
    setBusy(true); setError(''); setPrediction(null)
    try {
      const res = await api.post('/api/predict', { date, shift, is_holiday: holiday })
      setPrediction(res.data.predicted_invoice_count)
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Dự đoán thất bại. Kiểm tra Backend và dữ liệu.')
    } finally { setBusy(false) }
  }

  const chartData = [...history].reverse().slice(-14).map((r) => ({
    label: `${r.date.slice(5)} ${r.shift.slice(0, 3)}`, invoices: r.invoice_count
  }))

  return <main className="page">
    <header className="hero">
      <div><p className="eyebrow">MACHINE LEARNING PROJECT</p><h1>Coffee Invoice Forecast</h1>
      <p className="subtitle">Dự đoán số lượng hóa đơn theo ngày, ca làm và ngày nghỉ.</p></div>
      <div className="hero-mark">☕</div>
    </header>
    {error && <div className="error">{error}</div>}
    <section className="stats">
      <article className="stat"><span>Tổng giao dịch</span><strong>{overview ? overview.transaction_rows.toLocaleString('vi-VN') : '—'}</strong></article>
      <article className="stat"><span>Số cửa hàng</span><strong>{overview?.unique_stores ?? '—'}</strong></article>
      <article className="stat"><span>Bản ghi ngày nghỉ</span><strong>{overview ? overview.holiday_rows.toLocaleString('vi-VN') : '—'}</strong></article>
      <article className="stat"><span>Nhóm ngày / ca</span><strong>{overview ? overview.daily_shift_groups.toLocaleString('vi-VN') : '—'}</strong></article>
    </section>
    <section className="grid">
      <article className="panel prediction">
        <div className="panel-heading"><div><p className="eyebrow">FORECAST</p><h2>Dự đoán số hóa đơn</h2></div><span className="pill">ML baseline</span></div>
        <form onSubmit={runPrediction}>
          <label>Ngày dự đoán<input type="date" value={date} onChange={e => setDate(e.target.value)} required /></label>
          <label>Ca làm<select value={shift} onChange={e => setShift(e.target.value)}>{shifts.map(s => <option key={s}>{s}</option>)}</select></label>
          <label className="toggle-row"><span>Ngày nghỉ / ngày lễ</span><input type="checkbox" checked={holiday} onChange={e => setHoliday(e.target.checked)} /><b>{holiday ? 'true' : 'false'}</b></label>
          <button disabled={busy}>{busy ? 'Đang dự đoán…' : 'Dự đoán'}</button>
        </form>
        {prediction !== null && <div className="result"><span>Số hóa đơn dự đoán</span><strong>{prediction.toLocaleString('vi-VN')}</strong><small>hóa đơn · {shift} · {holiday ? 'Ngày nghỉ' : 'Ngày thường'}</small></div>}
        <p className="hint">Mốc ca: Night 00–05, Morning 06–11, Afternoon 12–16, Evening 17–23.</p>
      </article>
      <article className="panel chart-panel">
        <div className="panel-heading"><div><p className="eyebrow">HISTORY</p><h2>Lịch sử theo ngày / ca</h2></div></div>
        <div className="chart"><ResponsiveContainer width="100%" height="100%"><BarChart data={chartData}><CartesianGrid strokeDasharray="3 3" vertical={false}/><XAxis dataKey="label" tick={{fontSize: 10}} interval="preserveStartEnd"/><YAxis allowDecimals={false}/><Tooltip/><Bar dataKey="invoices" name="Số hóa đơn" radius={[5,5,0,0]}/></BarChart></ResponsiveContainer></div>
        <p className="hint">Biểu đồ hiển thị các nhóm ngày / ca gần nhất trong dữ liệu nguồn.</p>
      </article>
    </section>
    <section className="panel table-panel">
      <div className="panel-heading"><div><p className="eyebrow">DATA</p><h2>Dữ liệu lịch sử gần đây</h2></div><button className="secondary" onClick={() => void loadDashboard()}>Làm mới</button></div>
      <div className="table-wrap"><table><thead><tr><th>Ngày</th><th>Ca làm</th><th>Holiday</th><th>Số hóa đơn</th></tr></thead>
      <tbody>{history.slice(0, 12).map((r, i) => <tr key={`${r.date}-${r.shift}-${i}`}><td>{r.date}</td><td>{r.shift}</td><td><span className={r.is_holiday ? 'badge yes' : 'badge'}>{String(r.is_holiday)}</span></td><td>{r.invoice_count}</td></tr>)}
      {!history.length && <tr><td colSpan={4}>Chưa có dữ liệu. Hãy kiểm tra Backend.</td></tr>}</tbody></table></div>
    </section>
    <footer>Starter project · React + FastAPI + scikit-learn · Chưa tích hợp Docker</footer>
  </main>
}
