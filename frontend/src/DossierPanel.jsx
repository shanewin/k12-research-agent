import React, { useState } from 'react';
import {
  FileText, ShieldCheck, MapPin, Users, Send, Copy, Zap, DollarSign,
  Landmark, Target, ChevronDown, ChevronRight, TrendingUp, Building2,
} from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import { API_BASE } from './apiConfig';

const num = (v) => { const f = parseFloat(v); return isNaN(f) || f < 0 ? null : f; };
const fmt = {
  int: (v) => num(v) != null ? Math.round(num(v)).toLocaleString() : '—',
  pct: (v) => num(v) != null ? `${num(v).toFixed(1)}%` : '—',
  pct100: (v) => num(v) != null ? `${(num(v) * 100).toFixed(1)}%` : '—',
  usd: (v) => num(v) != null ? `$${Math.round(num(v)).toLocaleString()}` : '—',
  usdM: (v) => num(v) != null && num(v) > 0 ? `$${(num(v) / 1e6).toFixed(1)}M` : '—',
};

function Metric({ label, value, caption }) {
  return (
    <div className="dm-metric">
      <div className="dm-metric-label">{label}</div>
      <div className="dm-metric-value">{value}</div>
      {caption && <div className="dm-metric-caption">{caption}</div>}
    </div>
  );
}

function Section({ icon: Icon, title, count, children, defaultOpen = true, subtitle }) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="card dm-section">
      <button className="dm-section-head" onClick={() => setOpen(!open)}>
        {open ? <ChevronDown size={15} /> : <ChevronRight size={15} />}
        <Icon size={17} className="accent" />
        <h3>{title}</h3>
        {count != null && <span className="dm-count">{count}</span>}
        {subtitle && <span className="dm-subtitle">{subtitle}</span>}
      </button>
      {open && <div className="dm-section-body">{children}</div>}
    </div>
  );
}

function Collapsible({ text, lines = 4 }) {
  const [open, setOpen] = useState(false);
  if (!text) return null;
  const isLong = text.length > 320;
  return (
    <div>
      <p className={`dm-prose ${!open && isLong ? 'dm-clamp' : ''}`} style={{ WebkitLineClamp: lines }}>{text}</p>
      {isLong && (
        <button className="dm-more" onClick={() => setOpen(!open)}>
          {open ? 'Show less' : 'Show more'}
        </button>
      )}
    </div>
  );
}

function DossierPanel({ profile, resultId, onRefresh }) {
  const [drafting, setDrafting] = useState(false);
  const [draftError, setDraftError] = useState(null);
  if (!profile) return null;

  const contacts = profile.contacts || [];
  const outreach = profile.outreach;
  const signals = profile.signals || [];
  const bp = profile.buying_profile;
  const erate = profile.erate_report || {};
  const board = profile.board_meeting_report || {};
  const fp = (profile.metadata || {}).funding_profile || {};
  const tags = (fp.profile_tags || '').split(' · ').filter(t => t && t !== '—');
  const techItems = board.technology_items || [];
  const vendorMentions = board.vendor_mentions || [];

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

  const strengthClass = String(profile.signal_strength || '').toLowerCase();

  return (
    <div className="dossier-panel animate-fade-in">
      {/* Header */}
      <div className="dossier-header card">
        <div className="dossier-title">
          <div className={`badge strength-${strengthClass}`}>
            {profile.signal_strength} SIGNAL · {profile.recommended_action}
          </div>
          <h2>{profile.district_name}</h2>
          <div className="meta-row">
            <span className="meta-item"><MapPin size={14} /> {fp.county || profile.county || profile.state}</span>
            <span className="meta-item"><Building2 size={14} /> {fmt.int(profile.number_of_schools)} schools</span>
            <span className="meta-item"><Users size={14} /> {contacts.length} contacts</span>
            {profile.website_url && (
              <a className="meta-item" href={profile.website_url} target="_blank" rel="noreferrer">
                {profile.website_url.replace(/^https?:\/\/(www\.)?/, '').replace(/\/$/, '')}
              </a>
            )}
          </div>
          {tags.length > 0 && (
            <div className="dm-tags">
              {tags.map(t => <span key={t} className="drawer-tag"><Target size={10} /> {t}</span>)}
            </div>
          )}
        </div>
        <div className="score-circle">
          <div className="score-value">{profile.icp_score}</div>
          <div className="score-label">ICP</div>
        </div>
      </div>

      {/* At a glance */}
      <div className="card dm-metrics">
        <Metric label="Enrollment" value={fmt.int(profile.total_enrollment)} caption="Total K-12 students" />
        <Metric label="Reading Proficiency" value={fmt.pct(fp.ela_proficient_pct)} caption="Meeting ELA standard (CAASPP)" />
        <Metric label="FRPM Rate" value={fmt.pct(fp.frpm_pct)} caption="Free/reduced meals — poverty proxy" />
        <Metric label="Chronic Absence" value={fmt.pct(fp.chronic_absent_rate)} caption="Missing 10%+ of school year" />
        <Metric label="Title I" value={fmt.usdM(fp.title_i_amount)} caption="Federal supplemental instruction" />
        <Metric label="LCFF Supp+Conc" value={fmt.usdM(fp.lcff_supp_conc_total)} caption="CA high-need student funding" />
      </div>

      {/* Buying signals — the reason to call */}
      {signals.length > 0 && (
        <Section icon={Zap} title="Buying Signals" count={signals.length}>
          <div className="dm-list">
            {signals.map((s, i) => (
              <div key={i} className="dm-item">
                <span className={`dm-strength ${String(s.strength || '').toLowerCase()}`}>{s.strength}</span>
                <div className="dm-item-body">
                  <div className="dm-item-title">{s.title}</div>
                  {s.detail && <div className="dm-item-detail">{s.detail}</div>}
                  <div className="dm-item-meta">
                    {s.signal_type}
                    {s.source_url && <> · <a href={s.source_url} target="_blank" rel="noreferrer">source</a></>}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </Section>
      )}

      {/* Procurement behaviour */}
      {bp && (
        <Section icon={ShieldCheck} title="Procurement Profile" subtitle={bp.style}>
          <div className="dm-inline-metrics">
            <Metric label="Velocity" value={bp.procurement_velocity || '—'} />
            <Metric label="Price Sensitivity" value={bp.price_sensitivity_score ?? '—'} caption="0 = premium buyer" />
            <Metric label="Vendor Loyalty" value={bp.vendor_loyalty_score ?? '—'} caption="100 = sticks with incumbents" />
            <Metric label="Confidence" value={bp.confidence || '—'} caption="Evidence quality" />
          </div>
          {(bp.key_procurement_findings || []).length > 0 && (
            <ul className="dm-bullets">
              {bp.key_procurement_findings.map((f, i) => <li key={i}>{f}</li>)}
            </ul>
          )}
          {bp.recommended_sales_strategy && (
            <div className="dm-strategy">
              <div className="dm-strategy-label">Recommended sales strategy</div>
              <Collapsible text={bp.recommended_sales_strategy} />
            </div>
          )}
          {bp.justification && (
            <div className="dm-strategy">
              <div className="dm-strategy-label">Evidence</div>
              <Collapsible text={bp.justification} />
            </div>
          )}
        </Section>
      )}

      {/* E-Rate procurement history */}
      {erate.status === 'complete' && (
        <Section icon={Landmark} title="E-Rate Procurement History"
                 count={(erate.funding_history || []).length} defaultOpen={false}>
          <div className="dm-inline-metrics">
            <Metric label="Recent Funding" value={fmt.usdM(erate.total_funding_recent)} caption="Requested, latest years" />
            <Metric label="Form 470 Postings" value={erate.active_rfps_count ?? 0} caption="Competitive bidding activity" />
            <Metric label="Pending Requests" value={erate.pending_requests_count ?? 0} caption="Awaiting commitment" />
            <Metric label="Billed Entity" value={erate.ben || '—'} caption="USAC identifier" />
          </div>
          {(erate.key_vendors || []).length > 0 && (
            <div className="dm-vendors">
              <span className="dm-metric-label">Incumbent vendors</span>
              <div className="dm-tags">
                {erate.key_vendors.map(v => <span key={v} className="drawer-tag">{v}</span>)}
              </div>
            </div>
          )}
        </Section>
      )}

      {/* Board activity */}
      {(techItems.length > 0 || vendorMentions.length > 0) && (
        <Section icon={TrendingUp} title="Board Meeting Activity"
                 count={techItems.length + vendorMentions.length} defaultOpen={false}
                 subtitle={board.platform ? `${board.meetings_analyzed} meetings · ${board.platform}` : null}>
          <div className="dm-list">
            {techItems.map((t, i) => (
              <div key={`t${i}`} className="dm-item">
                <span className={`dm-strength ${String(t.signal_strength || '').toLowerCase()}`}>{t.signal_strength}</span>
                <div className="dm-item-body">
                  <div className="dm-item-title">{t.title || t.description}</div>
                  {t.title && t.description && <div className="dm-item-detail">{t.description}</div>}
                  {t.meeting_date && <div className="dm-item-meta">{t.meeting_date}</div>}
                </div>
              </div>
            ))}
            {vendorMentions.map((v, i) => (
              <div key={`v${i}`} className="dm-item">
                <span className="dm-strength">VENDOR</span>
                <div className="dm-item-body">
                  <div className="dm-item-title">{v.vendor_name}</div>
                  {v.context && <div className="dm-item-detail">{v.context}</div>}
                </div>
              </div>
            ))}
          </div>
        </Section>
      )}

      {/* Decision makers */}
      {contacts.length > 0 && (
        <Section icon={Users} title="Decision Makers" count={contacts.length}>
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
        </Section>
      )}

      {/* Outreach */}
      {resultId && (
        <Section icon={Send} title="Outreach Sequence" count={outreach ? (outreach.emails || []).length : null}>
          {!outreach && (
            <div className="dm-empty-action">
              <span>Generate a profile-driven email sequence from this research.</span>
              <button className="btn-primary" onClick={draftOutreach} disabled={drafting}>
                <Send size={14} /> {drafting ? 'Drafting...' : 'Draft Outreach Sequence'}
              </button>
            </div>
          )}
          {draftError && <div className="drawer-empty" style={{ color: '#ffc857' }}>{draftError}</div>}
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
                      <button className="btn-icon" title="Copy email" aria-label="Copy email"
                        onClick={() => navigator.clipboard.writeText(`Subject: ${e.subject_line}\n\n${e.body}`)}>
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
        </Section>
      )}

      {/* Full brief */}
      <Section icon={FileText} title="Full Intelligence Brief" defaultOpen={false}>
        <div className="markdown-container">
          <ReactMarkdown>{profile.intelligence_brief || 'No brief generated.'}</ReactMarkdown>
        </div>
      </Section>
    </div>
  );
}

export default DossierPanel;
