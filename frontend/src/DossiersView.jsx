import React, { useState, useEffect } from 'react';
import { FileText, ArrowLeft, Building2 } from 'lucide-react';
import { API_BASE } from './apiConfig';
import DossierPanel from './DossierPanel';

// Library of saved research dossiers (research_results table).
function DossiersView({ selectedId, onSelect }) {
  const [results, setResults] = useState([]);
  const [detail, setDetail] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`${API_BASE}/api/results`)
      .then(res => res.json())
      .then(data => { setResults(data); setLoading(false); })
      .catch(() => setLoading(false));
  }, []);

  const loadDetail = () => {
    if (selectedId == null) { setDetail(null); return; }
    fetch(`${API_BASE}/api/results/${selectedId}`)
      .then(res => res.json())
      .then(setDetail)
      .catch(() => setDetail(null));
  };

  useEffect(loadDetail, [selectedId]);

  if (detail) {
    return (
      <div className="animate-fade-in">
        <button className="btn-secondary" style={{ marginBottom: '1rem' }} onClick={() => onSelect(null)}>
          <ArrowLeft size={14} /> All dossiers
        </button>
        <DossierPanel profile={detail.profile} resultId={detail.id} onRefresh={loadDetail} />
      </div>
    );
  }

  return (
    <div className="card animate-fade-in" style={{ maxWidth: '900px', margin: '0 auto' }}>
      <div className="dash-card-header" style={{ marginBottom: '1rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <FileText size={18} className="accent" />
          <h3 style={{ margin: 0 }}>{loading ? 'Loading...' : `${results.length} Research Dossiers`}</h3>
        </div>
      </div>
      {!loading && results.length === 0 && (
        <div className="empty-state" style={{ padding: '2rem' }}>
          No dossiers yet. Run research on a district from the Prospect view.
        </div>
      )}
      <div className="dash-list">
        {results.map(r => (
          <div key={r.id} className="dash-row" onClick={() => onSelect(r.id)}>
            <span className={`strength-dot ${String(r.signal_strength || '').toLowerCase()}`}></span>
            <div className="dash-row-main">
              <span className="dash-row-title">{r.district_name}, {r.state}</span>
              <span className="dash-row-sub">
                ICP {r.icp_score} · {r.signal_strength} · {new Date(r.created_at).toLocaleDateString()}
              </span>
            </div>
            {r.hubspot_synced
              ? <span className="stage-pill synced"><Building2 size={11} /> In HubSpot</span>
              : <span className="stage-pill">Researched</span>}
          </div>
        ))}
      </div>
    </div>
  );
}

export default DossiersView;
