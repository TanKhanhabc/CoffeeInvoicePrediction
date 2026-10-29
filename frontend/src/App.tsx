import { useEffect, useState } from 'react'
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { api, type HistoryRow, type Overview } from './api'

const shifts = ['Night', 'Morning', 'Afternoon', 'Evening']
const today = new Date().toISOString().slice(0, 10)

type ForecastPoint = { label: string; invoices: number; fullDate: string }
type ChatMessage = { role: 'assistant' | 'user'; text: string }
type AppTab = 'overview' | 'forecast'

function createForecast(days: number): ForecastPoint[] {
  const start = new Date()
  start.setHours(12, 0, 0, 0)
  start.setDate(start.getDate() + 1)

  return Array.from({ length: days }, (_, index) => {
    const date = new Date(start)
    date.setDate(start.getDate() + index)
    const weekday = date.getDay()
    const weekendBoost = weekday === 0 || weekday === 6 ? 18 : 0
    const variation = ((index * 17 + 11) % 23) - 11
    const fullDate = date.toLocaleDateString('vi-VN', { day: '2-digit', month: '2-digit' })

    return {
      label: days === 7
        ? date.toLocaleDateString('vi-VN', { weekday: 'short' })
        : date.toLocaleDateString('vi-VN', { day: '2-digit' }),
      invoices: Math.max(12, 58 + weekendBoost + variation + Math.round(index * 0.3)),
      fullDate,
    }
  })
}

export default function App() {
  const [overview, setOverview] = useState<Overview | null>(null)
  const [history, setHistory] = useState<HistoryRow[]>([])
  const [date, setDate] = useState(today)
  const [shift, setShift] = useState('Morning')
  const [holiday, setHoliday] = useState(false)
  const [prediction, setPrediction] = useState<number | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [activeTab, setActiveTab] = useState<AppTab>('overview')
  const [chatOpen, setChatOpen] = useState(false)
  const [chatInput, setChatInput] = useState('')
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([
    { role: 'assistant', text: 'Xin chào! Mình có thể giúp bạn xem nhanh dự báo và gợi ý chuẩn bị cho quán.' },
  ])
  const forecastWeek = createForecast(7)
  const forecastMonth = createForecast(30)

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
    setBusy(true)
    setError('')
    setPrediction(null)
    try {
      const res = await api.post('/api/predict', { date, shift, is_holiday: holiday })
      setPrediction(res.data.predicted_invoice_count)
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Dự đoán thất bại. Kiểm tra Backend và dữ liệu.')
    } finally {
      setBusy(false)
    }
  }

  const chartData = [...history].reverse().slice(-14).map((row) => ({
    label: `${row.date.slice(5)} ${row.shift.slice(0, 3)}`,
    invoices: row.invoice_count,
  }))

  function sendChatMessage(e: React.FormEvent) {
    e.preventDefault()
    const question = chatInput.trim()
    if (!question) return

    const normalizedQuestion = question.toLocaleLowerCase('vi')
    let answer = 'Đây là giao diện demo nên mình chưa kết nối dữ liệu thực. Bạn có thể hỏi về dự báo 7 ngày, dự báo tháng hoặc cách chuẩn bị ca làm.'
    if (normalizedQuestion.includes('7 ngày') || normalizedQuestion.includes('tuần')) {
      const busiestDay = forecastWeek.reduce((busiest, day) => day.invoices > busiest.invoices ? day : busiest)
      answer = `Trong dự báo mô phỏng 7 ngày, ngày ${busiestDay.fullDate} có thể đông nhất với khoảng ${busiestDay.invoices} hóa đơn.`
    } else if (normalizedQuestion.includes('tháng') || normalizedQuestion.includes('30 ngày')) {
      const average = Math.round(forecastMonth.reduce((sum, day) => sum + day.invoices, 0) / forecastMonth.length)
      answer = `Dự báo mô phỏng 30 ngày ước tính trung bình khoảng ${average} hóa đơn mỗi ngày.`
    } else if (normalizedQuestion.includes('nhân viên') || normalizedQuestion.includes('chuẩn bị') || normalizedQuestion.includes('nguyên liệu')) {
      answer = 'Bạn có thể ưu tiên bố trí thêm nhân sự và chuẩn bị nguyên liệu trước các ngày cuối tuần — đây thường là nhóm ngày có lượng khách cao hơn.'
    } else if (normalizedQuestion.includes('xin chào') || normalizedQuestion.includes('hello') || normalizedQuestion.includes('chào')) {
      answer = 'Chào bạn! Bạn muốn xem dự báo tuần hay dự báo tháng?'
    }

    setChatMessages((messages) => [
      ...messages,
      { role: 'user', text: question },
      { role: 'assistant', text: answer },
    ])
    setChatInput('')
  }

  return (
    <main className="page">
      <header className="topbar">
        <a className="brand" href="#" aria-label="Coffee Forecast trang chủ">
          <span className="brand-mark">C</span>
          <span className="brand-name">coffee<span>forecast</span></span>
        </a>
        <nav className="main-nav" aria-label="Điều hướng chính">
          <button
            className={activeTab === 'overview' ? 'nav-tab active' : 'nav-tab'}
            onClick={() => setActiveTab('overview')}
            aria-current={activeTab === 'overview' ? 'page' : undefined}
          >
            Tổng quan
          </button>
          <button
            className={activeTab === 'forecast' ? 'nav-tab active' : 'nav-tab'}
            onClick={() => setActiveTab('forecast')}
            aria-current={activeTab === 'forecast' ? 'page' : undefined}
          >
            Dự báo
          </button>
        </nav>
        <div className="topbar-meta"><span className="status-dot" /> Hệ thống dự báo</div>
      </header>

      <section className="hero">
        <div className="hero-copy">
          <p className="eyebrow"><span className="eyebrow-line" /> COFFEE SHOP ANALYTICS</p>
          <h1>Dự báo thông minh,<br /><span>phục vụ đúng nhịp.</span></h1>
          <p className="subtitle">Ước tính lượng hóa đơn theo ngày và ca làm để bạn luôn sẵn sàng cho lượt khách tiếp theo.</p>
          <button className="hero-link" onClick={() => setActiveTab('forecast')}>Xem dự báo <span aria-hidden="true">↘</span></button>
        </div>
        <div className="hero-art" aria-hidden="true">
          <div className="hero-orbit orbit-one" />
          <div className="hero-orbit orbit-two" />
          <div className="hero-bean bean-one" />
          <div className="hero-bean bean-two" />
          <div className="hero-cup"><span>☕</span></div>
          <span className="hero-art-label">BREW · SERVE · REPEAT</span>
        </div>
      </section>

      {error && <div className="error" role="alert"><span aria-hidden="true">!</span>{error}</div>}

      {activeTab === 'overview' && (
        <>
      <section className="stats" aria-label="Tổng quan dữ liệu">
        <article className="stat">
          <div className="stat-top"><span>Tổng giao dịch</span><span className="stat-icon">↗</span></div>
          <strong>{overview ? overview.transaction_rows.toLocaleString('vi-VN') : '—'}</strong>
          <small>Dữ liệu giao dịch</small>
        </article>
        <article className="stat">
          <div className="stat-top"><span>Cửa hàng</span><span className="stat-icon">⌂</span></div>
          <strong>{overview?.unique_stores ?? '—'}</strong>
          <small>Đang có trong tập dữ liệu</small>
        </article>
        <article className="stat">
          <div className="stat-top"><span>Ngày nghỉ / lễ</span><span className="stat-icon">✳</span></div>
          <strong>{overview ? overview.holiday_rows.toLocaleString('vi-VN') : '—'}</strong>
          <small>Bản ghi ngày đặc biệt</small>
        </article>
        <article className="stat">
          <div className="stat-top"><span>Nhóm ngày / ca</span><span className="stat-icon">▦</span></div>
          <strong>{overview ? overview.daily_shift_groups.toLocaleString('vi-VN') : '—'}</strong>
          <small>Cơ sở cho mô hình dự báo</small>
        </article>
      </section>

      <section className="content-grid">
        <article className="panel prediction" id="forecast">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">01 — DỰ BÁO</p>
              <h2>Lên kế hoạch cho ca tiếp theo</h2>
              <p className="panel-description">Chọn ngày và ca làm để xem lượng hóa đơn ước tính.</p>
            </div>
            <span className="model-tag"><span /> ML baseline</span>
          </div>

          <form onSubmit={runPrediction}>
            <label>
              Ngày dự đoán
              <input type="date" value={date} onChange={(e) => setDate(e.target.value)} required />
            </label>
            <label>
              Ca làm
              <select value={shift} onChange={(e) => setShift(e.target.value)}>
                {shifts.map((item) => <option key={item}>{item}</option>)}
              </select>
            </label>
            <label className="toggle-row">
              <span className="toggle-copy"><strong>Ngày nghỉ / ngày lễ</strong><small>Điều chỉnh dự báo cho ngày đặc biệt</small></span>
              <input type="checkbox" checked={holiday} onChange={(e) => setHoliday(e.target.checked)} />
              <span className="toggle-control" aria-hidden="true" />
            </label>
            <button className="primary-button" disabled={busy}>
              {busy ? <><span className="spinner" /> Đang tính toán…</> : <>Tạo dự báo <span aria-hidden="true">→</span></>}
            </button>
          </form>

          {prediction !== null ? (
            <div className="result" aria-live="polite">
              <div className="result-copy"><span>KẾT QUẢ DỰ BÁO</span><small>{shift} · {holiday ? 'Ngày nghỉ / lễ' : 'Ngày thường'}</small></div>
              <strong>{prediction.toLocaleString('vi-VN')}<small> hóa đơn</small></strong>
            </div>
          ) : (
            <div className="result-placeholder"><span className="placeholder-icon">✳</span><span>Kết quả dự báo sẽ hiển thị tại đây</span></div>
          )}
          <p className="hint">Ca làm: Night 00–05 · Morning 06–11 · Afternoon 12–16 · Evening 17–23</p>
        </article>

        <article className="panel chart-panel">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">02 — XU HƯỚNG</p>
              <h2>Lịch sử hóa đơn</h2>
              <p className="panel-description">Các nhóm ngày và ca làm gần nhất</p>
            </div>
            <span className="chart-period">14 nhóm gần nhất</span>
          </div>
          <div className="chart">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData} margin={{ top: 8, right: 4, left: -18, bottom: 0 }}>
                <CartesianGrid stroke="#edf0e9" strokeDasharray="4 5" vertical={false} />
                <XAxis dataKey="label" axisLine={false} tickLine={false} tick={{ fontSize: 10, fill: '#858a7e' }} interval="preserveStartEnd" dy={10} />
                <YAxis allowDecimals={false} axisLine={false} tickLine={false} tick={{ fontSize: 10, fill: '#858a7e' }} />
                <Tooltip
                  cursor={{ fill: '#f4f5ef' }}
                  contentStyle={{ border: '1px solid #e8e9df', borderRadius: 12, boxShadow: '0 8px 24px #26351d12', fontSize: 12 }}
                  labelStyle={{ color: '#68715f', marginBottom: 4 }}
                />
                <Bar dataKey="invoices" name="Số hóa đơn" fill="#53734b" radius={[5, 5, 0, 0]} maxBarSize={34} />
              </BarChart>
            </ResponsiveContainer>
          </div>
          <div className="chart-footer"><span><i /> Số hóa đơn</span><span>Dữ liệu tổng hợp theo ngày / ca</span></div>
        </article>
      </section>

      <section className="panel table-panel">
        <div className="panel-heading table-heading">
          <div>
            <p className="eyebrow">03 — DỮ LIỆU</p>
            <h2>Hoạt động gần đây</h2>
            <p className="panel-description">Thông tin lịch sử dùng làm cơ sở phân tích.</p>
          </div>
          <button className="secondary-button" onClick={() => void loadDashboard()}><span aria-hidden="true">↻</span> Làm mới</button>
        </div>
        <div className="table-wrap">
          <table>
            <thead><tr><th>Ngày</th><th>Ca làm</th><th>Loại ngày</th><th className="numeric">Số hóa đơn</th></tr></thead>
            <tbody>
              {history.slice(0, 12).map((row, index) => (
                <tr key={`${row.date}-${row.shift}-${index}`}>
                  <td className="date-cell">{row.date}</td>
                  <td>{row.shift}</td>
                  <td><span className={row.is_holiday ? 'badge holiday' : 'badge'}><i />{row.is_holiday ? 'Ngày nghỉ' : 'Ngày thường'}</span></td>
                  <td className="numeric invoice-cell">{row.invoice_count.toLocaleString('vi-VN')}</td>
                </tr>
              ))}
              {!history.length && <tr><td className="empty-row" colSpan={4}>Chưa có dữ liệu. Hãy kiểm tra kết nối Backend.</td></tr>}
            </tbody>
          </table>
        </div>
      </section>
        </>
      )}

      {activeTab === 'forecast' && <section className="forecast-grid" aria-label="Dự báo trong tương lai">
        <article className="panel forecast-panel">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">03 — DỰ BÁO 7 NGÀY</p>
              <h2>Lượng hóa đơn tuần tới</h2>
              <p className="panel-description">Ước tính số hóa đơn theo từng ngày.</p>
            </div>
            <span className="chart-period">7 ngày</span>
          </div>
          <div className="chart forecast-chart">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={forecastWeek} margin={{ top: 8, right: 4, left: -18, bottom: 0 }}>
                <CartesianGrid stroke="#edf0e9" strokeDasharray="4 5" vertical={false} />
                <XAxis dataKey="label" axisLine={false} tickLine={false} tick={{ fontSize: 10, fill: '#858a7e' }} />
                <YAxis allowDecimals={false} axisLine={false} tickLine={false} tick={{ fontSize: 10, fill: '#858a7e' }} />
                <Tooltip
                  cursor={{ fill: '#f4f5ef' }}
                  contentStyle={{ border: '1px solid #e8e9df', borderRadius: 12, fontSize: 12 }}
                  formatter={(value) => [`${value} hóa đơn`, 'Dự báo']}
                  labelFormatter={(_, payload) => payload?.[0]?.payload.fullDate ?? ''}
                />
                <Bar dataKey="invoices" name="Dự báo" fill="#53734b" radius={[5, 5, 0, 0]} maxBarSize={38} />
              </BarChart>
            </ResponsiveContainer>
          </div>
          <div className="demo-note">Dữ liệu minh họa giao diện · chưa kết nối mô hình dự báo</div>
        </article>

        <article className="panel forecast-panel">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">04 — DỰ BÁO 1 THÁNG</p>
              <h2>Lượng hóa đơn 30 ngày tới</h2>
              <p className="panel-description">Xu hướng ước tính theo từng ngày.</p>
            </div>
            <span className="chart-period">30 ngày</span>
          </div>
          <div className="chart forecast-chart">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={forecastMonth} margin={{ top: 8, right: 4, left: -18, bottom: 0 }}>
                <CartesianGrid stroke="#edf0e9" strokeDasharray="4 5" vertical={false} />
                <XAxis dataKey="label" axisLine={false} tickLine={false} tick={{ fontSize: 10, fill: '#858a7e' }} interval={4} />
                <YAxis allowDecimals={false} axisLine={false} tickLine={false} tick={{ fontSize: 10, fill: '#858a7e' }} />
                <Tooltip
                  cursor={{ fill: '#f4f5ef' }}
                  contentStyle={{ border: '1px solid #e8e9df', borderRadius: 12, fontSize: 12 }}
                  formatter={(value) => [`${value} hóa đơn`, 'Dự báo']}
                  labelFormatter={(_, payload) => payload?.[0]?.payload.fullDate ?? ''}
                />
                <Bar dataKey="invoices" name="Dự báo" fill="#8a9b70" radius={[3, 3, 0, 0]} maxBarSize={18} />
              </BarChart>
            </ResponsiveContainer>
          </div>
          <div className="demo-note">Dữ liệu minh họa giao diện · chưa kết nối mô hình dự báo</div>
        </article>
      </section>}

      {chatOpen && (
        <section className="chatbot-panel chat-widget" aria-label="Chatbot hỗ trợ">
          <div className="chat-widget-heading">
            <div>
              <strong>Coffee Assistant</strong>
              <small><span className="status-dot" /> Đang trực tuyến · Demo</small>
            </div>
            <button className="chat-close" onClick={() => setChatOpen(false)} aria-label="Đóng cửa sổ chat">×</button>
          </div>
          <div className="chat-messages" aria-live="polite">
            {chatMessages.map((message, index) => (
              <div className={`chat-message ${message.role}`} key={`${message.role}-${index}`}>
                {message.text}
              </div>
            ))}
          </div>
          <form className="chat-form" onSubmit={sendChatMessage}>
            <label className="visually-hidden" htmlFor="chat-input">Tin nhắn cho Coffee Assistant</label>
            <input
              id="chat-input"
              value={chatInput}
              onChange={(e) => setChatInput(e.target.value)}
              placeholder="Nhập tin nhắn..."
            />
            <button className="primary-button" type="submit" disabled={!chatInput.trim()} aria-label="Gửi tin nhắn">➤</button>
          </form>
          <p className="demo-note">Chatbot trả lời theo kịch bản mẫu, chưa kết nối AI/backend.</p>
        </section>
      )}
      <button
        className={chatOpen ? 'chat-launcher open' : 'chat-launcher'}
        onClick={() => setChatOpen((open) => !open)}
        aria-label={chatOpen ? 'Đóng chatbot' : 'Mở chatbot'}
        aria-expanded={chatOpen}
      >
        {chatOpen ? '×' : <svg aria-hidden="true" viewBox="0 0 24 24"><path d="M20 11.5a7.5 7.5 0 0 1-7.5 7.5H6l-3 2v-6.5A7.5 7.5 0 1 1 20 11.5Z" /><path d="M8 11.5h.01M12 11.5h.01M16 11.5h.01" /></svg>}
      </button>

      <footer><span className="footer-brand">coffee<span>forecast</span></span></footer>
    </main>
  )
}
