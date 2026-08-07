import React, { useState, useEffect, useMemo, useRef } from 'react';
import { Filter, DollarSign, Zap, Download, ArrowUpDown, Target, Play, Square, CheckCircle2, HelpCircle } from 'lucide-react';
import { API_BASE } from './apiConfig';
import DistrictDrawer from './DistrictDrawer';
import MethodologyModal from './MethodologyModal';

// FundFinder prospecting view, merged in from the Streamlit app, with the
// Target Profile scoring engine and batch research ported from an earlier client engagement.
function ProspectView({ onResearch, productType, onOpenDossier }) {
  const [rows, setRows] = useState([]);
  const [profiles, setProfiles] = useState([]);
  const [activeProfiles, setActiveProfiles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [researched, setResearched] = useState(new Map());
  const [drawerDistrict, setDrawerDistrict] = useState(null);
  const [showMethod, setShowMethod] = useState(false);
  const [batchLimit, setBatchLimit] = useState(10);
  const [batch, setBatch] = useState(null);
  const pollRef = useRef(null);
  const [filters, setFilters] = useState({
    search: '', minEnroll: 500, maxEnroll: 50000, minFrpm: 0,
    minPoverty: 0, minFedPP: 0, county: 'All', urbanicity: 'All',
  });
  const [sortKey, setSortKey] = useState('profile_count');

  useEffect(() => {
    fetch(`${API_BASE}/api/funding/CA`)
      .then(res => res.json())
      .then(data => {
        setRows(data.districts || []);
        setProfiles(data.profiles || []);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

  const toggleProfile = (key) => setActiveProfiles(prev =>
    prev.includes(key) ? prev.filter(k => k !== key) : [...prev, key]);

  const refreshResearched = () => {
    fetch(`${API_BASE}/api/results`)
      .then(res => res.json())
      .then(data => setResearched(new Map(
        data.filter(r => r.state === 'CA').map(r => [r.district_name.toLowerCase(), r.id]))))
      .catch(() => {});
  };

  useEffect(() => {
    refreshResearched();
    // Pick up an already-running batch on mount (e.g. after a page refresh)
    fetch(`${API_BASE}/api/batch/status`)
      .then(res => res.json())
      .then(s => { if (s.state !== 'idle') { setBatch(s); startPolling(); } })
      .catch(() => {});
    return () => clearInterval(pollRef.current);
  }, []);

  const startPolling = () => {
    clearInterval(pollRef.current);
    pollRef.current = setInterval(() => {
      fetch(`${API_BASE}/api/batch/status`)
        .then(res => res.json())
        .then(s => {
          setBatch(s);
          refreshResearched();
          if (s.state === 'idle') clearInterval(pollRef.current);
        })
        .catch(() => {});
    }, 5000);
  };

  const startBatch = () => {
    fetch(`${API_BASE}/api/batch/start`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ product_type: productType, limit: batchLimit, min_profiles: 1 }),
    })
      .then(res => res.json())
      .then(data => {
        if (data.detail) { alert(data.detail); return; }
        setBatch({ state: 'running', done: 0, total: data.targets.length, current: null });
        startPolling();
      })
      .catch(err => alert(`Batch start failed: ${err}`));
  };

  const stopBatch = () => {
    fetch(`${API_BASE}/api/batch/stop`, { method: 'POST' }).catch(() => {});
  };

  const batchRunning = batch && batch.state !== 'idle';

  const counties = useMemo(() =>
    ['All', ...[...new Set(rows.map(r => r.county).filter(Boolean))].sort()], [rows]);
  const urbanicities = useMemo(() =>
    ['All', ...[...new Set(rows.map(r => r.urbanicity).filter(Boolean))].sort()], [rows]);

  const num = (v) => { const f = parseFloat(v); return isNaN(f) || f < 0 ? null : f; };

  const filtered = useMemo(() => {
    const f = filters;
    let out = rows.filter(r => {
      const enroll = num(r.enroll) || 0;
      if (enroll < f.minEnroll || enroll > f.maxEnroll) return false;
      if ((num(r.frpm_pct) || 0) < f.minFrpm) return false;
      if ((num(r.stpov_pct) || 0) * 100 < f.minPoverty) return false;
      if ((num(r.rev_fed_pp) || 0) < f.minFedPP) return false;
      if (f.county !== 'All' && r.county !== f.county) return false;
      if (f.urbanicity !== 'All' && r.urbanicity !== f.urbanicity) return false;
      if (f.search && !r.dist_name.toLowerCase().includes(f.search.toLowerCase())) return false;
      if (activeProfiles.length > 0 && !activeProfiles.some(k => r[k] === 1)) return false;
      return true;
    });
    // Tie-break profile-count sorting by federal $/pupil so hot accounts rank sensibly
    return out.sort((a, b) =>
      ((num(b[sortKey]) || 0) - (num(a[sortKey]) || 0)) ||
      ((num(b.rev_fed_pp) || 0) - (num(a.rev_fed_pp) || 0)));
  }, [rows, filters, sortKey, activeProfiles]);

  const set = (key) => (e) => setFilters({ ...filters, [key]: e.target.type === 'number' ? Number(e.target.value) : e.target.value });

  const fmt = {
    int: (v) => num(v) != null ? Math.round(num(v)).toLocaleString() : '—',
    pct: (v) => num(v) != null ? `${num(v).toFixed(1)}%` : '—',
    pct100: (v) => num(v) != null ? `${(num(v) * 100).toFixed(1)}%` : '—',
    usd: (v) => num(v) != null ? `$${Math.round(num(v)).toLocaleString()}` : '—',
    usdM: (v) => num(v) != null ? `$${(num(v) / 1e6).toFixed(1)}M` : '—',
  };

  const downloadCsv = () => {
    const cols = ['dist_name', 'county', 'profile_count', 'profile_tags', 'enroll', 'frpm_pct', 'stpov_pct', 'ela_proficient_pct', 'rev_fed_pp', 'title_i_amount', 'lcff_supp_conc_total', 'urbanicity'];
    const lines = [cols.join(','), ...filtered.map(r => cols.map(c => `"${r[c] ?? ''}"`).join(','))];
    const blob = new Blob([lines.join('\n')], { type: 'text/csv' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = `ca_target_districts_${new Date().toISOString().slice(0, 10)}.csv`;
    a.click();
  };

  const sortOptions = [
    { key: 'profile_count', label: 'ICP (Profiles Matched)' },
    { key: 'rev_fed_pp', label: 'Federal $/Pupil' },
    { key: 'title_i_amount', label: 'Title I $' },
    { key: 'lcff_supp_conc_total', label: 'LCFF Supp+Conc $' },
    { key: 'enroll', label: 'Enrollment' },
    { key: 'frpm_pct', label: 'FRPM %' },
  ];

  return (
    <div className="prospect-view animate-fade-in">
      <div className="prospect-layout">
        {/* Filter sidebar */}
        <div className="card filter-panel">
          <div className="form-header">
            <Filter className="accent" size={20} />
            <h3 style={{ margin: 0 }}>Target Filters</h3>
          </div>
          <div className="filter-field">
            <label>
              <span style={{ display: 'inline-flex', alignItems: 'center', gap: '0.3rem' }}>
                Target Profiles
                <button className="btn-icon info-btn" onClick={() => setShowMethod(true)}
                  title="How scoring works" aria-label="How scoring works">
                  <HelpCircle size={13} />
                </button>
              </span>
              <span className="filter-value">{activeProfiles.length ? `${activeProfiles.length} active` : 'All'}</span>
            </label>
            <div className="profile-chips">
              {profiles.map(p => (
                <button
                  key={p.key}
                  className={`profile-chip ${activeProfiles.includes(p.key) ? 'active' : ''}`}
                  title={p.name}
                  onClick={() => toggleProfile(p.key)}
                >
                  <Target size={11} /> {p.label}
                </button>
              ))}
            </div>
          </div>
          <div className="filter-field">
            <label>District Name</label>
            <input type="text" value={filters.search} onChange={set('search')} placeholder="Search districts..." />
          </div>
          <div className="filter-field-row">
            <div className="filter-field">
              <label>Min Enrollment</label>
              <input type="number" value={filters.minEnroll} onChange={set('minEnroll')} />
            </div>
            <div className="filter-field">
              <label>Max Enrollment</label>
              <input type="number" value={filters.maxEnroll} onChange={set('maxEnroll')} />
            </div>
          </div>
          <div className="filter-field">
            <label>Min FRPM % <span className="filter-value">{filters.minFrpm}%</span></label>
            <input type="range" min="0" max="100" step="5" value={filters.minFrpm} onChange={set('minFrpm')} />
          </div>
          <div className="filter-field">
            <label>Min Student Poverty % <span className="filter-value">{filters.minPoverty}%</span></label>
            <input type="range" min="0" max="70" step="5" value={filters.minPoverty} onChange={set('minPoverty')} />
          </div>
          <div className="filter-field">
            <label>Min Federal $/Pupil <span className="filter-value">${filters.minFedPP}</span></label>
            <input type="range" min="0" max="5000" step="250" value={filters.minFedPP} onChange={set('minFedPP')} />
          </div>
          <div className="filter-field">
            <label>County</label>
            <select value={filters.county} onChange={set('county')} className="custom-select">
              {counties.map(c => <option key={c} value={c}>{c}</option>)}
            </select>
          </div>
          <div className="filter-field">
            <label>Urbanicity</label>
            <select value={filters.urbanicity} onChange={set('urbanicity')} className="custom-select">
              {urbanicities.map(u => <option key={u} value={u}>{u}</option>)}
            </select>
          </div>
        </div>

        {/* Results table */}
        <div className="card prospect-results">
          <div className="prospect-results-header">
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
              <DollarSign className="accent" size={20} />
              <h3 style={{ margin: 0 }}>
                {loading ? 'Loading funding dataset...' : `${filtered.length} Target Districts`}
              </h3>
            </div>
            <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', flexWrap: 'wrap' }}>
              <ArrowUpDown size={14} className="accent" />
              <select value={sortKey} onChange={(e) => setSortKey(e.target.value)} className="custom-select sort-select">
                {sortOptions.map(o => <option key={o.key} value={o.key}>Sort: {o.label}</option>)}
              </select>
              <button className="btn-secondary" onClick={downloadCsv} disabled={!filtered.length}>
                <Download size={14} /> CSV
              </button>
              {!batchRunning && (
                <div className="batch-controls">
                  <span className="batch-label">Top</span>
                  <input
                    type="number" min="1" max="100" value={batchLimit}
                    onChange={(e) => setBatchLimit(Number(e.target.value))}
                    className="batch-limit-input"
                  />
                  <button
                    className="btn-primary batch-start-btn"
                    onClick={startBatch}
                    title="Runs the full AI research pipeline on the top unresearched ICP targets. Takes minutes and spends API credits per district."
                  >
                    <Play size={13} /> Batch Research
                  </button>
                </div>
              )}
            </div>
          </div>

          {batchRunning && (
            <div className="batch-banner">
              <div className="radar-sweep"></div>
              <span className="batch-progress">
                Batch {batch.state === 'stopping' ? 'stopping' : 'running'}: {batch.done}/{batch.total} done
                {batch.current ? ` — researching ${batch.current}` : ''}
                {batch.errors?.length ? ` (${batch.errors.length} errors)` : ''}
              </span>
              <button className="btn-secondary" onClick={stopBatch} disabled={batch.state === 'stopping'}>
                <Square size={12} /> Stop
              </button>
            </div>
          )}

          <div className="prospect-table-wrapper">
            <table className="prospect-table">
              <thead>
                <tr>
                  <th>ICP</th><th>District</th><th>County</th><th>Enroll</th><th>FRPM</th><th>ELA Prof</th>
                  <th>Fed $/Pupil</th><th>Title I</th><th>LCFF S+C</th><th>Type</th><th></th>
                </tr>
              </thead>
              <tbody>
                {filtered.slice(0, 200).map(r => (
                  <tr key={r.ncesid} className="prospect-row" onClick={() => setDrawerDistrict(r)}>
                    <td>
                      <span
                        className={`icp-badge ${r.profile_count >= 4 ? 'hot' : r.profile_count >= 2 ? 'warm' : r.profile_count >= 1 ? 'mild' : ''}`}
                        title={r.profile_tags}
                      >
                        {r.profile_count}
                      </span>
                    </td>
                    <td className="district-name" title={r.profile_tags}>
                      {r.dist_name}
                      {researched.has(r.dist_name.toLowerCase()) && (
                        <CheckCircle2 size={13} className="researched-check" title="Already researched" />
                      )}
                    </td>
                    <td>{(r.county || '').replace(' County', '')}</td>
                    <td>{fmt.int(r.enroll)}</td>
                    <td>{fmt.pct(r.frpm_pct)}</td>
                    <td>{fmt.pct(r.ela_proficient_pct)}</td>
                    <td>{fmt.usd(r.rev_fed_pp)}</td>
                    <td>{fmt.usdM(r.title_i_amount)}</td>
                    <td>{fmt.usdM(r.lcff_supp_conc_total)}</td>
                    <td>{r.urbanicity || '—'}</td>
                    <td>
                      <button
                        className="btn-primary research-row-btn"
                        onClick={(e) => { e.stopPropagation(); onResearch(r); }}
                      >
                        <Zap size={12} /> Research
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {filtered.length > 200 && (
              <div className="table-footnote">Showing top 200 of {filtered.length} — tighten filters or download the CSV for the full list.</div>
            )}
          </div>
        </div>
      </div>

      {showMethod && (
        <MethodologyModal profiles={profiles} counts={null} onClose={() => setShowMethod(false)} />
      )}

      <DistrictDrawer
        district={drawerDistrict}
        resultId={drawerDistrict ? researched.get(drawerDistrict.dist_name.toLowerCase()) : null}
        onClose={() => setDrawerDistrict(null)}
        onResearch={(d) => { setDrawerDistrict(null); onResearch(d); }}
        onOpenDossier={onOpenDossier}
      />
    </div>
  );
}

export default ProspectView;
