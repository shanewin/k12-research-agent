import logging
import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from dataclasses import asdict

from agent import K12ResearchAgent
from config.templates import TEMPLATES
from config.product_context import ProductContext
from database import engine, get_db
from models.template import ProductTemplateModel
from sqlalchemy.orm import Session
from fastapi import Depends
import json

from config.settings import TAVILY_API_KEY, ANTHROPIC_API_KEY
from data_sources.tavily_client import K12TavilyClient
from anthropic import Anthropic
from analysis.local_rag import LocalRAG

# Create database tables
ProductTemplateModel.metadata.create_all(bind=engine)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("k12-api")

app = FastAPI(title="K12 Research Agent API")

# Enable CORS for the React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, restrict this to the frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ResearchRequest(BaseModel):
    district_name: str
    state_code: str
    product_type: str = "ai_teaching"

class AutoFillRequest(BaseModel):
    website_url: str

@app.get("/")
def read_root():
    return {"status": "K12 Research Agent API is online"}

@app.get("/api/templates")
def get_templates(db: Session = Depends(get_db)):
    # Fetch all templates from the database
    all_templates = {}
    db_templates = db.query(ProductTemplateModel).all()
    for t in db_templates:
        all_templates[t.slug] = t.context_data
        all_templates[t.slug]["is_custom"] = True
        all_templates[t.slug]["db_id"] = t.id
        
    return all_templates

@app.post("/api/templates")
def create_template(template_data: dict, db: Session = Depends(get_db)):
    name = template_data.get("product_name", "Unnamed Product")
    slug = name.lower().replace(" ", "_")
    
    # Check if exists
    existing = db.query(ProductTemplateModel).filter(ProductTemplateModel.slug == slug).first()
    if existing:
        existing.context_data = template_data
    else:
        new_template = ProductTemplateModel(
            name=name,
            slug=slug,
            context_data=template_data
        )
        db.add(new_template)
    
    db.commit()
    return {"status": "success", "slug": slug}

@app.post("/api/templates/auto-fill")
def auto_fill_template(request: AutoFillRequest):
    url = request.website_url
    try:
        tavily = K12TavilyClient(api_key=TAVILY_API_KEY)
        client = Anthropic(api_key=ANTHROPIC_API_KEY)
        
        # 1. Scrape URL
        content = ""
        extraction = tavily.extract(urls=[url])
        if extraction and "results" in extraction and extraction["results"]:
            content = extraction["results"][0].get("raw_content", "")
            if not content:
                content = extraction["results"][0].get("content", "")
                
        # 1.5 Fallback Scraper if Tavily failed (e.g. Budget Exhausted)
        if not content:
            logger.info("Tavily extraction empty or failed. Trying fallback scraper.")
            import requests
            import re
            import urllib3
            urllib3.disable_warnings()
            try:
                resp = requests.get(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}, timeout=15, verify=False)
                html = resp.text
                # Clean out script and style tags
                clean_html = re.sub(r'(?is)<(script|style).*?>.*?(</\1>)', '', html)
                # Remove all html tags
                text = re.sub(r'(?is)<[^>]+>', ' ', clean_html)
                # Collapse whitespace
                content = re.sub(r'\s+', ' ', text).strip()
            except Exception as fe:
                logger.error(f"Fallback scrape failed: {fe}")
                
        if not content:
            return {"error": "Failed to extract content from the provided URL. The site might be blocking scrapers or our API budget is exhausted."}
            
        # 2. Extract context using LocalRAG
        documents = [{"content": content, "url": url}]
        # Generic EdTech keywords to find relevant product descriptions
        rag = LocalRAG(keywords=["education", "edtech", "school", "district", "students", "teachers", "learning", "curriculum", "platform", "software"]) 
        
        context = rag.get_context_for_claude(documents, product_category="EdTech", max_tokens_approx=5000)
        
        # 3. Call Claude to extract fields
        system_prompt = """You are an expert EdTech product analyst. Read the provided website text for an EdTech product and extract the following information into a SINGLE, strictly formatted JSON object for the primary product. 
If information is missing, use your best guess based on the context or provide a reasonable default. Do not wrap it in a markdown block, just output raw JSON. Do NOT return multiple JSON objects.

{
  "company_name": "string",
  "product_name": "string",
  "product_category": "string (e.g., SIS, LMS, AI Teaching Assistant)",
  "one_liner": "string (What the product does in one sentence)",
  "all_keywords": "string (comma separated list of relevant keywords and search terms)",
  "all_buyer_titles": "string (comma separated target buyer titles)",
  "direct_competitors": "string (comma separated list of competitors, if discernible, otherwise leave empty)",
  "ideal_enrollment_min": integer (if not specified, default to 2000),
  "ideal_enrollment_max": integer (if not specified, default to 150000)
}"""
        msg = client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=1000,
            temperature=0,
            system=system_prompt,
            messages=[{"role": "user", "content": f"Website context:\n{context}\n\nPlease extract the JSON."}]
        )
        
        result_text = msg.content[0].text.strip()
        
        # Handle cases where Claude might still wrap in markdown or add text
        if "```json" in result_text:
            result_text = result_text.split("```json")[1].split("```")[0].strip()
        elif "```" in result_text:
            result_text = result_text.split("```")[1].strip()
            
        # Use raw_decode to parse the first valid JSON object and ignore trailing text/objects
        start_idx = result_text.find("{")
        if start_idx != -1:
            try:
                decoder = json.JSONDecoder()
                parsed_obj, _ = decoder.raw_decode(result_text[start_idx:])
                return parsed_obj
            except json.JSONDecodeError:
                pass
                
        return json.loads(result_text)
    except Exception as e:
        logger.error(f"Error in auto-fill: {e}")
        return {"error": str(e)}

@app.delete("/api/templates/{slug}")
def delete_template(slug: str, db: Session = Depends(get_db)):
    template = db.query(ProductTemplateModel).filter(ProductTemplateModel.slug == slug).first()
    if template:
        db.delete(template)
        db.commit()
        return {"status": "success"}
    return {"status": "not_found"}, 404

@app.get("/api/districts/{state_code}")
def get_districts(state_code: str):
    from data_sources.nces import NCESClient
    client = NCESClient()
    return client.get_districts_by_state(state_code)

@app.websocket("/ws/research")
async def research_websocket(websocket: WebSocket):
    await websocket.accept()
    logger.info("WebSocket connection established")
    
    try:
        data = await websocket.receive_json()
        logger.info(f"Received research request: {data}")
        district_name = data.get("district_name")
        state_code = data.get("state_code")
        product_type = data.get("product_type")
        
        if not district_name or not state_code:
            await websocket.send_json({"type": "error", "message": "Missing district_name or state_code"})
            return

        # Initialize the agent with the requested product context from the database
        from database import SessionLocal
        db = SessionLocal()
        db_template = db.query(ProductTemplateModel).filter(ProductTemplateModel.slug == product_type).first()
        
        if not db_template:
            db.close()
            logger.warning(f"Product template not found for slug: {product_type}")
            await websocket.send_json({"type": "error", "message": f"Invalid product type: {product_type}"})
            return
            
        context = ProductContext(**db_template.context_data)
        db.close()

        agent = K12ResearchAgent(context)
        
        loop = asyncio.get_running_loop()
        # Define a callback to stream updates back via WebSocket
        def status_callback(msg: str):
            asyncio.run_coroutine_threadsafe(
                websocket.send_json({"type": "thinker", "message": msg}),
                loop
            )

        # Run the blocking agent code in a thread so the event loop can process statuses
        profile = await asyncio.to_thread(agent.research_district, district_name, state_code, status_callback)
        
        # Send final completed profile
        await websocket.send_json({"type": "complete", "profile": as_dict_clean(profile)})
        
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")
    except Exception as e:
        logger.error(f"Error in research: {e}")
        await websocket.send_json({"type": "error", "message": str(e)})

def as_dict_clean(profile):
    # Helper to convert DistrictProfile to a JSON-serializable dict
    # We would use dataclasses.asdict() normally
    return {
        "district_name": profile.district_name,
        "state": profile.state,
        "icp_score": profile.icp_score,
        "signal_strength": profile.signal_strength,
        "recommended_action": profile.recommended_action,
        "intelligence_brief": profile.intelligence_brief,
        "erate": vars(profile.erate_report) if profile.erate_report else None,
        "buying_profile": vars(profile.buying_profile) if profile.buying_profile else None
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
