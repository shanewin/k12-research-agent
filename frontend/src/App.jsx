import React, { useState, useEffect, useRef } from 'react';
import { Search, Brain, FileText, Activity, ShieldCheck, MapPin, Users, Zap, ExternalLink, ChevronDown, DollarSign } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import './App.css';
import { API_BASE, WS_BASE } from './apiConfig';
import ProspectView from './ProspectView';
import DashboardView from './DashboardView';
import DossiersView from './DossiersView';
import DossierPanel from './DossierPanel';
import { LayoutDashboard } from 'lucide-react';

// California-specific build: the platform targets CA districts only.
const STATE = 'CA';

function App() {
  const [district, setDistrict] = useState('');
  const [state, setState] = useState(STATE);
  const [view, setView] = useState('dashboard'); // 'dashboard' | 'prospect' | 'research' | 'dossiers'
  const [dossierId, setDossierId] = useState(null);
  const [fundingRow, setFundingRow] = useState(null);
  const [districts, setDistricts] = useState([]);
  const [isLoadingDistricts, setIsLoadingDistricts] = useState(false);
  const [abortController, setAbortController] = useState(null);
  const [isSearching, setIsSearching] = useState(false);
  const [thinkerLogs, setThinkerLogs] = useState([]);
  const [profile, setProfile] = useState(null);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [filteredDistricts, setFilteredDistricts] = useState([]);
  const [ws, setWs] = useState(null);
  
  const bottomRef = useRef(null);

  useEffect(() => {
    if (district.length > 0) {
      const noiseWords = ["school", "district", "unified", "elementary", "sd", "isd", "usd", "high", "public", "independent"];
      
      const userInputKeywords = district.toLowerCase()
        .replace(/[^\w\s]/g, '')
        .split(/\s+/)
        .filter(word => word.length > 1 && !noiseWords.includes(word));

      const filtered = districts.filter(d => {
        const districtNameLower = d.name.toLowerCase();
        return userInputKeywords.every(keyword => districtNameLower.includes(keyword)) ||
               districtNameLower.includes(district.toLowerCase());
      }).slice(0, 10);

      setFilteredDistricts(filtered);
      setShowSuggestions(true);
    } else if (districts.length > 0) {
      // If empty but suggestions are active (on focus), show first 10
      setFilteredDistricts(districts.slice(0, 10));
    } else {
      setFilteredDistricts([]);
      setShowSuggestions(false);
    }
  }, [district, districts]);

  useEffect(() => {
    if (bottomRef.current) {
      bottomRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [thinkerLogs]);

  // Deep-link support: /?district=Barstow+Unified
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const linkedDistrict = params.get('district');
    if (linkedDistrict && params.get('demo') !== 'true') {
      setDistrict(linkedDistrict);
      setView('research');
    }
  }, []);

  // Prospect table / dashboard -> Research handoff (carries the funding row along)
  const handleProspectResearch = (row) => {
    const name = row.dist_name || row.name;
    setDistrict(name);
    setProfile(null);
    setView('research');
    if (row.enroll !== undefined) {
      setFundingRow(row);
    } else if (row.ncesid || row.leaid) {
      // Partial row (e.g. dashboard hot target) — hydrate from the funding API
      fetch(`${API_BASE}/api/funding/CA/${row.ncesid || row.leaid}`)
        .then(res => res.json())
        .then(setFundingRow)
        .catch(() => setFundingRow(null));
    }
  };

  const openDossier = (id) => {
    setDossierId(id);
    setView('dossiers');
  };

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    if (params.get('demo') === 'true') {
      setDistrict('Demo Unified School District');
      setState('CA');
      
      const mockProfile = {
        district_name: "Demo Unified School District",
        state: "CA",
        signal_strength: "HIGH",
        icp_score: 63,
        buying_profile: {
          style: "Strategic / Innovation-Focused",
          justification: "Recent ESSER funding combined with a push for personalized learning points to a proactive buying stance.",
          recommended_sales_strategy: "Lead with outcomes and pilot success metrics. Focus on how the platform integrates with their existing LMS (Canvas)."
        },
        intelligence_brief: `## Executive Summary
Demo Unified School District presents a **high-value opportunity** with an ICP score of 63.

### Key Signals
* **Recent Leadership Change**: A new Assistant Superintendent of Curriculum was hired 4 months ago.
* **Funding Availability**: Public records indicate $2.4M in allocated but unspent tutoring funds.
* **Strategic Goals**: Their 2025 technology plan heavily emphasizes "personalized, always-on academic support".

### Competitor Landscape
They are currently using a legacy solution (Paper.co) but have expressed public dissatisfaction with engagement rates during the last board meeting.

### Recommended Action
Initiate contact with the Director of Instructional Technology, referencing the recent board meeting notes regarding low engagement metrics.`
      };
      
      setProfile(mockProfile);
    }
  }, []);

  const startResearch = () => {
    if (!district || !state) return;

    // Check if demo is active to prevent overriding the mock report
    const params = new URLSearchParams(window.location.search);
    if (params.get('demo') === 'true') {
      return; 
    }

    setIsSearching(true);
    setThinkerLogs([]);
    setProfile(null);

    // Connect to WebSocket
    const socket = new WebSocket(`${WS_BASE}/ws/research`);
    
    socket.onopen = () => {
      socket.send(JSON.stringify({
        district_name: district,
        state_code: state
      }));
    };

    socket.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === 'thinker' || data.type === 'status') {
        setThinkerLogs(prev => [...prev, { id: Date.now(), msg: data.message, timestamp: new Date().toLocaleTimeString() }]);
      } else if (data.type === 'complete') {
        setProfile(data.profile);
        setIsSearching(false);
        socket.close();
      } else if (data.type === 'error') {
        setThinkerLogs(prev => [...prev, { id: Date.now(), msg: `⚠️ Error: ${data.message}`, type: 'error' }]);
        setIsSearching(false);
      }
    };

    socket.onclose = () => {
      console.info("WebSocket connection closed");
      setIsSearching(false);
    };

    socket.onerror = (err) => {
      console.error("WebSocket error:", err);
      setThinkerLogs(prev => [...prev, { id: Date.now(), msg: "⚠️ WebSocket connection error", type: 'error' }]);
      setIsSearching(false);
    };

    setWs(socket);
  };

  const interruptStateLoading = () => {
    if (abortController) {
      abortController.abort();
      setAbortController(null);
      setState('');
      setIsLoadingDistricts(false);
    }
  };

  return (
    <div className="glass-box-container">
      {/* State Loading Overlay */}
      {isLoadingDistricts && (
        <div className="loading-overlay">
          <div className="loading-content card">
            <div className="pulse-loader"><Brain size={48} /></div>
            <h3>Syncing NCES Database...</h3>
            <p>Fetching active districts for {state}</p>
            <button className="btn-secondary interrupt" onClick={interruptStateLoading}>
              <Zap size={14} />
              Interrupt / Choose New State
            </button>
          </div>
        </div>
      )}

      {/* Header */}
      <header className="main-header">
        <div className="logo">
          <Brain className="accent" size={32} />
          <h1>California K12 <span>Intelligence</span></h1>
        </div>
        <nav className="view-tabs">
          <button
            className={`view-tab ${view === 'dashboard' ? 'active' : ''}`}
            onClick={() => setView('dashboard')}
          >
            <LayoutDashboard size={16} /> Dashboard
          </button>
          <button
            className={`view-tab ${view === 'prospect' ? 'active' : ''}`}
            onClick={() => setView('prospect')}
          >
            <DollarSign size={16} /> Prospect
          </button>
          <button
            className={`view-tab ${view === 'research' ? 'active' : ''}`}
            onClick={() => setView('research')}
          >
            <Brain size={16} /> Research
          </button>
          <button
            className={`view-tab ${view === 'dossiers' ? 'active' : ''}`}
            onClick={() => { setDossierId(null); setView('dossiers'); }}
          >
            <FileText size={16} /> Dossiers
          </button>
        </nav>
        <div className="nav-actions">
          <div className="status-badge">AI LITERACY TOOL · CA</div>
        </div>
      </header>

      <main className="main-content">
        {view === 'dashboard' && (
          <DashboardView
            onGoProspect={() => setView('prospect')}
            onResearchDistrict={handleProspectResearch}
            onOpenDossier={openDossier}
          />
        )}

        {view === 'dossiers' && (
          <DossiersView selectedId={dossierId} onSelect={setDossierId} />
        )}

        {view === 'prospect' && (
          <ProspectView
            onResearch={handleProspectResearch}
            onOpenDossier={openDossier}
          />
        )}

        {view === 'research' && (
        <div className="centered-search">
          <div className="search-card card">
            <div className="form-header">
              <Search className="accent" size={24} />
              <h2>Intelligence Scan Setup</h2>
            </div>

            {fundingRow && fundingRow.dist_name === district && (
              <div className="funding-strip">
                <div className="funding-strip-title">
                  <DollarSign size={14} className="accent" />
                  <span>Funding Profile — {fundingRow.dist_name}</span>
                </div>
                <div className="funding-chips">
                  <div className="funding-chip"><label>Enrollment</label><span>{Math.round(fundingRow.enroll).toLocaleString()}</span></div>
                  <div className="funding-chip"><label>FRPM</label><span>{parseFloat(fundingRow.frpm_pct) >= 0 ? `${parseFloat(fundingRow.frpm_pct).toFixed(1)}%` : '—'}</span></div>
                  <div className="funding-chip"><label>Fed $/Pupil</label><span>${Math.round(fundingRow.rev_fed_pp).toLocaleString()}</span></div>
                  <div className="funding-chip"><label>Title I</label><span>{parseFloat(fundingRow.title_i_amount) > 0 ? `$${(fundingRow.title_i_amount / 1e6).toFixed(1)}M` : '—'}</span></div>
                  <div className="funding-chip"><label>LCFF S+C</label><span>{parseFloat(fundingRow.lcff_supp_conc_total) > 0 ? `$${(fundingRow.lcff_supp_conc_total / 1e6).toFixed(1)}M` : '—'}</span></div>
                  <div className="funding-chip"><label>{(fundingRow.county || '').replace(' County', '')}</label><span>{fundingRow.urbanicity || 'CA'}</span></div>
                </div>
              </div>
            )}

            <div className="form-layout">
              {/* Row 1: District (state is locked to California) */}
              <div className="form-row">
                <div className="field">
                  <label>California School District</label>
                  <div className="autocomplete-wrapper large">
                    <input
                      type="text"
                      placeholder="Search 1,860 California districts..."
                      value={district}
                      onChange={(e) => setDistrict(e.target.value)}
                      onFocus={() => setShowSuggestions(true)}
                      onBlur={() => setTimeout(() => setShowSuggestions(false), 300)}
                      disabled={!state || isLoadingDistricts}
                    />
                    {state && !isLoadingDistricts && (
                      <div className="input-indicator">
                        {district.length > 0 ? `${filteredDistricts.length} results` : `Showing top districts`}
                      </div>
                    )}
                    {showSuggestions && filteredDistricts.length > 0 && (
                      <div className="suggestions-overlay container-card">
                        {filteredDistricts.map((d, idx) => (
                          <div 
                            key={idx} 
                            className="suggestion-item"
                            onClick={() => {
                              setDistrict(d.name);
                              setShowSuggestions(false);
                            }}
                          >
                            <MapPin size={14} className="accent" />
                            <span>{d.name}</span>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              </div>

            </div>

            <div className="form-footer">
              <button 
                className="btn-primary start-btn" 
                onClick={startResearch}
                disabled={isSearching || !district || !state}
              >
                <Zap size={18} />
                {isSearching ? 'Analyzing District...' : 'Launch Intelligence Scan'}
              </button>
            </div>
          </div>

          <div className="mini-thinker card">
            <div className="sidebar-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Activity size={18} className={isSearching ? "accent pulse-loader" : "accent"} />
                <h3>Activity Monitor</h3>
              </div>
              {isSearching && (
                <div className="scanning-badge">
                  <div className="radar-sweep"></div>
                  <span style={{ fontSize: '0.75rem', color: 'var(--accent-color)', fontWeight: '600' }}>AGENT ACTIVE</span>
                </div>
              )}
            </div>
            <div className="logs-container">
              {thinkerLogs.length === 0 && !isSearching && (
                <div className="empty-state">Monitor ready...</div>
              )}
              {thinkerLogs.map(log => (
                <div key={log.id} className={`log-entry ${log.type || ''}`}>
                  <span className="log-time">{log.timestamp}</span>
                  <span className="log-msg">{log.msg}</span>
                </div>
              ))}
              <div ref={bottomRef} />
            </div>
          </div>
        </div>
        )}

        {view === 'research' && profile && <DossierPanel profile={profile} />}
      </main>

    </div>
  );
}

export default App;
