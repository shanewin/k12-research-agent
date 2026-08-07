# Data Additions Checklist

These are the highest-priority data points to add to `ca_district_funding_full.csv` for
the product district qualification. Each one strengthens our ability to identify districts that
**need literacy intervention**, **have funding**, and **are under pressure to act**.

---

## Checklist

- [x] **ELPAC Scores** (English Learner proficiency) — DONE
  - **In simple terms:** ELPAC is a test that only English Learner students take. It checks
    how well they're learning English. We already knew *how many* EL students each district
    has (that's the `ell_enroll` column — we got it back in Step 2 of our pipeline when we
    pulled the CCD Directory data from the `educationdata` R package), but now we also know
    *how well they're doing*. If a district has a lot of EL students who are still at the
    "Beginning" level, that's a district that really needs a literacy tool.
  - **Source:** California Department of Education, through the ETS testing website.
  - **What it is:** California's test that measures how well English Learner students are
    acquiring English. Separate from CAASPP — CAASPP tests reading ability for all students,
    ELPAC tests English proficiency specifically for EL students.
  - **Why it matters:** A district with a lot of EL students AND low ELPAC scores has the
    strongest possible case for spending Title III money on a literacy tool. Right now we
    only know how many EL students a district has — not how well they're doing.
  - **Columns added:** `elpac_well_developed_pct`, `elpac_beginning_pct`, `elpac_tested`
  - **Coverage:** 744 of 1,860 districts have ELPAC data
  - **How we did it:**
    1. Went to the CDE assessment data page: https://www.cde.ca.gov/ds/ad/assessmentdata.asp
    2. Found the Summative ELPAC research files link, which goes to:
       https://caaspp-elpac.ets.org/elpac/ResearchFilesSA?ps=true&lstTestYear=2025&lstTestType=SA&lstCounty=00&lstDistrict=00000
    3. Downloaded the "All Students" CSV file (4MB zip):
       https://caaspp-elpac.ets.org/elpac/researchfiles/sa_elpac2025_1_csv_v1.zip
    4. Unzipped into `data/elpac/`. The main file is `sa_elpac2025_1_csv_v1.txt`
    5. **Important differences from CAASPP:**
       - ELPAC uses **different TypeID codes**: `02` = district (CAASPP uses `6`)
       - ELPAC has **4 performance levels** instead of CAASPP's met/not-met:
         - Level 4 = "Well Developed" (student is proficient in English)
         - Level 3 = "Moderately Developed"
         - Level 2 = "Somewhat Developed"
         - Level 1 = "Beginning" (student is just starting to learn English)
       - Column names use camelCase (e.g., `CountyCode`) instead of spaces (e.g., `County Code`)
    6. Filtered to: TypeID=02 (district-level), Grade=13 (all grades combined) → 959 districts
    7. Merged using same CDE code approach: CountyCode + DistrictCode → match to state_leaid
    8. We kept Level 4 % (well developed — the good news) and Level 1 % (beginning — the
       students who need the most help). A district with high Level 1 % is a strong target.

- [x] **CSI/TSI/ATSI Designation Lists** (school improvement status) — DONE
  - **In simple terms:** The state of California keeps a list of schools that are doing poorly
    and need to get better. These schools are basically on a "you need to fix this" list from
    the government. The important part: schools on this list get *extra money* specifically to
    improve, and they *have to* spend it. This is potentially one of the most valuable data
    points we have — if a district has schools on this list AND low ELA/ELPAC scores, that's
    the perfect storm: they have a literacy problem, they have money earmarked to fix it, and
    they're under pressure from the state to act. That's a very strong target for the product.
  - **Source:** California Department of Education, ESSA Assistance Status files.
  - **What it is:** Schools and districts that California has identified as needing
    improvement based on low performance or equity gaps.
    - CSI = Comprehensive Support and Improvement (the whole school is struggling)
    - TSI = Targeted Support and Improvement (specific student groups are struggling)
    - ATSI = Additional Targeted Support and Improvement (the most severe TSI cases)
  - **Why it matters:** Districts with CSI/TSI schools are **required** to create improvement
    plans and have **dedicated funding** to implement them. Low ELA scores are one of the
    main reasons schools land on these lists. These are highly motivated buyers with money
    earmarked for exactly the kind of tool the product is.
  - **Columns added:** `csi_school_count`, `atsi_school_count`, `tsi_school_count`, `has_improvement_status`
  - **Coverage:** 338 of 1,860 districts have at least one school under improvement status
  - **How we did it:**
    1. Went to: https://www.cde.ca.gov/sp/sw/t1/essaassistdatafiles.asp
    2. Downloaded the 2025-26 ESSA Assistance Status Spreadsheet (XLSX):
       https://www.cde.ca.gov/sp/sw/t1/documents/essaassistance25.xlsx
    3. Saved into `data/csi_tsi/essaassistance25.xlsx`
    4. **Important:** This file is at the **school level** (one row per school, ~10,000 rows),
       not the district level. Each school has an `AssistanceStatus2025` column with values
       like "CSI Low Perform", "CSI Grad", "ATSI", "TSI", or "No Status".
    5. To get district-level data, we **aggregated**: counted how many schools in each
       district have each status. Used the first 7 characters of the 14-character CDS code
       as the district identifier.
    6. Merged using the same CDE code approach (first 7 chars of CDS → match to state_leaid)
    7. Districts not in the ESSA file got 0 for all counts
    8. Example: Los Angeles Unified has 29 CSI schools, 5 ATSI schools, and 32 TSI schools

- [x] **Chronic Absenteeism Rates** — DONE
  - **In simple terms:** This tells us what percentage of students are missing a LOT of school
    (18+ days per year). Kids who miss that much school almost always fall behind in reading.
    And kids who can't read well often stop wanting to go to school — so it becomes a cycle.
    Districts with high absenteeism are actively looking for tools to help, especially ones
    with family engagement features (which the product has).
  - **Source:** California Department of Education, chronic absenteeism data files.
  - **What it is:** The percentage of students who miss 10% or more of school days in a year.
    A student missing ~18+ days out of 180 is "chronically absent."
  - **Why it matters:** High absenteeism and low literacy are strongly linked — kids who
    aren't in school fall behind in reading, and kids who can't read often disengage and
    stop showing up. Districts with high chronic absenteeism are under pressure to fix it
    and are looking for engagement tools. the product's family engagement features are directly
    relevant here.
  - **Columns added:** `chronic_absent_rate`, `chronic_absent_count`
  - **Coverage:** 901 of 1,860 districts (mean rate: 19.1%, median: 16.9%)
  - **How we did it:**
    1. Went to: https://www.cde.ca.gov/ds/ad/filesabd.asp
    2. Downloaded the 2024-25 file (33MB, tab-delimited, latin-1 encoding):
       https://www3.cde.ca.gov/demo-downloads/attendance/chronicabsenteeism25-v2.txt
    3. Saved into `data/absenteeism/chronicabsenteeism25.txt`
    4. **Important:** The file has ~341,000 rows because it breaks down absenteeism by
       reporting category (race, gender, student group), Charter School status (All/Yes/No),
       and DASS status (Dashboard Alternative School Status — All/Yes/No). Each combination
       is a separate row.
    5. To get the overall district rate, we filtered to:
       - `Aggregate Level = 'D'` (district, not school or county)
       - `Reporting Category = 'TA'` (total, all students)
       - `Charter School = 'All'` (includes all schools)
       - `DASS = 'All'` (includes all school types)
    6. That gives us exactly 1 row per district with the overall chronic absenteeism rate
    7. Merged using CDE code (County Code + District Code → state_leaid)

- [x] **Title I Actual Allocations** (dollar amounts per district) — DONE
  - **In simple terms:** Title I is the biggest pot of federal money for schools. The government
    gives it to districts with a lot of students from low-income families, and it's supposed
    to be spent on improving reading and math. Before, we only knew a district's *total*
    federal money (that's the `rev_fed` column — it came from the edfinr finance data in
    Step 1 of our pipeline, which pulls from the F-33 fiscal survey). The F-33 survey reports
    revenue as one lump sum per funding source (federal, state, local) — it doesn't break
    federal money down into Title I vs. IDEA vs. Title III vs. other grants. Now that we
    pulled the actual Title I allocation from the U.S. Department of Education, we know
    exactly how much of that federal money is Title I — so we can tell a sales rep "this
    district has $5 million in Title I funds that can be used for literacy tools."
  - **Source:** U.S. Department of Education, published allocation tables (one Excel file per state).
  - **What it is:** The actual amount of Title I money the federal government allocated to
    each district. Title I is the largest federal education funding program — it targets
    schools with high poverty to improve academic achievement, especially in reading and math.
  - **Why it matters:** Right now we know a district's total federal revenue, but we don't
    know how much of that is specifically Title I. A district getting $15M in Title I has a
    very different buying capacity than one getting $500K — even if their total federal
    revenue looks similar (because the smaller one might get more IDEA or other grants).
  - **Columns added:** `title_i_amount`
  - **Coverage:** 860 of 1,860 districts have Title I allocations > $0 (total: $2.2 billion for CA)
  - **How we did it:**
    1. Went to the US Dept of Education's Title I allocation page:
       https://www.ed.gov/about/ed-overview/budget/estimated-esea-title-i-lea-allocations-fy-2024
    2. Downloaded the California Excel file:
       https://www.ed.gov/media/document/fy2024-esea-title-1-tables-california-109627.xlsx
       (Note: Every state has its own file on that page — same URL pattern with state name)
    3. Saved into `data/title_i/fy2024_title1_california.xlsx`
    4. The file has one sheet with 3 columns: LEA ID, LEA Name, FY 2024 Title I Allocation
    5. **ID mapping:** The LEA ID is 6 digits (e.g., "600001"). Our NCES IDs are 7 digits
       with a leading zero (e.g., "0600001"). So we just prepend "0" to the LEA ID to match.
    6. These are **estimated** allocations — actual amounts may be slightly less due to
       state-level adjustments. But they're close enough for qualifying districts.
    7. Example: Los Angeles Unified gets ~$496M, Fresno Unified ~$84M, most districts
       are in the $100K-$5M range

- [x] **FRPM Data** (Free and Reduced Price Meals) — DONE
  - **In simple terms:** FRPM tells us what percentage of students in a district qualify for
    free or reduced-price lunch. It's basically the best way to measure how many students
    come from low-income families. We already had a poverty number from the Census, but it
    was from 2022 and was missing for half the districts. FRPM is from 2024-25 and it's
    the actual number California uses to decide which districts get extra state funding.
  - **Source:** California Department of Education, FRPM data files (school-level, we added up to district).
  - **What it is:** The count and percentage of students eligible for free or reduced-price
    meals. This is the most commonly used poverty indicator in California schools — more
    current and more granular than the SAIPE poverty estimate we currently have from edfinr.
  - **Why it matters:** FRPM percentage is what California actually uses in its LCFF (Local
    Control Funding Formula) to calculate extra funding for high-poverty districts. A
    district's FRPM rate directly determines how much supplemental state money they get.
    It's also the standard metric districts cite when applying for Title I programs.
  - **Columns added:** `frpm_pct`, `frpm_count`
  - **Coverage:** 911 of 1,860 districts (mean: 58.6%, median: 61.7%)
  - **How we did it:**
    1. Went to: https://www.cde.ca.gov/ds/ad/filessp.asp
    2. Downloaded the 2024-25 FRPM file (2MB Excel):
       https://www.cde.ca.gov/ds/ad/documents/frpm2425.xlsx
    3. Saved into `data/frpm/frpm2425.xlsx`
    4. **Important:** The file is at the **school level** — one row per school (~10,600 rows).
       Each row has enrollment and FRPM-eligible count for that school.
    5. To get district-level data, we **summed** enrollment and FRPM counts across all
       schools in each district, then computed the percentage.
    6. Merged using CDE code (County Code + District Code → state_leaid)
    7. Note: We already had `stpov_pct` (student poverty rate from Census ACS/SAIPE).
       FRPM is more current (2024-25 vs 2022) and is the metric California actually uses
       for funding formulas. Both columns are kept — they measure similar things differently.

- [x] **LCFF Supplemental & Concentration Grants** — DONE
  - **In simple terms:** LCFF is how California gives state money to school districts. Every
    district gets a base amount per student. But districts with more high-need students (EL,
    low-income, foster youth) get **extra money** on top — called supplemental and concentration
    grants. This turned out to be the **single biggest funding source** in our dataset.
    California gave out **$12.8 billion** in LCFF supplemental + concentration grants in
    2024-25 — compared to just $2.2 billion in Title I. For many districts, their LCFF grant
    is 5-10x larger than their Title I money. We were massively understating available funding
    before adding this.
  - **Source:** California Department of Education, LCFF Summary Data (Principal Apportionment).
  - **What it is:** The supplemental grant goes to all districts based on their share of
    high-need students. The concentration grant is extra money for districts where **more than
    55%** of students are high-need. Together, they represent the largest pool of flexible
    funding available to high-need California districts.
  - **Why it matters:** Unlike Title I (which has strict federal rules about how it's spent),
    LCFF money gives districts **more flexibility**. A district can choose to spend LCFF
    supplemental money on a literacy tool without jumping through as many hoops. And the
    districts that get the most LCFF money are the exact same districts the product targets —
    high EL enrollment, high poverty.
  - **Columns added:** `lcff_supplemental`, `lcff_concentration`, `lcff_supp_conc_total`,
    `lcff_unduplicated_pct`
  - **Coverage:** 911 of 1,860 districts
  - **How we did it:**
    1. Went to: https://www.cde.ca.gov/fg/aa/pa/lcffsumdata.asp
    2. Downloaded the 2024-25 LCFF Summary Data (1MB Excel):
       https://www.cde.ca.gov/fg/aa/pa/documents/lcffsummary2425.xlsx
    3. Saved into `data/lcff/lcffsummary2425.xlsx`
    4. The file has multiple sheets (Annual, P-2, P-1). We used the "Annual" sheet which
       has the final certified numbers.
    5. **Important:** The file includes both district-level and school-level rows (for
       charter schools). We filtered to district-level rows only using `School Code = 0000000`.
    6. Key columns: `Total LCFF Supplemental Grant`, `Total LCFF Concentration Grant`,
       and `Unduplicated Pupil Percentage` (the % of students who are EL, FRPM-eligible,
       or foster youth — this is the number that drives the LCFF formula).
    7. Merged using CDE code (County Code + District Code → state_leaid)
    8. Example: Los Angeles Unified gets **$1.47 billion** in LCFF supp+conc (vs $496M
       Title I). Santa Ana Unified gets **$163M** (vs $17M Title I).

---

## What We Already Have (completed)

- [x] **Finance data** (revenue, spending, per-pupil) — from edfinr / F-33 Survey
- [x] **EL & SPED enrollment counts** — from educationdata / CCD Directory
- [x] **ELA proficiency scores** (CAASPP) — from CDE/ETS research files
- [x] **ELPAC scores** (EL proficiency levels) — from CDE/ETS ELPAC research files
- [x] **CSI/TSI/ATSI designations** (school improvement status) — from CDE ESSA assistance files
- [x] **Chronic absenteeism rates** — from CDE absenteeism data files
- [x] **Title I allocations** — from US Dept of Education FY2024 allocation tables
- [x] **FRPM data** (poverty indicator) — from CDE FRPM school-level data, aggregated to district
- [x] **LCFF supplemental & concentration grants** — from CDE LCFF Summary Data
