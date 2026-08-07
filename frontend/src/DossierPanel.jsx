import React, { useState } from 'react';
import { FileText, ShieldCheck, MapPin, Users, Send, Copy } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import { API_BASE } from './apiConfig';

// Shared intelligence-dossier renderer (Research view + Dossiers library).
// When resultId is provided, the outreach-sequence generator is available.
function DossierPanel({ profile, resultId, onRefresh }) {
  const [drafting, setDrafting] = useState(false);
  const [draftError, setDraftError] = useState(null);
  if (!profile) return null;
  const contacts = profile.contacts || [];
  const outreach = profile.outreach;

  const draftOutreach = () => {
    setDrafting(true);
    setDraftError(null);
    fetch(`${API_BASE}/api/outreach/${resultId}`, { method: 'POST' })
      .then(async res => {
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'Generation failed');
        onRefresh && onRefresh();
      })
      .catch(err => setDraftError(String(err.message || err)))
      .finally(() => setDrafting(false));
  };
  return (
    <div className="dossier-panel animate-fade-in">
      <div className="dossier-header card">
        <div className="dossier-title">
          <div className="badge strength-high">{profile.signal_strength} STRENGTH</div>
          <h2>{profile.district_name} Intelligence Dossier</h2>
          <div className="meta-row">
            <span className="meta-item"><MapPin size={14} /> {profile.state}</span>
            <span className="meta-item"><Users size={14} /> {profile.icp_score} ICP Score</span>
            {contacts.length > 0 && (
              <span className="meta-item"><Users size={14} /> {contacts.length} contacts</span>
            )}
          </div>
        </div>
        <div className="score-circle">
          <div className="score-value">{profile.icp_score}</div>
          <div className="score-label">ICP</div>
        </div>
      </div>

      <div className="dossier-grid" style={{ gridTemplateColumns: '1fr' }}>
        <div className="card buying-card">
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1.5rem' }}>
            <ShieldCheck size={20} className="accent" />
            <h3 style={{ margin: 0, fontSize: '1.25rem' }}>Buying Profile & Recommendations</h3>
          </div>
          {profile.buying_profile && (
            <div className="profile-details" style={{ display: 'flex', gap: '2rem', flexWrap: 'wrap' }}>
              <div style={{ flex: '1', minWidth: '300px' }}>
                <div className="profile-pill">{profile.buying_profile.style}</div>
                <p><strong>Justification:</strong> {profile.buying_profile.justification}</p>
              </div>
              <div style={{ flex: '1', minWidth: '300px' }}>
                <p style={{ color: 'var(--accent-color)' }}><strong>Sales Strategy:</strong></p>
                <p>{profile.buying_profile.recommended_sales_strategy}</p>
              </div>
            </div>
          )}
        </div>

        {contacts.length > 0 && (
          <div className="card">
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1rem' }}>
              <Users size={20} className="accent" />
              <h3 style={{ margin: 0, fontSize: '1.25rem' }}>Decision Makers</h3>
            </div>
            <div className="contacts-grid">
              {contacts.map((c, i) => (
                <div key={i} className="contact-card">
                  <div className="contact-name">{c.name}</div>
                  <div className="contact-title">{c.title}</div>
                  {c.email && <div className="contact-detail">{c.email}</div>}
                  {c.is_new && <span className="contact-flag">New in role</span>}
                </div>
              ))}
            </div>
          </div>
        )}

        {resultId && (
          <div className="card">
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: outreach ? '1rem' : 0 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                <Send size={20} className="accent" />
                <h3 style={{ margin: 0, fontSize: '1.25rem' }}>Outreach Sequence</h3>
              </div>
              {!outreach && (
                <button className="btn-primary" onClick={draftOutreach} disabled={drafting}>
                  <Send size={14} /> {drafting ? 'Drafting...' : 'Draft Outreach Sequence'}
                </button>
              )}
            </div>
            {draftError && <div className="drawer-empty" style={{ color: '#ffc857', marginTop: '0.5rem' }}>{draftError}</div>}
            {outreach && (
              <>
                {(outreach.suggested_contacts || []).length > 0 && (
                  <div className="outreach-suggestions">
                    <span className="outreach-suggestion-label">Suggested recipients:</span>
                    {outreach.suggested_contacts.map((s, i) => (
                      <span key={i} className="stage-pill" title={s.reason}>{s.name} · {s.title}</span>
                    ))}
                  </div>
                )}
                <div className="outreach-emails">
                  {(outreach.emails || []).map(e => (
                    <div key={e.sequence_number} className="outreach-email">
                      <div className="outreach-email-head">
                        <span className="outreach-seq">#{e.sequence_number}</span>
                        <div className="outreach-subject">{e.subject_line}</div>
                        <button
                          className="btn-icon" title="Copy email body" aria-label="Copy email body"
                          onClick={() => navigator.clipboard.writeText(`Subject: ${e.subject_line}\n\n${e.body}`)}
                        >
                          <Copy size={14} />
                        </button>
                      </div>
                      <div className="outreach-meta">{e.profile} · {e.funding_source}</div>
                      <p className="outreach-body">{e.body}</p>
                    </div>
                  ))}
                </div>
              </>
            )}
          </div>
        )}

        <div className="card summary-card markdown-container" style={{ padding: '2.5rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1rem', borderBottom: '1px solid rgba(255,255,255,0.1)', paddingBottom: '1rem' }}>
            <FileText size={20} className="accent" />
            <h3 style={{ margin: 0, fontSize: '1.25rem' }}>Full Intelligence Brief</h3>
          </div>
          <ReactMarkdown>{profile.intelligence_brief || 'Analyzing...'}</ReactMarkdown>
        </div>
      </div>
    </div>
  );
}

export default DossierPanel;
