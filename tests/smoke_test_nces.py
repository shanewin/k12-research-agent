from data_sources.nces import NCESClient
import logging

logging.basicConfig(level=logging.INFO)

def test_nces():
    client = NCESClient()
    # Test with Fairfax County Public Schools (VA, FIPS 51)
    district = client.get_district("Fairfax County Public Schools", "51")
    if district:
        print(f"Name: {district.get('lea_name')}")
        print(f"LEAID: {district.get('leaid')}")
        enrollment = district.get('enrollment_detail')
        if enrollment:
            print(f"Enrollment: {enrollment.get('enrollment')}")
        else:
            print("Enrollment data not available")
        
        finance = district.get('finance')
        if finance:
            print(f"Finance (Total Rev): {finance.get('rev_total')}")
        else:
            print("Finance data not available")
    else:
        print("District not found")

if __name__ == "__main__":
    test_nces()
