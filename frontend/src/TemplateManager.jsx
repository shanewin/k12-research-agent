import React, { useState } from 'react';
import { X, Save, Trash2, Plus, Sparkles } from 'lucide-react';
import { API_BASE } from './apiConfig';

const TemplateManager = ({ templates, onSave, onDelete, onClose }) => {
  const [formData, setFormData] = useState({
    company_name: '',
    product_name: '',
    product_category: '',
    one_liner: '',
    all_keywords: '',
    direct_competitors: '',
    all_buyer_titles: '',
    ideal_enrollment_min: '',
    ideal_enrollment_max: ''
  });
  
  const [autoFillUrl, setAutoFillUrl] = useState('');
  const [isAutoFilling, setIsAutoFilling] = useState(false);

  const handleAutoFill = async () => {
    if (!autoFillUrl) return;
    setIsAutoFilling(true);
    try {
      const response = await fetch(`${API_BASE}/api/templates/auto-fill`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ website_url: autoFillUrl })
      });
      const data = await response.json();
      if (data.error) {
        alert("Error auto-filling: " + data.error);
      } else {
        setFormData(prev => ({ ...prev, ...data }));
      }
    } catch (err) {
      alert("Error auto-filling template.");
      console.error(err);
    } finally {
      setIsAutoFilling(false);
    }
  };

  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    const keywordsList = (formData.all_keywords || '').split(',').map(s => s.trim()).filter(Boolean);
    const titlesList = (formData.all_buyer_titles || '').split(',').map(s => s.trim()).filter(Boolean);
    const competitorsList = (formData.direct_competitors || '').split(',').map(s => s.trim()).filter(Boolean);

    const template = {
      company_name: formData.company_name,
      product_name: formData.product_name,
      product_category: formData.product_category,
      one_liner: formData.one_liner,
      primary_keywords: keywordsList,
      secondary_keywords: keywordsList,
      board_agenda_triggers: keywordsList,
      rfp_keywords: keywordsList,
      primary_buyer_titles: titlesList,
      secondary_buyer_titles: titlesList,
      direct_competitors: competitorsList,
      ideal_enrollment_min: formData.ideal_enrollment_min ? parseInt(formData.ideal_enrollment_min, 10) : 2000,
      ideal_enrollment_max: formData.ideal_enrollment_max ? parseInt(formData.ideal_enrollment_max, 10) : 150000,
    };
    onSave(template);
    setFormData({
      company_name: '',
      product_name: '',
      product_category: '',
      one_liner: '',
      all_keywords: '',
      direct_competitors: '',
      all_buyer_titles: '',
      ideal_enrollment_min: '',
      ideal_enrollment_max: ''
    });
    setAutoFillUrl('');
  };

  return (
    <div className="modal-overlay">
      <div className="modal-content card">
        <div className="modal-header">
          <h3>Manage Product Templates</h3>
          <button className="btn-icon" onClick={onClose}><X size={20} /></button>
        </div>
        
        <div className="modal-body">
          <section className="current-templates">
            <h4>Existing Templates</h4>
            <div className="template-list">
              {Object.entries(templates).map(([slug, t]) => (
                <div key={slug} className="template-item">
                  <span>{t.product_name || slug}</span>
                  {t.is_custom && (
                    <button className="btn-text danger" onClick={() => onDelete(slug)}>
                      <Trash2 size={16} />
                    </button>
                  )}
                </div>
              ))}
            </div>
          </section>

          <form onSubmit={handleSubmit} className="template-form">
            <div className="autofill-section" style={{ display: 'flex', gap: '10px', marginBottom: '20px', alignItems: 'flex-end' }}>
              <div className="field" style={{ flex: 1, marginBottom: 0 }}>
                <label>Website URL (for AI Auto-Fill)</label>
                <input 
                  value={autoFillUrl} 
                  onChange={(e) => setAutoFillUrl(e.target.value)} 
                />
              </div>
              <button 
                type="button" 
                className="btn-secondary" 
                onClick={handleAutoFill} 
                disabled={isAutoFilling || !autoFillUrl}
                style={{ display: 'flex', alignItems: 'center', gap: '8px', height: 'fit-content', padding: '10px 16px' }}
              >
                <Sparkles size={16} /> 
                {isAutoFilling ? 'Scanning...' : 'Auto-Fill with AI'}
              </button>
            </div>

            <h4>Add New Custom Product</h4>
            <div className="form-grid">
              <div className="field">
                <label>Company Name</label>
                <input name="company_name" value={formData.company_name} onChange={handleChange} required />
              </div>
              <div className="field">
                <label>Product Name</label>
                <input name="product_name" value={formData.product_name} onChange={handleChange} required />
              </div>
              <div className="field">
                <label>Category</label>
                <input name="product_category" value={formData.product_category} onChange={handleChange} required />
              </div>
              <div className="field">
                <label>One Liner</label>
                <input name="one_liner" value={formData.one_liner} onChange={handleChange} required />
              </div>
              <div className="field" style={{ gridColumn: '1 / -1' }}>
                <label>Relevant Keywords & Search Terms (comma separated)</label>
                <input name="all_keywords" value={formData.all_keywords} onChange={handleChange} required />
              </div>
              <div className="field" style={{ gridColumn: '1 / -1' }}>
                <label>Target Buyer Titles (comma separated)</label>
                <input name="all_buyer_titles" value={formData.all_buyer_titles} onChange={handleChange} />
              </div>
              <div className="field">
                <label>Direct Competitors (comma separated)</label>
                <input name="direct_competitors" value={formData.direct_competitors} onChange={handleChange} />
              </div>
              <div className="field" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
                <div>
                  <label>Min Enrollment</label>
                  <input name="ideal_enrollment_min" type="number" value={formData.ideal_enrollment_min} onChange={handleChange} />
                </div>
                <div>
                  <label>Max Enrollment</label>
                  <input name="ideal_enrollment_max" type="number" value={formData.ideal_enrollment_max} onChange={handleChange} />
                </div>
              </div>
            </div>
            <button type="submit" className="btn-primary">
              <Plus size={18} /> Add Template
            </button>
          </form>
        </div>
      </div>
    </div>
  );
};

export default TemplateManager;
