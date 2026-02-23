import logging
from data_sources.nces import NCESClient
from models.district import DistrictProfile

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_nces_profile():
    nces = NCESClient()
    
    # Test with Fairfax County Public Schools (Large District)
    print("\n--- Testing Fairfax County Public Schools (VA) ---")
    profile = nces.get_district_profile("Fairfax County Public Schools", "VA")
    
    if profile:
        print(f"Name: {profile.district_name}")
        print(f"NCES ID: {profile.nces_id}")
        print(f"Enrollment: {profile.total_enrollment}")
        print(f"Locale: {profile.locale_type}")
        print(f"Grade Span: {profile.grade_span}")
        print(f"Total Revenue: ${profile.total_revenue:,.2f}" if profile.total_revenue else "Total Revenue: N/A")
        print(f"Fed Revenue: ${profile.rev_fed_total:,.2f}" if profile.rev_fed_total else "Fed Revenue: N/A")
        print(f"Per Pupil Exp: ${profile.per_pupil_expenditure:,.2f}" if profile.per_pupil_expenditure else "Per Pupil Exp: N/A")
        
        # Verify 20+ data points availability
        attrs = vars(profile)
        populated = [k for k, v in attrs.items() if v is not None and v != [] and v != {}]
        print(f"\nPopulated data points: {len(populated)}")
        for k in populated[:10]:
            print(f"  - {k}: {attrs[k]}")
    else:
        print("Failed to fetch profile.")

if __name__ == "__main__":
    test_nces_profile()
