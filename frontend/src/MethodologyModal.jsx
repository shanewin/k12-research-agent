import React from 'react';
import { X, Database, Brain, Target, Building2, ArrowRight } from 'lucide-react';

// "How scoring works" explainer. Opened from the dashboard and Prospect view.
// The profile definitions (rule + sales angle) come from the backend, so this
// stays accurate when someone adapts the rules for their own product.
function MethodologyModal({ profiles, counts, onClose }) {
  const countFor = (label) => {
    const c = (counts || []).find(p => p.label === label);
    return c ? c.count : null;
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="methodology-modal card" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>How districts are scored</h2>
          <button className="btn-icon" onClick={onClose} aria-label="Close"><X size={18} /></button>
        </div>

        <div className="method-layers">
          <div className="method-layer">
            <div className="method-layer-title"><Database size={16} className="accent" /> Layer 1 — Data scoring (free, instant)</div>
            <p>
              Every California district is scored against the six target profiles below using
              <strong> public data only</strong>: state funding (LCFF), federal funding (Title I),
              reading proficiency (CAASPP), English-learner progress (ELPAC), free/reduced meals,
              chronic absenteeism, and special education enrollment. No AI, no API calls — the
              rules run over a bundled dataset the moment the app loads. The ICP badge on each
              district is simply <strong>how many profiles it matches</strong> (0–6).
            </p>
          </div>
          <div className="method-flow">
            <span className="method-step"><Database size={13} /> Score all 1,860</span>
            <ArrowRight size={14} />
            <span className="method-step"><Target size={13} /> Pick targets</span>
            <ArrowRight size={14} />
            <span className="method-step"><Brain size={13} /> AI research the best</span>
            <ArrowRight size={14} />
            <span className="method-step"><Building2 size={13} /> Sync to HubSpot</span>
          </div>
          <div className="method-layer">
            <div className="method-layer-title"><Brain size={16} className="accent" /> Layer 2 — AI deep research (on demand, per district)</div>
            <p>
              Data scoring tells you <strong>who</strong> to look at; it can't tell you what's
              happening inside a district right now. Deep research sends an AI agent to read the
              district's website, board meeting agendas, and local news through your product's
              lens — surfacing decision-makers, active buying signals, and a written brief. The
              final ICP score blends both layers: live signals plus funding fit.
            </p>
          </div>
        </div>

        <h3 className="method-profiles-title">The six target profiles</h3>
        <p className="method-note">
          Each profile is a plain data rule tied to a funding source that could pay for the
          product. These ship tuned for a literacy product — adapt them to your own ICP in
          <code> data_sources/local_funding.py</code>.
        </p>
        <div className="method-profile-list">
          {(profiles || []).map(p => (
            <div key={p.key} className="method-profile">
              <div className="method-profile-head">
                <span className="drawer-tag">{p.name}</span>
                {countFor(p.label) != null && (
                  <span className="method-count">{countFor(p.label)} districts</span>
                )}
              </div>
              {p.rule && <p className="method-rule"><strong>Rule:</strong> {p.rule}</p>}
              {p.angle && <p className="method-angle"><strong>Why it matters:</strong> {p.angle}</p>}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

export default MethodologyModal;
