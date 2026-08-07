from sqlalchemy import Column, Integer, String, JSON, DateTime, Boolean
from sqlalchemy.sql import func
from database import Base

class ResearchResultModel(Base):
    __tablename__ = "research_results"

    id = Column(Integer, primary_key=True, index=True)
    district_name = Column(String, index=True)
    state = Column(String(2), index=True)
    product_type = Column(String, index=True)
    icp_score = Column(Integer, default=0)
    signal_strength = Column(String, default="LOW")
    recommended_action = Column(String, default="MONITOR")

    # Full DistrictProfile dump (contacts, signals, tech profile, e-rate, etc.)
    profile_data = Column(JSON)

    hubspot_synced = Column(Boolean, default=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
