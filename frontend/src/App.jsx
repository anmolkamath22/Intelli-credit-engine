import { useMemo, useState } from 'react'
import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis, CartesianGrid, BarChart, Bar } from 'recharts'

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000'
const DATA_TYPES = [
  'annual_reports',
  'financial_statements',
  'balance_sheets',
  'gst_returns',
  'bank_statements',
  'legal_documents',
  'news_documents'
]

async function api(path, options = {}) {
  const res = await fetch(`${API_BASE}${path}`, options)
  if (!res.ok) {
    const txt = await res.text()
    throw new Error(txt || `API ${path} failed`)
  }
  return res.json()
}

function scoreBand(score) {
  if (score >= 75) return 'Strong Credit'
  if (score >= 60) return 'Moderate Risk'
  if (score >= 45) return 'Weak / Elevated Risk'
  return 'High Risk'
}

function decisionFromBand(band) {
  if (band === 'strong_credit') return 'APPROVE'
  if (band === 'acceptable_moderate_risk') return 'CONDITIONAL APPROVE'
  if (band === 'weak_elevated_risk') return 'CONDITIONAL / REDUCE LIMIT'
  return 'REJECT / HIGH RISK'
}

export default function App() {
  const [company, setCompany] = useState('Blue Star Ltd')
  const [dataType, setDataType] = useState('annual_reports')
  const [files, setFiles] = useState([])
  const [status, setStatus] = useState('Idle')
  const [jobId, setJobId] = useState('')
  const [dashboard, setDashboard] = useState(null)
  const [running, setRunning] = useState(false)
  const [officer, setOfficer] = useState({
    factory_utilization: 0.7,
    management_credibility: 0.7,
    inventory_build_up: 0.3,
    supply_chain_risk: 0.3,
    collateral_notes: '',
    channel_checks: ''
  })

  const yearlyRows = useMemo(() => dashboard?.financial_history?.yearly_data || [], [dashboard])
  const trendRows = useMemo(() => yearlyRows.map(r => ({
    year: r.year,
    revenue: r.revenue || 0,
    ebitda: r.ebitda || 0,
    debt: r.debt || 0
  })), [yearlyRows])

  const riskRows = useMemo(() => {
    if (!dashboard?.credit_features) return []
    const c = dashboard.credit_features
    return [
      { name: 'Litigation Risk', value: Number(c.litigation_risk_score || 0) },
      { name: 'Management Risk', value: Number(c.management_risk_score || 0) },
      { name: 'Sector Risk', value: Number(c.sector_risk_score || 0) },
      { name: 'Circular Risk', value: Number(c.circular_trading_risk || 0) }
    ]
  }, [dashboard])

  async function uploadFiles() {
    if (!company || files.length === 0) return
    const form = new FormData()
    form.append('company', company)
    form.append('data_type', dataType)
    Array.from(files).forEach(f => form.append('files', f))
    setStatus('Uploading files...')
    await fetch(`${API_BASE}/api/v1/company/upload`, { method: 'POST', body: form })
    setStatus('Files uploaded')
  }

  async function saveOfficerInputs() {
    setStatus('Saving officer inputs...')
    await api('/api/v1/company/officer-inputs', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ company, ...officer })
    })
    setStatus('Officer inputs saved')
  }

  async function runPipeline() {
    setRunning(true)
    setStatus('Queueing pipeline...')
    const queued = await api('/api/v1/pipeline/run', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ company, debug_financials: true })
    })
    setJobId(queued.job_id)

    let complete = false
    while (!complete) {
      await new Promise(r => setTimeout(r, 2500))
      const job = await api(`/api/v1/jobs/${queued.job_id}`)
      setStatus(`Pipeline: ${job.status}`)
      if (job.status === 'completed') complete = true
      if (job.status === 'failed') throw new Error(job.error || 'Pipeline failed')
    }

    const d = await api(`/api/v1/dashboard/${encodeURIComponent(company)}`)
    setDashboard(d)
    setStatus('Pipeline completed')
    setRunning(false)
  }

  async function refreshDashboard() {
    const d = await api(`/api/v1/dashboard/${encodeURIComponent(company)}`)
    setDashboard(d)
    setStatus('Dashboard refreshed')
  }

  const score = Number(dashboard?.scoring_output?.credit_score || 0)
  const band = dashboard?.scoring_output?.score_band || ''
  const decision = dashboard?.scoring_output?.decision || decisionFromBand(band)
  const loanCr = Number(
    dashboard?.scoring_output?.recommended_loan_limit_crore ??
    dashboard?.scoring_output?.recommended_loan_limit ??
    0
  )
  const riskPremium = Number(
    dashboard?.scoring_output?.risk_premium_percent ??
    dashboard?.scoring_output?.risk_premium ??
    0
  )
  const interestRate = Number(
    dashboard?.scoring_output?.recommended_interest_rate_percent ??
    dashboard?.scoring_output?.recommended_interest_rate ??
    0
  )

  return (
    <div className="page">
      <header className="hero">
        <div>
          <h1>Intelli-Credit Engine</h1>
          <p>AI-powered Credit Appraisal Platform for Hackathon Demo</p>
        </div>
        <div className="status">{status}</div>
      </header>

      <section className="grid two">
        <article className="card">
          <h2>Company & Data Upload</h2>
          <label>Company Name</label>
          <input value={company} onChange={e => setCompany(e.target.value)} placeholder="Blue Star Ltd" />
          <label>Dataset Type</label>
          <select value={dataType} onChange={e => setDataType(e.target.value)}>
            {DATA_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
          </select>
          <input type="file" multiple onChange={e => setFiles(e.target.files)} />
          <button onClick={uploadFiles}>Upload Files</button>
        </article>

        <article className="card">
          <h2>Credit Officer Input</h2>
          {['factory_utilization', 'management_credibility', 'inventory_build_up', 'supply_chain_risk'].map(k => (
            <div key={k} className="row">
              <label>{k.replaceAll('_', ' ')}</label>
              <input
                type="number"
                step="0.05"
                min="0"
                max="1"
                value={officer[k]}
                onChange={e => setOfficer(v => ({ ...v, [k]: Number(e.target.value) }))}
              />
            </div>
          ))}
          <label>Collateral Notes</label>
          <textarea value={officer.collateral_notes} onChange={e => setOfficer(v => ({ ...v, collateral_notes: e.target.value }))} />
          <label>Channel Checks</label>
          <textarea value={officer.channel_checks} onChange={e => setOfficer(v => ({ ...v, channel_checks: e.target.value }))} />
          <button onClick={saveOfficerInputs}>Save Officer Inputs</button>
        </article>
      </section>

      <section className="grid three">
        <article className="card highlight">
          <h3>Final Credit Score</h3>
          <div className="score">{score.toFixed(2)}</div>
          <p>{scoreBand(score)}</p>
        </article>
        <article className="card highlight">
          <h3>Decision</h3>
          <div className="score small">{decision}</div>
          <p>{band || 'N/A'}</p>
        </article>
        <article className="card highlight">
          <h3>Loan & Interest</h3>
          <div className="score small">INR {loanCr.toFixed(2)} Cr</div>
          <p>{riskPremium.toFixed(2)}% premium | {interestRate.toFixed(2)}% p.a.</p>
        </article>
      </section>

      <section className="card actions">
        <button disabled={running} onClick={runPipeline}>{running ? 'Running...' : 'Run Full Credit Evaluation'}</button>
        <button onClick={refreshDashboard}>Refresh Results</button>
        {jobId && <span className="job">Job: {jobId}</span>}
      </section>

      <section className="grid two">
        <article className="card">
          <h2>5-Year Financial Trends (INR Crores)</h2>
          <div className="chartWrap">
            <ResponsiveContainer width="100%" height={260}>
              <LineChart data={trendRows}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="year" />
                <YAxis />
                <Tooltip />
                <Line type="monotone" dataKey="revenue" stroke="#0077b6" strokeWidth={2} />
                <Line type="monotone" dataKey="ebitda" stroke="#2a9d8f" strokeWidth={2} />
                <Line type="monotone" dataKey="debt" stroke="#e76f51" strokeWidth={2} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </article>

        <article className="card">
          <h2>Risk Breakdown</h2>
          <div className="chartWrap">
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={riskRows}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" />
                <YAxis />
                <Tooltip />
                <Bar dataKey="value" fill="#f4a261" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </article>
      </section>

      <section className="grid two">
        <article className="card">
          <h2>Board & Litigation</h2>
          <ul>
            {(dashboard?.research_summary?.board_of_directors || []).slice(0, 8).map((d, i) => <li key={i}>{d}</li>)}
          </ul>
          <p>Litigation Count: {dashboard?.research_summary?.litigation_count ?? 'N/A'}</p>
          <p>Litigation Risk Score: {dashboard?.research_summary?.litigation_risk_score ?? 'N/A'}</p>
        </article>

        <article className="card">
          <h2>News & Sector</h2>
          <p>Negative News Count: {dashboard?.research_summary?.negative_news_count ?? 'N/A'}</p>
          <p>News Sentiment Score: {dashboard?.research_summary?.news_sentiment_score ?? 'N/A'}</p>
          <p>Sector Risk: {dashboard?.research_summary?.sector_risk ?? 'N/A'}</p>
        </article>
      </section>

      <section className="card">
        <h2>Decision Trace & Risk Flags</h2>
        <ul>
          {(dashboard?.decision_trace?.risk_flags || []).map((f, i) => (
            <li key={i}><strong>{f.flag || f}:</strong> {f.explanation || ''}</li>
          ))}
        </ul>
      </section>

      <section className="card">
        <h2>Downloads</h2>
        <div className="downloadRow">
          <a href={`${API_BASE}/api/v1/download/${encodeURIComponent(company)}/cam_pdf`} target="_blank">CAM PDF</a>
          <a href={`${API_BASE}/api/v1/download/${encodeURIComponent(company)}/cam_tex`} target="_blank">CAM TEX</a>
          <a href={`${API_BASE}/api/v1/download/${encodeURIComponent(company)}/cam_payload`} target="_blank">CAM Payload</a>
          <a href={`${API_BASE}/api/v1/download/${encodeURIComponent(company)}/decision_trace`} target="_blank">Decision Trace</a>
        </div>
      </section>
    </div>
  )
}
