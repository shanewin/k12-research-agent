import React from 'react';
import { FileText, ShieldCheck, MapPin, Users } from 'lucide-react';
import ReactMarkdown from 'react-markdown';

// Shared intelligence-dossier renderer (Research view + Dossiers library).
function DossierPanel({ profile }) {
  if (!profile) return null;
  const contacts = profile.contacts || [];
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
