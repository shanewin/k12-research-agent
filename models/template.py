from sqlalchemy import Column, Integer, String, JSON
from database import Base

class ProductTemplateModel(Base):
    __tablename__ = "templates"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    slug = Column(String, unique=True, index=True)
    
    # Store all ProductContext fields in a JSON blob for flexibility
    # This includes company_name, product_name, category, keywords, competitors, etc.
    context_data = Column(JSON)
