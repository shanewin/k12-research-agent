import React, { useState, useEffect } from 'react';
import { Layers, Target, Brain, Users, Building2, Zap, ArrowRight, Activity, FileText, HelpCircle } from 'lucide-react';
import { API_BASE } from './apiConfig';
import MethodologyModal from './MethodologyModal';

// CRM-style landing dashboard: pipeline funnel, hot targets, recent dossiers.
function DashboardView({ onGoProspect, onResearchDistrict, onOpenDossier }) {
  const [data, setData] = useState(null);
  const [showMethod, setShowMethod] = useState(false);
  const [profileDefs, setProfileDefs] = useState(null);

  const openMethodology = () => {
    setShowMethod(true);
    if (!profileDefs && !(data && data.profiles)) {
      // Fallback source for the definitions if the dashboard payload lacks them
      fetch(`${API_BASE}/api/funding/CA`)
        .then(res => res.json())
        .then(d => setProfileDefs(d.profiles || []))
        .catch(() => {});
    }
  };

  useEffect(() => {
    const load = () => fetch(`${API_BASE}/api/dashboard`)
      .then(res => res.json()).then(setData).catch(() => {});
    load();
    const t = setInterval(load, 15000);
    return () => clearInterval(t);
  }, []);

  if (!data) return <div className="empty-state" style={{ padding: '3rem' }}>Loading dashboard...</div>;

  const stages = [
    { label: 'Universe', value: data.universe, icon: Layers, hint: 'CA districts in dataset' },
    { label: 'ICP Targets', value: data.targeted, icon: Target, hint: 'Match ≥1 target profile', info: true },
    { label: 'Researched', value: data.researched, icon: Brain, hint: 'AI dossiers completed' },
    { label: 'Contacts', value: data.contacts_found, icon: Users, hint: 'Decision-makers found' },
    { label: 'In HubSpot', value: data.synced, icon: Building2, hint: 'Synced to CRM' },
  ];
  const fmtM = (v) => { const f = parseFloat(v); return f > 0 ? `$${(f / 1e6).toFixed(1)}M` : '—'; };
  const batchActive = data.batch && data.batch.state !== 'idle';

  return (
    <div className="dashboard-view animate-fade-in">
      {batchActive && (
        <div className="batch-banner" style={{ marginBottom: '1.25rem' }}>
          <div className="radar-sweep"></div>
          <span className="batch-progress">
            Batch research running: {data.batch.done}/{data.batch.total} done
            {data.batch.current ? ` — ${data.batch.current}` : ''}
          </span>
        </div>
      )}

      <div className="pipeline-row">
        {stages.map((s, i) => (
          <React.Fragment key={s.label}>
            <div className="pipeline-stage card">
              <div style={{ display: 'flex', justifyContent: 'space-between', width: '100%' }}>
                <s.icon size={18} className="accent" />
                {s.info && (
                  <button className="btn-icon info-btn" onClick={openMethodology}
                    title="How is this calculated?" aria-label="How is this calculated?">
                    <HelpCircle size={15} />
                  </button>
                )}
              </div>
              <div className="pipeline-value">{s.value.toLocaleString()}</div>
              <div className="pipeline-label">{s.label}</div>
              <div className="pipeline-hint">{s.hint}</div>
            </div>
            {i < stages.length - 1 && <ArrowRight size={16} className="pipeline-arrow" />}
          </React.Fragment>
        ))}
      </div>

      <div className="dashboard-grid">
        <div className="card dash-card">
          <div className="dash-card-header">
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <Zap size={17} className="accent" />
              <h3>Hot Targets</h3>
            </div>
            <button className="btn-secondary dash-link" onClick={onGoProspect}>All targets →</button>
          </div>
          <div className="dash-list">
            {data.hot_targets.map(t => (
              <div key={t.leaid} className="dash-row" onClick={() => onResearchDistrict(t)}>
                <span className={`icp-badge ${t.profile_count >= 4 ? 'hot' : 'warm'}`}>{t.profile_count}</span>
                <div className="dash-row-main">
                  <span className="dash-row-title">{t.name}</span>
                  <span className="dash-row-sub">{(t.county || '').replace(' County', '')} · Title I {fmtM(t.title_i)}</span>
                </div>
                <span className="dash-row-action"><Brain size={13} /> Research</span>
              </div>
            ))}
          </div>
        </div>

        <div className="card dash-card">
          <div className="dash-card-header">
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <FileText size={17} className="accent" />
              <h3>Recent Dossiers</h3>
            </div>
          </div>
          <div className="dash-list">
            {data.recent_results.length === 0 && (
              <div className="empty-state" style={{ padding: '1.5rem' }}>
                No research yet — pick a hot target or run a batch from Prospect.
              </div>
            )}
            {data.recent_results.map(r => (
              <div key={r.id} className="dash-row" onClick={() => onOpenDossier(r.id)}>
                <span className={`strength-dot ${String(r.signal_strength || '').toLowerCase()}`}></span>
                <div className="dash-row-main">
                  <span className="dash-row-title">{r.district_name}</span>
                  <span className="dash-row-sub">ICP {r.icp_score} · {r.signal_strength} · {r.hubspot_synced ? 'In HubSpot' : 'Not synced'}</span>
                </div>
                <span className="dash-row-action">Open →</span>
              </div>
            ))}
          </div>
        </div>

        <div className="card dash-card dash-profiles">
          <div className="dash-card-header">
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <Activity size={17} className="accent" />
              <h3>Target Profile Breakdown</h3>
            </div>
            <button className="btn-secondary dash-link" onClick={openMethodology}>
              <HelpCircle size={13} /> How scoring works
            </button>
          </div>
          <div className="profile-bars">
            {data.profile_breakdown.map(p => (
              <div key={p.label} className="profile-bar-row" title={p.name}>
                <span className="profile-bar-label">{p.label}</span>
                <div className="profile-bar-track">
                  <div className="profile-bar-fill" style={{ width: `${Math.min(100, (p.count / data.targeted) * 100)}%` }}></div>
                </div>
                <span className="profile-bar-count">{p.count}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {showMethod && (
        <MethodologyModal
          profiles={(data && data.profiles) || profileDefs || []}
          counts={data.profile_breakdown}
          onClose={() => setShowMethod(false)}
        />
      )}
    </div>
  );
}

export default DashboardView;
