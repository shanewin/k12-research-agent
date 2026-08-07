import os
import requests
from typing import List, Optional
from models.erate import ErateReport, ErateFundingRequest
from config.product_context import ProductContext

class ErateIntelligence:
    """
    Module for extracting E-Rate funding and RFP data from USAC Open Data (Socrata).
    """
    
    BASE_URL_471 = "https://opendata.usac.org/resource/4vjh-m9v3.json" # Form 471 Dataset
    BASE_URL_470 = "https://opendata.usac.org/resource/jsy6-d5cw.json" # Form 470 Dataset
    
    def __init__(self):
        self.app_token = os.getenv("USAC_APP_TOKEN")
        self.api_key_id = os.getenv("USAC_API_KEY_ID")
        self.api_key_secret = os.getenv("USAC_API_KEY_SECRET")
        self.headers = {
            "X-App-Token": self.app_token
        }
        if self.api_key_id and self.api_key_secret:
            self.auth = (self.api_key_id, self.api_key_secret)
        else:
            self.auth = None

    def get_district_erate_data(self, nces_id: str, district_name: str) -> ErateReport:
        report = ErateReport(status="searching")
        
        # 1. Fetch Form 471 (Funding Requests - Past/Current spending)
        requests_471 = self._fetch_471_data(nces_id)
        
        # 2. Fetch Form 470 (RFP/Bidding - Future intent)
        requests_470 = self._fetch_470_data(nces_id)
        
        all_requests = requests_471 + requests_470
        
        if not all_requests:
            report.status = "not_found"
            return report
            
        report.funding_history = all_requests
        report.status = "complete"
        self._calculate_summary(report)
        
        return report

    def _fetch_471_data(self, nces_id: str) -> List[ErateFundingRequest]:
        # Simple SoQL query for Form 471
        # Note: Fields might vary slightly by dataset version, but nces_id is standard in E-Rate datasets
        params = {
            "$where": f"nces_id = '{nces_id}'",
            "$order": "funding_year DESC",
            "$limit": 50
        }
        
        try:
            response = requests.get(self.BASE_URL_471, headers=self.headers, params=params, auth=self.auth, timeout=30)
            if response.status_code != 200:
                return []
            
            data = response.json()
            requests_list = []
            for item in data:
                requests_list.append(ErateFundingRequest(
                    funding_year=int(item.get('funding_year', 0)),
                    application_number=item.get('application_number', ''),
                    frn=item.get('frn', ''),
                    ben=item.get('ben', ''),
                    organization_name=item.get('organization_name', ''),
                    service_type=item.get('service_type', ''),
                    product_service_description=item.get('product_service_description', ''),
                    vendor_name=item.get('service_provider_name', ''),
                    total_cost=float(item.get('total_cost', 0.0)),
                    funding_commitment_request=float(item.get('funding_commitment_request', 0.0)),
                    status=item.get('status', 'Unknown'),
                    form_type="Form 471"
                ))
            return requests_list
        except Exception:
            return []

    def _fetch_470_data(self, nces_id: str) -> List[ErateFundingRequest]:
        # Simple SoQL query for Form 470
        params = {
            "$where": f"nces_id = '{nces_id}'",
            "$order": "funding_year DESC",
            "$limit": 20
        }
        
        try:
            response = requests.get(self.BASE_URL_470, headers=self.headers, params=params, auth=self.auth, timeout=30)
            if response.status_code != 200:
                return []
            
            data = response.json()
            requests_list = []
            for item in data:
                requests_list.append(ErateFundingRequest(
                    funding_year=int(item.get('funding_year', 0)),
                    application_number=item.get('application_number', ''),
                    frn="N/A (RFP Phase)",
                    ben=item.get('ben', ''),
                    organization_name=item.get('organization_name', ''),
                    service_type=item.get('service_type', ''),
                    product_service_description="RFP for: " + item.get('service_request_description', ''),
                    vendor_name="N/A (Bidding)",
                    total_cost=0.0,
                    funding_commitment_request=0.0,
                    status="Active RFP",
                    form_type="Form 470"
                ))
            return requests_list
        except Exception:
            return []

    def _calculate_summary(self, report: ErateReport):
        recent_year = 2024
        total = 0.0
        rfps = 0
        pendings = 0
        vendors = set()
        
        for req in report.funding_history:
            if req.funding_year >= recent_year:
                total += req.funding_commitment_request
            if req.form_type == "Form 470":
                rfps += 1
            if req.status.lower() in ["pending", "active rfp"]:
                pendings += 1
            if req.vendor_name and req.vendor_name != "N/A (Bidding)":
                vendors.add(req.vendor_name)
        
        report.total_funding_recent = total
        report.active_rfps_count = rfps
        report.pending_requests_count = pendings
        report.key_vendors = list(vendors)[:5]
        
        report.summary = f"Identified {len(report.funding_history)} E-Rate records. Recent funding for 2024+ totals ${total:,.2f}. "
        if rfps > 0:
            report.summary += f"There are {rfps} active RFPs (Form 470s) indicating upcoming purchasing intent."
        else:
            report.summary += "No active RFPs (Form 470s) found for the current window."
