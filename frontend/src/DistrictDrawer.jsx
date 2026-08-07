import React, { useState, useEffect } from 'react';
import { X, Brain, FileText, Target, DollarSign, Building2 } from 'lucide-react';
import { API_BASE } from './apiConfig';

// CRM-style record drawer: opens on a Prospect row.
// Funding profile + matched ICPs + research status + actions.
function DistrictDrawer({ district, resultId, onClose, onResearch, onOpenDossier }) {
  const [full, setFull] = useState(null);
  const [syncState, setSyncState] = useState(null); // null | 'syncing' | 'synced' | error string

  const syncToHubspot = () => {
    if (!resultId || syncState === 'syncing') return;
    setSyncState('syncing');
    fetch(`${API_BASE}/api/hubspot/sync/${resultId}`, { method: 'POST' })
      .then(async res => {
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'Sync failed');
        setSyncState('synced');
      })
      .catch(err => setSyncState(String(err.message || err)));
  };

  useEffect(() => {
    setFull(null);
    if (!district) return;
    fetch(`${API_BASE}/api/funding/CA/${district.ncesid}`)
      .then(res => res.json())
      .then(setFull)
      .catch(() => {});
  }, [district]);

  if (!district) return null;
  const d = full || district;
  const num = (v) => { const f = parseFloat(v); return isNaN(f) || f < 0 ? null : f; };
  const fmt = {
    int: (v) => num(v) != null ? Math.round(num(v)).toLocaleString() : '—',
    pct: (v) => num(v) != null ? `${num(v).toFixed(1)}%` : '—',
    pct100: (v) => num(v) != null ? `${(num(v) * 100).toFixed(1)}%` : '—',
    usd: (v) => num(v) != null ? `$${Math.round(num(v)).toLocaleString()}` : '—',
    usdM: (v) => num(v) != null && num(v) > 0 ? `$${(num(v) / 1e6).toFixed(1)}M` : '—',
  };
  const tags = (district.profile_tags || '').split(' · ').filter(t => t && t !== '—');

  const metrics = [
    ['Enrollment', fmt.int(d.enroll)], ['Schools', fmt.int(d.school_count)],
    ['FRPM', fmt.pct(d.frpm_pct)], ['Poverty', fmt.pct100(d.stpov_pct)],
    ['EL', fmt.pct100(d.ell_pct)], ['SPED', fmt.pct100(d.sped_pct)],
    ['ELA Proficient', fmt.pct(d.ela_proficient_pct)], ['Chronic Absent', fmt.pct(d.chronic_absent_rate)],
    ['Fed $/Pupil', fmt.usd(d.rev_fed_pp)], ['Title I', fmt.usdM(d.title_i_amount)],
    ['LCFF S+C', fmt.usdM(d.lcff_supp_conc_total)], ['Median HH Income', fmt.usd(d.mhi)],
  ];

  return (
    <>
      <div className="drawer-backdrop" onClick={onClose}></div>
      <aside className="district-drawer animate-fade-in">
        <div className="drawer-header">
          <div>
            <h3>{district.dist_name}</h3>
            <div className="drawer-sub">
              {(d.county || '').replace(' County', '')} County · {d.urbanicity || 'CA'}
              {d.website && <> · <a href={d.website.startsWith('http') ? d.website : `https://${d.website}`} target="_blank" rel="noreferrer">website</a></>}
            </div>
          </div>
          <button className="btn-icon" onClick={onClose} aria-label="Close"><X size={18} /></button>
        </div>

        <div className="drawer-section">
          <div className="drawer-section-title"><Target size={13} /> ICP Profiles ({district.profile_count || 0})</div>
          {tags.length > 0 ? (
            <div className="drawer-tags">
              {tags.map(t => <span key={t} className="drawer-tag">{t}</span>)}
            </div>
          ) : <div className="drawer-empty">No target profiles matched</div>}
        </div>

        <div className="drawer-section">
          <div className="drawer-section-title"><DollarSign size={13} /> Funding & Demographics</div>
          <div className="drawer-metrics">
            {metrics.map(([label, value]) => (
              <div key={label} className="drawer-metric">
                <label>{label}</label>
                <span>{value}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="drawer-section">
          <div className="drawer-section-title"><Brain size={13} /> Pipeline Stage</div>
          {resultId
            ? <span className="stage-pill synced">Researched — dossier available</span>
            : <span className="stage-pill">Scored — not yet researched</span>}
        </div>

        <div className="drawer-actions">
          {resultId ? (
            <button className="btn-primary" onClick={() => onOpenDossier(resultId)}>
              <FileText size={15} /> Open Dossier
            </button>
          ) : (
            <button className="btn-primary" onClick={() => onResearch(district)}>
              <Brain size={15} /> Run AI Research
            </button>
          )}
          {resultId ? (
            <button
              className="btn-secondary"
              onClick={syncToHubspot}
              disabled={syncState === 'syncing' || syncState === 'synced'}
            >
              <Building2 size={14} />
              {syncState === 'syncing' ? 'Syncing...' : syncState === 'synced' ? 'Synced to HubSpot ✓' : 'Sync to HubSpot'}
            </button>
          ) : (
            <button className="btn-secondary" disabled title="Research this district first, then sync it to HubSpot">
              <Building2 size={14} /> Not in HubSpot
            </button>
          )}
          {syncState && syncState !== 'syncing' && syncState !== 'synced' && (
            <div className="drawer-empty" style={{ color: '#ffc857' }}>{syncState}</div>
          )}
        </div>
      </aside>
    </>
  );
}

export default DistrictDrawer;
