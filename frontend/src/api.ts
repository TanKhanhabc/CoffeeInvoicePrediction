import axios from 'axios'
export const api = axios.create({ baseURL: import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000', timeout: 60000 })
export type Overview = { transaction_rows: number; date_start: string; date_end: string; unique_stores: number; holiday_rows: number; daily_shift_groups: number }
export type HistoryRow = { date: string; shift: string; is_holiday: boolean; invoice_count: number }
