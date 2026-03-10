import { useEffect, useMemo, useRef, useState } from 'react'
import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis, CartesianGrid, BarChart, Bar } from 'recharts'
import { API_BASE, API_PREFIX } from './config'

const DATA_TYPES = [
  'alm',
  'shareholding_pattern',
  'borrowing_profile',
  'annual_reports',
  'portfolio_cuts',
  'financial_statements',
  'balance_sheets',
  'gst_returns',
  'bank_statements',
  'legal_documents',
  'news_documents'
]

const REQUIRED_UPLOAD_TYPES = [
  'alm',
  'shareholding_pattern',
  'borrowing_profile',
  'annual_reports',
  'portfolio_cuts'
]

const DEFAULT_SCHEMA_TEMPLATE = {
  alm: ['maturity_bucket', 'assets_amount', 'liabilities_amount', 'gap'],
  shareholding_pattern: ['holder_name', 'holder_type', 'ownership_percent'],
  borrowing_profile: ['lender', 'facility_type', 'outstanding_amount', 'interest_rate', 'maturity_date'],
  annual_reports: ['fiscal_year', 'revenue', 'ebitda', 'net_profit', 'total_debt'],
  portfolio_cuts: ['segment', 'exposure', 'npa_percent', 'collection_efficiency']
}

async function api(path, options = {}) {
  const res = await fetch(`${API_BASE}${path}`, options)
  const payload = await res.json().catch(() => ({}))
  if (!res.ok || payload.success === false) {
    const msg = payload.message || payload.detail || `API ${path} failed`
    throw new Error(msg)
  }
  return payload
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

function prettyScoreBand(v = '') {
  const map = {
    strong_credit: 'Strong credit profile',
    acceptable_moderate_risk: 'Acceptable profile with moderate risk',
    weak_elevated_risk: 'Weak profile with elevated risk',
    high_risk: 'High-risk profile'
  }
  return map[v] || (v ? prettyKey(v) : 'N/A')
}

function bandInterpretation(v = '') {
  const map = {
    strong_credit: 'Financial and risk signals support standard approval terms.',
    acceptable_moderate_risk: 'Credit can be extended with tighter controls and risk-based pricing.',
    weak_elevated_risk: 'Lending should remain conservative with strong covenants and close monitoring.',
    high_risk: 'Risk level is outside acceptable tolerance for standard lending.'
  }
  return map[v] || 'Risk band interpretation unavailable.'
}

function prettyDecision(v = '') {
  const map = {
    approve: 'APPROVE',
    approve_with_conditions: 'APPROVE WITH CONDITIONS',
    reject: 'REJECT'
  }
  return map[v] || v || 'N/A'
}

function prettyInterestDecision(v = '') {
  const map = {
    accept_requested_rate: 'Accept requested rate',
    increase_rate: 'Increase rate',
    negotiate_rate: 'Negotiate / reprice'
  }
  return map[v] || v || 'N/A'
}

function prettyKey(v = '') {
  return String(v)
    .replaceAll('_', ' ')
    .replace(/\b\w/g, (m) => m.toUpperCase())
}

export default function App() {
  const [company, setCompany] = useState('Blue Star Ltd')
  const [dataType, setDataType] = useState('annual_reports')
  const [files, setFiles] = useState([])
  const [status, setStatus] = useState('Idle')
  const [jobId, setJobId] = useState('')
  const [dashboard, setDashboard] = useState(null)
  const [uploadCounts, setUploadCounts] = useState({})
  const [classification, setClassification] = useState([])
  const [schemaMap, setSchemaMap] = useState({})
  const [extractionPreview, setExtractionPreview] = useState({})
  const [running, setRunning] = useState(false)
  const [error, setError] = useState('')
  const [offline, setOffline] = useState(false)
  const pollRef = useRef(null)

  const [officer, setOfficer] = useState({
    factory_utilization: 0.7,
    management_credibility: 0.7,
    inventory_build_up: 0.3,
    supply_chain_risk: 0.3,
    collateral_notes: '',
    channel_checks: ''
  })
  const [entity, setEntity] = useState({
    cin: '',
    pan: '',
    sector: '',
    subsector: '',
    turnover: '',
    loan_type: '',
    loan_amount: '',
    loan_tenure_months: '',
    interest_rate: ''
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

  useEffect(() => {
    return () => {
      if (pollRef.current) clearInterval(pollRef.current)
    }
  }, [])

  async function checkHealth() {
    try {
      const h = await api(`${API_PREFIX}/health`)
      setOffline(!(h?.data?.status === 'ok'))
    } catch (e) {
      setOffline(true)
      setError(`Backend unreachable at ${API_BASE}`)
    }
  }

  useEffect(() => {
    checkHealth()
  }, [])

  async function uploadFiles() {
    if (!company || files.length === 0) {
      setError('Select company and at least one file')
      return
    }
    setError('')
    const form = new FormData()
    form.append('company', company)
    form.append('data_type', dataType)
    Array.from(files).forEach(f => form.append('files', f))
    setStatus('Uploading files...')
    const res = await fetch(`${API_BASE}${API_PREFIX}/company/upload`, { method: 'POST', body: form })
    const payload = await res.json().catch(() => ({}))
    if (!res.ok || payload.success === false) {
      throw new Error(payload.message || 'Upload failed')
    }
    const uploadedCount = (payload.saved_files || []).length
    setUploadCounts(prev => ({ ...prev, [dataType]: (prev[dataType] || 0) + uploadedCount }))
    setFiles([])
    setStatus(`Files uploaded (${(payload.saved_files || []).length})`)
  }

  async function saveEntityProfile() {
    setError('')
    setStatus('Saving entity profile...')
    await api(`${API_PREFIX}/entity/onboard`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        company,
        ...entity,
        turnover: Number(entity.turnover || 0),
        loan_amount: Number(entity.loan_amount || 0),
        loan_tenure_months: Number(entity.loan_tenure_months || 0),
        interest_rate: Number(entity.interest_rate || 0)
      })
    })
    setStatus('Entity onboarding saved')
  }

  async function runClassification() {
    setError('')
    setStatus('Classifying uploaded files...')
    const form = new FormData()
    form.append('company', company)
    const res = await fetch(`${API_BASE}${API_PREFIX}/classification/auto`, { method: 'POST', body: form })
    const payload = await res.json().catch(() => ({}))
    if (!res.ok || payload.success === false) throw new Error(payload.message || 'Classification failed')
    setClassification(payload?.data?.files || [])
    setStatus('Classification generated')
  }

  async function approveClassification(fileName, finalCategory) {
    await api(`${API_PREFIX}/classification/review`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        company,
        file_name: fileName,
        approved: true,
        final_category: finalCategory
      })
    })
    setClassification(prev => prev.map(r => r.file_name === fileName ? { ...r, approved: true, final_category: finalCategory } : r))
  }

  async function loadSchema() {
    const d = await api(`${API_PREFIX}/schema-mapping/${encodeURIComponent(company)}`)
    setSchemaMap(d?.data?.mappings || {})
    setStatus('Schema mapping loaded')
  }

  async function saveSchema() {
    await api(`${API_PREFIX}/schema-mapping`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ company, mappings: schemaMap })
    })
    setStatus('Schema mapping saved')
  }

  async function runExtractionPreview() {
    const form = new FormData()
    form.append('company', company)
    const res = await fetch(`${API_BASE}${API_PREFIX}/extraction/preview`, { method: 'POST', body: form })
    const payload = await res.json().catch(() => ({}))
    if (!res.ok || payload.success === false) throw new Error(payload.message || 'Extraction preview failed')
    setExtractionPreview(payload?.data?.extracted_structured_data || {})
    setStatus('Extraction preview generated')
  }

  async function saveOfficerInputs() {
    setError('')
    setStatus('Saving officer inputs...')
    await api(`${API_PREFIX}/company/officer-inputs`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ company, ...officer })
    })
    setStatus('Officer inputs saved')
  }

  async function runPipeline() {
    setRunning(true)
    setError('')
    setStatus('Queueing pipeline...')

    const queued = await api(`${API_PREFIX}/pipeline/run`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ company, debug_financials: true })
    })
    const id = queued.job_id
    setJobId(id)

    const startedAt = Date.now()
    const timeoutMs = 15 * 60 * 1000

    if (pollRef.current) clearInterval(pollRef.current)
    pollRef.current = setInterval(async () => {
      try {
        const job = await api(`${API_PREFIX}/jobs/${id}/status`)
        setStatus(`Pipeline: ${job.status} (${job.progress || 0}%)`)

        if (job.status === 'completed') {
          clearInterval(pollRef.current)
          const result = await api(`${API_PREFIX}/jobs/${id}/result`)
          const d = await api(`${API_PREFIX}/dashboard/${encodeURIComponent(company)}`)
          setDashboard(d.data)
          setStatus(result.message || 'Pipeline completed')
          setRunning(false)
        } else if (job.status === 'failed') {
          clearInterval(pollRef.current)
          setError(job.error || 'Pipeline failed')
          setStatus('Pipeline failed')
          setRunning(false)
        } else if (Date.now() - startedAt > timeoutMs) {
          clearInterval(pollRef.current)
          setError('Pipeline timeout. Please retry and check backend logs.')
          setStatus('Pipeline timeout')
          setRunning(false)
        }
      } catch (e) {
        clearInterval(pollRef.current)
        setError(e.message || 'Polling failed')
        setStatus('Polling failed')
        setRunning(false)
      }
    }, 2500)
  }

  async function refreshDashboard() {
    setError('')
    const d = await api(`${API_PREFIX}/dashboard/${encodeURIComponent(company)}`)
    setDashboard(d.data)
    setClassification((d.data?.file_classification?.files) || [])
    setSchemaMap((d.data?.schema_mapping?.mappings) || {})
    setExtractionPreview((d.data?.extracted_structured_data?.extracted_structured_data) || {})
    const ep = d.data?.entity_profile || {}
    if (Object.keys(ep).length) {
      setEntity(v => ({
        ...v,
        cin: ep.cin || '',
        pan: ep.pan || '',
        sector: ep.sector || '',
        subsector: ep.subsector || '',
        turnover: ep.turnover ?? '',
        loan_type: ep.loan_type || '',
        loan_amount: ep.loan_amount ?? '',
        loan_tenure_months: ep.loan_tenure_months ?? '',
        interest_rate: ep.interest_rate ?? ''
      }))
    }
    setStatus('Dashboard refreshed')
  }

  const score = Number(dashboard?.scoring_output?.credit_score || 0)
  const band = dashboard?.scoring_output?.score_band || ''
  const decision = dashboard?.scoring_output?.decision_status || dashboard?.scoring_output?.decision || decisionFromBand(band)
  const requestedLoanCr = Number(
    dashboard?.scoring_output?.requested_loan_amount ??
    dashboard?.entity_profile?.loan_amount ??
    0
  )
  const supportCapCr = Number(dashboard?.scoring_output?.supportability_cap ?? 0)
  const supportability = dashboard?.scoring_output?.requested_amount_supportability || 'unknown'
  const loanType = dashboard?.scoring_output?.loan_type || dashboard?.entity_profile?.loan_type || 'N/A'
  const tenureMonths = Number(dashboard?.scoring_output?.loan_tenure_months || dashboard?.entity_profile?.loan_tenure_months || 0)
  const riskPremium = Number(
    dashboard?.scoring_output?.risk_premium_percent ??
    dashboard?.scoring_output?.risk_premium ??
    0
  )
  const requestedRate = Number(
    dashboard?.scoring_output?.requested_interest_rate ??
    dashboard?.entity_profile?.interest_rate ??
    0
  )
  const interestDecision = dashboard?.scoring_output?.interest_decision || 'N/A'
  const interestRate = Number(
    dashboard?.scoring_output?.recommended_interest_rate_percent ??
    dashboard?.scoring_output?.recommended_interest_rate ??
    0
  )
  const requiredUploadStatus = REQUIRED_UPLOAD_TYPES.map((t) => ({
    type: t,
    count: Number(uploadCounts[t] || 0),
    done: Number(uploadCounts[t] || 0) > 0
  }))
  const missingRequiredUploads = requiredUploadStatus.filter((x) => !x.done).map((x) => x.type)
  const effectiveSchemaMap = Object.keys(schemaMap || {}).length
    ? schemaMap
    : DEFAULT_SCHEMA_TEMPLATE

  const onAction = async (fn) => {
    try {
      await fn()
    } catch (e) {
      setError(e.message || 'Unexpected error')
      setStatus('Error')
      setRunning(false)
    }
  }

  return (
    <div className="page">
      <header className="hero">
        <div>
          <h1>Intelli-Credit Engine</h1>
          <p>API: {API_BASE}</p>
        </div>
        <div className="status">{status}</div>
      </header>

      {offline && <div className="errorBox">Backend is offline. Check API URL and backend process.</div>}
      {error && <div className="errorBox">{error}</div>}

      <section className="grid two">
        <article className="card">
          <h2>Entity Onboarding</h2>
          <label>Entity Name</label>
          <input value={company} onChange={e => setCompany(e.target.value)} />
          <div className="grid two compact">
            <div>
              <label>CIN</label>
              <input value={entity.cin} onChange={e => setEntity(v => ({ ...v, cin: e.target.value }))} />
            </div>
            <div>
              <label>PAN</label>
              <input value={entity.pan} onChange={e => setEntity(v => ({ ...v, pan: e.target.value }))} />
            </div>
            <div>
              <label>Sector</label>
              <input value={entity.sector} onChange={e => setEntity(v => ({ ...v, sector: e.target.value }))} />
            </div>
            <div>
              <label>Subsector</label>
              <input value={entity.subsector} onChange={e => setEntity(v => ({ ...v, subsector: e.target.value }))} />
            </div>
            <div>
              <label>Turnover (Cr)</label>
              <input type="number" value={entity.turnover} onChange={e => setEntity(v => ({ ...v, turnover: e.target.value }))} />
            </div>
            <div>
              <label>Loan Type</label>
              <input value={entity.loan_type} onChange={e => setEntity(v => ({ ...v, loan_type: e.target.value }))} />
            </div>
            <div>
              <label>Loan Amount (Cr)</label>
              <input type="number" value={entity.loan_amount} onChange={e => setEntity(v => ({ ...v, loan_amount: e.target.value }))} />
            </div>
            <div>
              <label>Tenure (months)</label>
              <input type="number" value={entity.loan_tenure_months} onChange={e => setEntity(v => ({ ...v, loan_tenure_months: e.target.value }))} />
            </div>
            <div>
              <label>Interest Rate (%)</label>
              <input type="number" value={entity.interest_rate} onChange={e => setEntity(v => ({ ...v, interest_rate: e.target.value }))} />
            </div>
          </div>
          <button onClick={() => onAction(saveEntityProfile)}>Save Onboarding</button>
        </article>

        <article className="card">
          <h2>Intelligent Data Ingestion</h2>
          <p>Required categories: ALM, Shareholding Pattern, Borrowing Profile, Annual Reports, Portfolio Cuts.</p>
          <div className="workflowBox">
            <div className="workflowTitle">Upload workflow (mandatory sequence)</div>
            <div className="workflowSteps">
              <span>1. Pick category</span>
              <span>2. Select files</span>
              <span>3. Click Upload Files</span>
              <span>4. Repeat next category</span>
            </div>
            <p className="workflowNote">Upload one category at a time. Do not mix files from different categories in the same upload.</p>
          </div>
          <label>Dataset Type</label>
          <select value={dataType} onChange={e => setDataType(e.target.value)}>
            {DATA_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
          </select>
          <input type="file" multiple onChange={e => setFiles(e.target.files)} />
          <p className="metaText">Selected files: {files?.length || 0}</p>
          <button onClick={() => onAction(uploadFiles)}>Upload Files</button>
          <div className="uploadProgress">
            {requiredUploadStatus.map(({ type: t, count: n, done }) => {
              return (
                <div key={t} className={`uploadChip ${done ? 'ok' : ''}`}>
                  <span>{t}</span>
                  <span>{done ? `${n} uploaded` : 'pending'}</span>
                </div>
              )
            })}
          </div>
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
          <button onClick={() => onAction(saveOfficerInputs)}>Save Officer Inputs</button>
        </article>
      </section>

      <section className="card actions">
        <div className="actionGroupLabel">Data quality workflow</div>
        <button onClick={() => onAction(runClassification)}>1) Auto Classify Files</button>
        <button onClick={() => onAction(loadSchema)}>2) Load Schema Mapping</button>
        <button onClick={() => onAction(saveSchema)}>3) Save Schema Mapping</button>
        <button onClick={() => onAction(runExtractionPreview)}>4) Build Extraction Preview</button>
      </section>

      <section className="grid two">
        <article className="card">
          <h2>Classification Review (Human-in-the-loop)</h2>
          <p className="metaText">Review predicted categories and correct any mismatch before running evaluation.</p>
          <div className="tableWrap">
            <table>
              <thead>
                <tr>
                  <th>File</th>
                  <th>Predicted</th>
                  <th>Confidence</th>
                  <th>Final Category</th>
                </tr>
              </thead>
              <tbody>
                {classification.slice(0, 20).map((r, idx) => (
                  <tr key={`${r.file_name}-${idx}`}>
                    <td>{r.file_name}</td>
                    <td>{r.predicted_category}</td>
                    <td>{r.confidence}</td>
                    <td>
                      <select
                        value={r.final_category || r.predicted_category}
                        onChange={e => onAction(() => approveClassification(r.file_name, e.target.value))}
                      >
                        {DATA_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
                      </select>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </article>

        <article className="card">
          <h2>Dynamic Schema Mapping</h2>
          <p className="metaText">Edit the extracted field list per category, then click Save Schema Mapping.</p>
          {Object.keys(schemaMap || {}).length === 0 && (
            <div className="emptyState">
              No saved schema found yet. Showing default template so you can start immediately.
            </div>
          )}
          {Object.entries(effectiveSchemaMap || {}).slice(0, 12).map(([k, fields]) => (
            <div key={k} className="row">
              <label>{prettyKey(k)}</label>
              <input
                value={(fields || []).join(', ')}
                onChange={e => setSchemaMap(v => ({ ...v, [k]: e.target.value.split(',').map(x => x.trim()).filter(Boolean) }))}
              />
            </div>
          ))}
          <button onClick={() => setSchemaMap(DEFAULT_SCHEMA_TEMPLATE)}>Reset To Default Template</button>
        </article>
      </section>

      <section className="card">
        <h2>Structured Extraction Preview</h2>
        <p className="metaText">Quick view of normalized output that will feed analysis and recommendation.</p>
        <pre className="jsonBox">{JSON.stringify(extractionPreview, null, 2)}</pre>
      </section>

      <section className="grid three">
        <article className="card highlight">
          <h3>Final Credit Score</h3>
          <div className="score">{score.toFixed(2)}</div>
          <p>{scoreBand(score)}</p>
        </article>
        <article className="card highlight">
          <h3>Final Credit Decision</h3>
          <div className="score small">{prettyDecision(decision)}</div>
          <p className="decisionBand">{prettyScoreBand(band)}</p>
          <p className="decisionHint">{bandInterpretation(band)}</p>
        </article>
        <article className="card highlight">
          <h3>Requested Loan Evaluation</h3>
          <div className="loanCardTop">
            <span className="loanAsk">Asked: INR {requestedLoanCr.toFixed(2)} Cr</span>
            <span className={`supportBadge ${String(supportability).includes('supportable') ? 'good' : 'warn'}`}>
              {prettyKey(supportability)}
            </span>
          </div>
          <div className="metricGrid">
            <div><b>Loan type</b><span>{loanType}</span></div>
            <div><b>Tenure</b><span>{tenureMonths || 'N/A'} months</span></div>
            <div><b>Internal cap</b><span>INR {supportCapCr.toFixed(2)} Cr</span></div>
            <div><b>Requested rate</b><span>{requestedRate.toFixed(2)}% p.a.</span></div>
            <div><b>Rate decision</b><span>{prettyInterestDecision(interestDecision)}</span></div>
            <div><b>Final rate</b><span>{interestRate.toFixed(2)}% p.a.</span></div>
            <div><b>Risk premium</b><span>{riskPremium.toFixed(2)}%</span></div>
          </div>
        </article>
      </section>

      <section className="card actions">
        <button disabled={running} onClick={() => onAction(runPipeline)}>{running ? 'Running...' : 'Run Full Credit Evaluation'}</button>
        <button onClick={() => onAction(refreshDashboard)}>Refresh Results</button>
        {missingRequiredUploads.length > 0 && (
          <span className="warnInline">Missing required uploads: {missingRequiredUploads.join(', ')}</span>
        )}
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
          <h2>Triangulated Insights</h2>
          <ul>
            {(dashboard?.triangulated_insights?.insights || []).map((i, idx) => (
              <li key={idx}><b>{i.theme}</b> ({i.severity}): {i.insight}</li>
            ))}
          </ul>
        </article>
        <article className="card">
          <h2>SWOT Analysis</h2>
          <p><b>Strengths:</b> {(dashboard?.swot_analysis?.strengths || []).join(' | ') || 'N/A'}</p>
          <p><b>Weaknesses:</b> {(dashboard?.swot_analysis?.weaknesses || []).join(' | ') || 'N/A'}</p>
          <p><b>Opportunities:</b> {(dashboard?.swot_analysis?.opportunities || []).join(' | ') || 'N/A'}</p>
          <p><b>Threats:</b> {(dashboard?.swot_analysis?.threats || []).join(' | ') || 'N/A'}</p>
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
          <p>Litigation Confidence: {dashboard?.research_summary?.litigation_confidence ?? 'N/A'}</p>
          <p>Board Risk: {dashboard?.board_risk_summary?.board_risk_score ?? 'N/A'}</p>
        </article>

        <article className="card">
          <h2>News & Sector</h2>
          <p>Negative News Count: {dashboard?.research_summary?.negative_news_count ?? 'N/A'}</p>
          <p>News Sentiment Score: {dashboard?.research_summary?.news_sentiment_score ?? 'N/A'}</p>
          <p>News Confidence: {dashboard?.research_summary?.news_confidence ?? 'N/A'}</p>
          <p>Sector Risk: {dashboard?.research_summary?.sector_risk ?? 'N/A'}</p>
        </article>
      </section>

      <section className="card">
        <h2>Conditions & Rationale</h2>
        <p>{dashboard?.scoring_output?.approval_rationale || 'N/A'}</p>
        <ul>
          {(dashboard?.scoring_output?.key_conditions || []).map((c, i) => <li key={i}>{c}</li>)}
        </ul>
      </section>

      <section className="card">
        <h2>Downloads</h2>
        <div className="downloadRow">
          <a href={`${API_BASE}${API_PREFIX}/download/${encodeURIComponent(company)}/cam_pdf`} target="_blank" rel="noreferrer">CAM PDF</a>
          <a href={`${API_BASE}${API_PREFIX}/download/${encodeURIComponent(company)}/cam_tex`} target="_blank" rel="noreferrer">CAM TEX</a>
          <a href={`${API_BASE}${API_PREFIX}/download/${encodeURIComponent(company)}/cam_payload`} target="_blank" rel="noreferrer">CAM Payload</a>
          <a href={`${API_BASE}${API_PREFIX}/download/${encodeURIComponent(company)}/decision_trace`} target="_blank" rel="noreferrer">Decision Trace</a>
        </div>
      </section>
    </div>
  )
}
