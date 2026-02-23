import React, { useState, useEffect, useRef } from 'react';
import { Search, Brain, FileText, Activity, ShieldCheck, MapPin, Users, Zap, ExternalLink, ChevronDown, Settings, Plus } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import './App.css';
import TemplateManager from './TemplateManager';

const STATES = [
  "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA", 
  "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD", 
  "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ", 
  "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC", 
  "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY", "DC"
].sort();

function App() {
  const [district, setDistrict] = useState('');
  const [state, setState] = useState('');
  const [districts, setDistricts] = useState([]);
  const [isLoadingDistricts, setIsLoadingDistricts] = useState(false);
  const [abortController, setAbortController] = useState(null);
  const [productType, setProductType] = useState('');
  const [templates, setTemplates] = useState({});
  const [showTemplateManager, setShowTemplateManager] = useState(false);
  const [isSearching, setIsSearching] = useState(false);
  const [thinkerLogs, setThinkerLogs] = useState([]);
  const [profile, setProfile] = useState(null);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [filteredDistricts, setFilteredDistricts] = useState([]);
  const [ws, setWs] = useState(null);
  
  const bottomRef = useRef(null);

  useEffect(() => {
    fetchTemplates();
  }, []);

  useEffect(() => {
    if (state && state.length === 2) {
      const controller = new AbortController();
      setAbortController(controller);
      setIsLoadingDistricts(true);
      
      fetch(`http://localhost:8000/api/districts/${state}`, { signal: controller.signal })
        .then(res => res.json())
        .then(data => {
          console.log(`Fetched ${data.length} districts for ${state}`);
          setDistricts(data);
          setFilteredDistricts([]);
          setIsLoadingDistricts(false);
          setAbortController(null);
        })
        .catch(err => {
          if (err.name === 'AbortError') {
            console.log('Fetch aborted');
          } else {
            console.error("Error fetching districts:", err);
          }
          setIsLoadingDistricts(false);
          setAbortController(null);
        });
    } else {
      setDistricts([]);
      setFilteredDistricts([]);
    }
  }, [state]);

  const fetchTemplates = () => {
    fetch('http://localhost:8000/api/templates')
      .then(res => res.json())
      .then(data => {
        setTemplates(data);
        // If current productType is empty and we have templates, select the first one
        const slugs = Object.keys(data);
        if (slugs.length > 0 && !data[productType]) {
          setProductType(slugs[0]);
        }
      })
      .catch(err => console.error("Error fetching templates:", err));
  };

  const handleSaveTemplate = (template) => {
    fetch('http://localhost:8000/api/templates', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(template)
    })
      .then(res => res.json())
      .then(() => {
        fetchTemplates();
        setShowTemplateManager(false);
      });
  };

  const handleDeleteTemplate = (slug) => {
    fetch(`http://localhost:8000/api/templates/${slug}`, {
      method: 'DELETE'
    })
      .then(res => res.json())
      .then(() => fetchTemplates());
  };

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

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    if (params.get('demo') === 'true') {
      setDistrict('Demo Unified School District');
      setState('CA');
      setProductType('k12-tutoring-platform');
      
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
    const socket = new WebSocket('ws://localhost:8000/ws/research');
    
    socket.onopen = () => {
      socket.send(JSON.stringify({
        district_name: district,
        state_code: state,
        product_type: productType
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
          <h1>K12 Research <span>Agent</span></h1>
        </div>
        <div className="nav-actions">
          <button className="btn-icon-labeled" onClick={() => setShowTemplateManager(true)}>
            <Settings size={18} />
            <span>Product Templates</span>
          </button>
          <div className="status-badge">V1.1 ACTIVE</div>
        </div>
      </header>

      <main className="main-content">
        <div className="centered-search">
          <div className="search-card card">
            <div className="form-header">
              <Search className="accent" size={24} />
              <h2>Intelligence Scan Setup</h2>
            </div>
            
            <div className="form-layout">
              {/* Row 1: State */}
              <div className="form-row">
                <div className="field">
                  <label>1. Target State</label>
                  <div className="select-wrapper large">
                    <select 
                      value={state}
                      onChange={(e) => setState(e.target.value)}
                      className="custom-select"
                    >
                      <option value="">Select a State...</option>
                      {STATES.map(s => (
                        <option key={s} value={s}>{s}</option>
                      ))}
                    </select>
                    <ChevronDown className="select-icon" size={16} />
                  </div>
                </div>
              </div>

              {/* Row 2: District */}
              <div className="form-row">
                <div className="field">
                  <label>2. School District</label>
                  <div className="autocomplete-wrapper large">
                    <input 
                      type="text" 
                      placeholder={state ? `Search ${state} districts...` : "Select a state first"}
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

              {/* Row 3: Product */}
              <div className="form-row">
                <div className="field">
                  <label>3. Research Lens (Product Type)</label>
                  <div className="select-row">
                    <div className="select-wrapper large" style={{ flex: 1 }}>
                      <select 
                        value={productType}
                        onChange={(e) => setProductType(e.target.value)}
                        className="custom-select"
                      >
                        {Object.entries(templates).map(([slug, t]) => (
                          <option key={slug} value={slug}>{t.product_name || slug}</option>
                        ))}
                      </select>
                      <ChevronDown className="select-icon" size={16} />
                    </div>
                    <button 
                      type="button"
                      className="btn-secondary add-custom" 
                      onClick={() => setShowTemplateManager(true)}
                    >
                      <Plus size={16} />
                      Add Custom
                    </button>
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

        {profile && (
          <div className="dossier-panel animate-fade-in">
            <div className="dossier-header card">
              <div className="dossier-title">
                <div className="badge strength-high">{profile.signal_strength} STRENGTH</div>
                <h2>{profile.district_name} Intelligence Dossier</h2>
                <div className="meta-row">
                  <span className="meta-item"><MapPin size={14} /> {profile.state}</span>
                  <span className="meta-item"><Users size={14} /> {profile.icp_score} ICP Score</span>
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

              <div className="card summary-card markdown-container" style={{ padding: '2.5rem' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1rem', borderBottom: '1px solid rgba(255,255,255,0.1)', paddingBottom: '1rem' }}>
                  <FileText size={20} className="accent" />
                  <h3 style={{ margin: 0, fontSize: '1.25rem' }}>Full Intelligence Brief</h3>
                </div>
                <ReactMarkdown>{profile.intelligence_brief || 'Analyzing...'}</ReactMarkdown>
              </div>
            </div>
          </div>
        )}
      </main>

      {showTemplateManager && (
        <TemplateManager 
          templates={templates}
          onSave={handleSaveTemplate}
          onDelete={handleDeleteTemplate}
          onClose={() => setShowTemplateManager(false)}
        />
      )}
    </div>
  );
}

export default App;
