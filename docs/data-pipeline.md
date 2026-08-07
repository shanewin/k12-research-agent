# Data Enrichment Notes

## Where Does Our Data Come From?

Our dataset (`ca_district_funding_full.csv`) has one row for every school district in
California (1,860 districts) and 67 columns of information about each one. We built it
by pulling data from **nine separate sources** and joining them together.

**Why nine sources?** Because no single database has everything we need. The U.S.
Department of Education collects different types of information through different surveys,
and they end up in different databases — even though they're about the same districts.
The state of California also publishes its own data separately. Think of it like how your
school might keep your grades in one system, your attendance in another, and your health
records in a third. Same student, different systems.

| Source | What It Tells Us | How We Pull It | Think of It As... |
|--------|------------------|----------------|-------------------|
| **F-33 Survey** | How much **money** each district receives and spends — broken down by federal, state, and local funding | R package called `edfinr` | The district's **bank statement** |
| **CCD Directory** | How many **students** are enrolled, and how many are English Learners (EL), Special Education (SPED), etc. | R package called `educationdata` | The district's **roster** |
| **CAASPP** | How well **all students** performed on reading tests — % meeting ELA standards | Downloaded from CDE/ETS website | The district's **report card** |
| **ELPAC** | How well **English Learner students** are learning English — proficiency levels | Downloaded from CDE/ETS website | The EL students' **progress report** |
| **ESSA Assistance** | Which schools are on the state's **"needs improvement" list** (CSI/TSI/ATSI) | Downloaded from CDE website | The district's **warning notice** |
| **Chronic Absenteeism** | What percentage of students are **missing too much school** | Downloaded from CDE website | The district's **attendance record** |
| **Title I Allocations** | Exactly how much **Title I money** each district gets from the federal government | Downloaded from US Dept of Ed website | The district's **Title I check** |
| **FRPM** | What percentage of students come from **low-income families** (free/reduced lunch eligibility) | Downloaded from CDE website | The district's **poverty indicator** |
| **LCFF Summary** | How much **extra state money** each district gets for serving high-need students (EL, low-income, foster youth) | Downloaded from CDE website | The district's **state bonus check** |

Each district has a unique ID number (called an NCES ID — a 7-digit code like "0600001").
We use this ID (or a related state-level ID) to match rows across all sources so we end
up with one combined row per district.

### Important: 1,860 LEAs vs. 1,015 School Districts

Our dataset has **1,860 rows**, but California only has **1,015 traditional school districts**
(per CDE's 2024-25 Fingertip Facts). The difference:

| LEA Type | Count | Data Coverage |
|----------|-------|---------------|
| Traditional school districts | 914 | 98-100% across all data sources |
| Independent charter districts | 941 | **0%** — no ELA, ELPAC, FRPM, LCFF, or Title I data |
| Supervisory unions | 5 | 0% |

**Why do charters have no data?** NCES assigns each independently reporting charter school
its own LEA ID and includes it in the F-33 fiscal survey. So we have their basic finance
and enrollment numbers from edfinr. But charter schools report assessment data (CAASPP,
ELPAC), FRPM, and LCFF funding through their **authorizing district**, not under their own
ID. So when we download CAASPP research files or CDE data, charter results are rolled into
the authorizing district's numbers — they don't appear as separate rows.

The app defaults to excluding charters and non-traditional LEAs (showing only the 914
traditional districts with full data). Users can uncheck this filter to see all 1,860 LEAs.

---

## What's in This Directory

### `ca_district_funding_full.csv`
The main dataset. 1,860 California districts, 67 columns. This is what the app reads.
Everything below describes how this file was built.

### `caaspp_ela/sb_ca2025_all_csv_ela_v1.txt`
Raw CAASPP ELA test results for all of California (2024-25). **CAASPP** stands for
"California Assessment of Student Performance and Progress" — it's the standardized
reading/writing test all California students take. The file has **2 million+ rows**
(475 MB) because it breaks results down by every school, grade, and student group. We
only use a tiny slice: district-level, all students, all grades combined → ~1,013 rows.
Uses carets (`^`) as separators. Downloaded from:
https://caaspp-elpac.ets.org/caaspp/ResearchFileListSB

### `elpac/sa_elpac2025_1_csv_v1.txt`
Raw ELPAC test results (2024-25). **ELPAC** stands for "English Language Proficiency
Assessments for California" — it's the test that only English Learner students take to
measure how well they're learning English. ~72,000 rows, caret-delimited. Downloaded from:
https://caaspp-elpac.ets.org/elpac/ResearchFilesSA

### `csi_tsi/essaassistance25.xlsx`
The 2025-26 ESSA school improvement status list from CDE. Shows which schools are
designated CSI (Comprehensive Support and Improvement), TSI (Targeted Support), or
ATSI (Additional Targeted Support). School-level data (~10,000 rows) that we aggregated
to district level. Downloaded from:
https://www.cde.ca.gov/sp/sw/t1/essaassistdatafiles.asp

### `absenteeism/chronicabsenteeism25.txt`
Chronic absenteeism rates for 2024-25 from CDE. Shows what % of students miss 10%+
of school days. ~341,000 rows (broken down by student group, charter status, etc.) —
we filtered to get one overall rate per district. Tab-delimited, latin-1 encoding.
Downloaded from: https://www.cde.ca.gov/ds/ad/filesabd.asp

### `title_i/fy2024_title1_california.xlsx`
FY 2024 Title I allocation amounts from the U.S. Department of Education. Shows exactly
how many Title I dollars each district receives. Simple 3-column file (~945 rows).
Downloaded from:
https://www.ed.gov/about/ed-overview/budget/estimated-esea-title-i-lea-allocations-fy-2024

### `frpm/frpm2425.xlsx`
Free and Reduced-Price Meal (FRPM) eligibility data for 2024-25 from CDE. Shows what %
of students qualify for free/reduced lunch — this is the poverty indicator California
actually uses for funding formulas. School-level (~10,600 rows) that we summed to district
level. Downloaded from: https://www.cde.ca.gov/ds/ad/filessp.asp

### `lcff/lcffsummary2425.xlsx`
LCFF (Local Control Funding Formula) summary data for 2024-25 from CDE. Shows how much
supplemental and concentration grant money each district receives from the state based on
their share of high-need students (EL, low-income, foster youth). This is the single
largest funding source in our dataset — $12.8 billion statewide, nearly 6x Title I.
Downloaded from: https://www.cde.ca.gov/fg/aa/pa/lcffsumdata.asp

### `DATA_ENRICHMENT_NOTES.md`
This file — documentation of where all the data came from and how to reproduce it.

### `DATA_ADDITIONS_CHECKLIST.md`
Step-by-step record of how we downloaded and merged each of the 5 additional data sources
(ELPAC, CSI/TSI, absenteeism, Title I, FRPM), with plain-English explanations and gotchas.

---

## Current Data File Details

- **File:** `ca_district_funding_full.csv`
- **Rows:** 1,860 California school districts
- **Columns:** 67

| Data | Year | Source |
|------|------|--------|
| Finance (revenue, spending) | 2022 fiscal year | edfinr R package (NCES F-33 Survey) |
| EL & SPED enrollment | 2021 school year | educationdata R package (NCES CCD Directory) |
| ELA test scores | 2024-25 | CAASPP research file (CDE/ETS) |
| ELPAC scores (EL proficiency) | 2024-25 | ELPAC research file (CDE/ETS) |
| CSI/TSI/ATSI status | 2025-26 | ESSA Assistance Status file (CDE) |
| Chronic absenteeism | 2024-25 | Absenteeism data file (CDE) |
| Title I allocations | FY 2024 | Allocation tables (US Dept of Ed) |
| FRPM (poverty indicator) | 2024-25 | FRPM data file (CDE) |
| LCFF supp/conc grants | 2024-25 | LCFF Summary Data (CDE) |

**Why are the years different?** Each source releases data on its own schedule. The
finance survey (F-33) had 2022 as the latest year when we pulled. The CCD Directory had
enrollment data up to 2022, but the EL and SPED fields were empty for 2022 — so we had
to fall back to 2021. The California-specific data (CAASPP, ELPAC, absenteeism, FRPM)
is the most current (2024-25).

---

## R Packages Used

### edfinr (Bellwether Education Partners)
- **What it does:** Makes it easy to pull school district finance data from the F-33
  federal survey. Without this package, you'd have to download raw files from the NCES
  website and clean them yourself.
- **GitHub:** https://github.com/bellwetherorg/edfinr
- **Main function:** `get_finance_data(yr, geo, dataset_type, cpi_adj)`
  - `yr` = year (e.g., "2022")
  - `geo` = state code (e.g., "CA") or "all" for national
  - `dataset_type = "skinny"` → 41 columns (what we use — revenue, spending, poverty, demographics)
  - `dataset_type = "full"` → 89 columns (adds detailed spending breakdowns — how much goes to
    instruction vs. administration vs. technology, etc. We don't use this because it doesn't
    help us identify which districts need literacy tools.)

### educationdata (Urban Institute)
- **What it does:** Makes it easy to pull data from several federal education databases,
  including the CCD (Common Core of Data) which has student enrollment counts.
- **GitHub:** https://github.com/UrbanInstitute/education-data-package-r
- **Why we need it:** The edfinr package gives us money data but NOT student demographic
  counts. To know how many English Learners or Special Ed students a district has, we need
  the CCD Directory — and this package is the easiest way to get it.

---

## Reproducible Data Pipeline

If you need to rebuild the dataset from scratch (or build it for a different state),
follow these steps in order.

### Step 1: Pull Finance Data (edfinr)
*This gives us the money side — how much federal/state/local funding each district gets.*

```r
library(edfinr)

# Replace "CA" with any state code, or "all" for national
# Replace "2022" with desired year, or "2018:2022" for range
finance <- as.data.frame(get_finance_data(yr = "2022", geo = "CA"))
```

**What you get:** A table with 41 columns and one row per district. Includes total revenue,
federal/state/local revenue, per-pupil spending, poverty rates, median household income, etc.
Does NOT include EL or SPED student counts — that comes from a different survey (Step 2).

### Step 2: Pull EL & SPED Enrollment (educationdata)
*This gives us the people side — how many EL and SPED students each district serves.*

```r
library(educationdata)

# fips = state FIPS code. This is a number the Census Bureau assigns to each state.
# California = 6, Texas = 48, New York = 36, Florida = 12
# Full list: https://www.census.gov/library/reference/code-lists/ansi.html

ccd <- get_education_data(
  level = "school-districts",
  source = "ccd",
  topic = "directory",
  filters = list(year = 2021, fips = 6)  # year 2021, California
)

# IMPORTANT: Check that the data actually has EL/SPED values before proceeding.
# Some years have these fields but they're all empty (NA).
cat("EL non-NA:", sum(!is.na(ccd$english_language_learners)), "\n")
cat("SPED non-NA:", sum(!is.na(ccd$spec_ed_students)), "\n")

# If both print 0, try changing the year to 2020 or 2019 until you get data.
```

**What you get:** A table with one row per district. The columns we care about:
- `english_language_learners` — count of EL students in the district
- `spec_ed_students` — count of SPED students in the district
- `teachers_total_fte` — number of full-time-equivalent teachers
- `number_of_schools` — how many schools are in the district
- `guidance_counselors_total_fte` — number of counselors

### Step 3: Merge Finance + Enrollment
*Now we join the money table and the people table using each district's NCES ID.*

```r
# CRITICAL: Both tables have a district ID column — "ncesid" in edfinr and "leaid"
# in educationdata. They're the same IDs (e.g., "0600001") but ONLY if you keep
# them as text strings.
#
# If R converts them to numbers, it strips the leading zero:
#   "0600001" becomes 600001
# Then the join finds zero matches and you get a table full of NAs.
#
# NEVER use as.integer() on these IDs. Keep them as strings.

ccd_subset <- data.frame(
  ncesid = ccd$leaid,  # Keep as string — DO NOT use as.integer()
  sped_enroll = ccd$spec_ed_students,
  ell_enroll = ccd$english_language_learners,
  total_teachers_fte = ccd$teachers_total_fte,
  school_count = ccd$number_of_schools,
  counselors_fte = ccd$guidance_counselors_total_fte,
  stringsAsFactors = FALSE
)

merged <- merge(finance, ccd_subset, by = "ncesid", all.x = TRUE)

# Compute percentages (what fraction of the district's students are EL or SPED)
merged$ell_pct <- merged$ell_enroll / merged$enroll
merged$sped_pct <- merged$sped_enroll / merged$enroll

# Clean up: CCD uses -2 to mean "data not available", which shows up as
# negative enrollment. Replace those with NA.
merged$sped_enroll[!is.na(merged$sped_enroll) & merged$sped_enroll < 0] <- NA

# Verify the merge worked
cat("Districts with EL data:", sum(!is.na(merged$ell_enroll)), "of", nrow(merged), "\n")
cat("Districts with SPED data:", sum(!is.na(merged$sped_enroll)), "of", nrow(merged), "\n")
```

### Step 4: Save the R Output

```r
write.csv(merged, "data/ca_district_funding_full.csv", row.names = FALSE)
```

At this point you have a CSV with 48 columns (41 finance + 7 enrollment).

### Step 5: Add CAASPP ELA Proficiency (Python)
*This gives us the performance side — how well students are doing in reading.*

This step is done in Python (not R) because the CAASPP file is a direct download,
not an R package.

**How to get the raw file:**
1. Go to https://caaspp-elpac.ets.org/caaspp/ResearchFileListSB
2. Download the "All Students" ELA research file for the most recent year
3. It downloads as a zip. Unzip it into `data/caaspp_ela/`
4. The file inside will be named something like `sb_ca2025_all_csv_ela_v1.txt`

**Why we have to filter it:** The raw file has 2 million+ rows because it breaks results
down by every combination of school/district, grade level, and student group. We only want
the **district-wide, all-students, all-grades-combined** ELA result — one number per district.

**How we join it:** CAASPP uses a different ID system than NCES. CAASPP identifies districts
by their CDE code (County Code + District Code, like "0161119"). Our finance data has a
column called `state_leaid` that contains this same code with a "CA-" prefix (like "CA-0161119").
So we strip the "CA-" and match on that.

```python
import pandas as pd

# Load the raw CAASPP file
# - sep="^" because it uses carets (^) instead of commas
# - encoding="latin-1" because it contains special characters that break UTF-8
caaspp = pd.read_csv("data/caaspp_ela/sb_ca2025_all_csv_ela_v1.txt",
    sep="^", encoding="latin-1", dtype=str)

# Filter to get one row per district:
# - Type ID = 6 means "district-level" (not school-level or state-level)
# - Student Group ID = 1 means "all students" (not broken out by race, gender, etc.)
# - Grade = 13 means "all grades combined" (not individual grades 3-8, 11)
# - Test ID = 1 means "ELA" (not math)
dist = caaspp[
    (caaspp["Type ID"] == "6") &
    (caaspp["Student Group ID"] == "1") &
    (caaspp["Grade"] == "13") &
    (caaspp["Test ID"] == "1")
].copy()

# Build the CDE code by combining county code + district code
dist["cde_code"] = dist["County Code"] + dist["District Code"]

# Convert the proficiency columns from text to numbers
dist["ela_proficient_pct"] = pd.to_numeric(dist["Percentage Standard Met and Above"], errors="coerce")
dist["ela_mean_score"] = pd.to_numeric(dist["Mean Scale Score"], errors="coerce")
dist["ela_tested"] = pd.to_numeric(dist["Total Students Tested"], errors="coerce")

# Load our merged finance+enrollment CSV from Step 4
df = pd.read_csv("data/ca_district_funding_full.csv", dtype={"ncesid": str})

# Create a matching CDE code by stripping "CA-" from state_leaid
df["cde_code"] = df["state_leaid"].str.replace("CA-", "")

# Merge on CDE code
df = df.merge(dist[["cde_code","ela_proficient_pct","ela_mean_score","ela_tested"]],
              on="cde_code", how="left")
df = df.drop(columns=["cde_code"])

# Save the CSV (now 51 columns — the remaining 12 are added by later steps)
df.to_csv("data/ca_district_funding_full.csv", index=False)
```

**Result:** 893 of 1,860 districts get ELA proficiency data. The other ~960 districts
are mostly charter schools and very small districts that don't participate in CAASPP testing.

**Important:** CAASPP is California's specific test. Every state has its own assessment
system (Texas uses STAAR, New York uses Regents, etc.). If you expand to another state,
you'll need to find that state's equivalent test data and adjust the filtering/download process.

---

## Full Reproducible Script for Any State (Steps 1-4 in R)

```r
library(edfinr)
library(educationdata)

# ---- CONFIGURE THESE FOR YOUR STATE ----
state_code <- "CA"       # edfinr uses 2-letter state codes
state_fips <- 6          # educationdata uses numeric FIPS codes (CA=6, TX=48, NY=36, FL=12)
finance_yr <- "2022"     # edfinr fiscal year
ccd_yr     <- 2021       # CCD year (usually finance_yr - 1, see gotchas below)
output_file <- "data/ca_district_funding_full.csv"
# -----------------------------------------

# Step 1: Finance data
finance <- as.data.frame(get_finance_data(yr = finance_yr, geo = state_code))

# Step 2: CCD enrollment data
ccd <- get_education_data(
  level = "school-districts",
  source = "ccd",
  topic = "directory",
  filters = list(year = ccd_yr, fips = state_fips)
)

# Verify EL/SPED data exists
el_count <- sum(!is.na(ccd$english_language_learners))
sped_count <- sum(!is.na(ccd$spec_ed_students))
cat("EL data available:", el_count, "\n")
cat("SPED data available:", sped_count, "\n")

if (el_count == 0) {
  warning("No EL data for year ", ccd_yr, ". Try year ", ccd_yr - 1)
}

# Step 3: Subset and rename CCD columns
ccd_subset <- data.frame(
  ncesid = ccd$leaid,  # String — do not convert to integer
  sped_enroll = ccd$spec_ed_students,
  ell_enroll = ccd$english_language_learners,
  total_teachers_fte = ccd$teachers_total_fte,
  school_count = ccd$number_of_schools,
  counselors_fte = ccd$guidance_counselors_total_fte,
  stringsAsFactors = FALSE
)

# Step 4: Merge, clean, save
merged <- merge(finance, ccd_subset, by = "ncesid", all.x = TRUE)
merged$sped_enroll[!is.na(merged$sped_enroll) & merged$sped_enroll < 0] <- NA
merged$ell_pct <- merged$ell_enroll / merged$enroll
merged$sped_pct <- merged$sped_enroll / merged$enroll

cat("Merged rows:", nrow(merged), "\n")
cat("EL matched:", sum(!is.na(merged$ell_enroll)), "\n")
cat("SPED matched:", sum(!is.na(merged$sped_enroll)), "\n")

write.csv(merged, output_file, row.names = FALSE)
cat("Saved to", output_file, "\n")

# Then run the Step 5 Python script to add state-specific test scores
```

---

## Known Gotchas (Things That Will Break If You're Not Careful)

### 1. Leading Zero in District IDs (CRITICAL)
California district IDs start with "06" (e.g., "0600001"). If R or Python reads these
as numbers instead of text, the leading zero gets stripped ("0600001" becomes "600001").
Then when you try to join the two tables, nothing matches because "600001" ≠ "0600001".
**Always read IDs as strings.** In R, use `stringsAsFactors = FALSE`. In Python, use
`dtype={"ncesid": str}`.

### 2. CCD EL/SPED Data May Be Missing for Recent Years
The CCD Directory sometimes publishes a year's data without filling in the EL and SPED
columns. When we built this dataset in March 2026, year 2022 had those columns but every
value was empty (NA). Year 2021 had the data. **Always check that the data is actually
there before merging.** If it's all NA, try the previous year.

### 3. SPED -2 Sentinel Values
The CCD uses the number `-2` to mean "data not available" instead of leaving it blank.
If you don't catch this, you end up with districts showing negative SPED enrollment.
**Replace any negative values with NA after merging.**

### 4. State FIPS Codes vs. State Abbreviations
The two R packages use different state identifiers. edfinr wants "CA", educationdata
wants 6. Common FIPS codes: CA=6, TX=48, NY=36, FL=12, IL=17, PA=42, OH=39.
Full list: https://www.census.gov/library/reference/code-lists/ansi.html

### 5. Coverage Differences Between Sources
edfinr returns 1,860 California districts. The CCD has 2,156. The difference is that
edfinr filters out invalid district types and outliers. Our merge keeps all edfinr
districts and drops unmatched CCD rows — so some small/unusual districts won't have
EL/SPED data.

### 6. Year Alignment (Confusing but Important)
edfinr year "2022" = the 2021-22 fiscal year. CCD year 2021 = the 2021-22 school year.
So edfinr "2022" and CCD "2021" are actually the **same school year**. When expanding
to other states, use `edfinr yr = "2022"` with `educationdata year = 2021` to stay aligned.

---

## What's in ca_district_funding_full.csv (67 columns)

### From edfinr — the "bank statement" (41 columns)
How much money each district has.

- **Identifiers:** ncesid, year, state, dist_name, state_leaid, county, cbsa, urbanicity, schlev, lea_type, lea_type_id, cong_dist
- **Revenue (inflation-adjusted):** rev_total, rev_total_pp, rev_local, rev_local_pp, rev_state, rev_state_pp, rev_fed, rev_fed_pp
- **Revenue (raw dollars):** rev_total_unadj, rev_local_unadj, rev_state_unadj, rev_fed_unadj
- **Expenditure:** exp_cur_pp, rev_exp_pp_diff, exp_cur_st_loc, exp_cur_fed, exp_cur_resa, exp_cur_total
- **Community economics (from Census ACS):** mhi (median household income), mpv (median property value), adult_pop, ba_plus_pop, ba_plus_pct (% with bachelor's degree), total_pop, student_pop, stpov_pop (students in poverty), stpov_pct (student poverty rate)
- **Other:** cpi_sy12 (inflation index), enroll (total enrollment)

### From educationdata CCD — the "roster" (7 columns)
How many students of each type the district serves.

- **sped_enroll** — Number of Special Education students
- **ell_enroll** — Number of English Language Learner students
- **ell_pct** — EL students as a percentage of total enrollment
- **sped_pct** — SPED students as a percentage of total enrollment
- **total_teachers_fte** — Number of full-time-equivalent teachers
- **school_count** — Number of schools in the district
- **counselors_fte** — Number of guidance counselors (FTE)

### From CAASPP — the "report card" (3 columns)
How well all students are performing in reading.

- **ela_proficient_pct** — % of students meeting or exceeding the ELA standard (2024-25)
- **ela_mean_score** — Average ELA scale score across all tested students
- **ela_tested** — How many students took the ELA assessment
- 893 of 1,860 districts have this data

### From ELPAC — the EL students' "progress report" (3 columns)
How well English Learner students specifically are learning English.

- **elpac_well_developed_pct** — % of EL students at Level 4 "Well Developed" (proficient)
- **elpac_beginning_pct** — % of EL students at Level 1 "Beginning" (just starting)
- **elpac_tested** — How many EL students took the ELPAC
- 744 of 1,860 districts have this data

### From ESSA Assistance Status — the "warning notice" (4 columns)
Which districts have schools on the state's improvement list.

- **csi_school_count** — Number of schools in the district designated CSI
- **atsi_school_count** — Number of schools designated ATSI
- **tsi_school_count** — Number of schools designated TSI
- **has_improvement_status** — 1 if the district has any school on any list, 0 if not
- 338 of 1,860 districts have at least one flagged school

### From CDE Absenteeism Data — the "attendance record" (2 columns)
How many students are missing too much school.

- **chronic_absent_rate** — % of students missing 10%+ of school days
- **chronic_absent_count** — Number of chronically absent students
- 901 of 1,860 districts have this data

### From US Dept of Ed — the "Title I check" (1 column)
Exactly how much Title I money each district gets.

- **title_i_amount** — FY 2024 Title I allocation in dollars
- 860 of 1,860 districts have allocations > $0 (total: $2.2 billion for CA)

### From CDE FRPM Data — the "poverty indicator" (2 columns)
What percentage of students come from low-income families.

- **frpm_pct** — % of students eligible for free or reduced-price meals
- **frpm_count** — Number of FRPM-eligible students
- 911 of 1,860 districts have this data
- Note: We also have `stpov_pct` from edfinr (Census ACS poverty estimate). FRPM is more
  current (2024-25 vs 2022) and is the metric California actually uses for funding formulas.

### From CDE LCFF Summary — the "state bonus check" (4 columns)
How much extra state money each district gets for serving high-need students.

- **lcff_supplemental** — Supplemental grant amount (all qualifying districts get this)
- **lcff_concentration** — Concentration grant amount (only districts where 55%+ of students are high-need)
- **lcff_supp_conc_total** — Combined supplemental + concentration total
- **lcff_unduplicated_pct** — % of students who are EL, FRPM-eligible, or foster youth (the number that drives the formula)
- 911 of 1,860 districts have this data
- This is the **largest funding source** in the dataset: $12.8 billion statewide vs $2.2 billion for Title I

---

## Possible Future Data Additions

### Financial Data (answering "where is the money?")

| Data | Where To Get It | Why It Would Help the product |
|------|-----------------|-------------------------|
| **IDEA Part B allocations** | US Dept of Ed (same site as Title I) | Exact dollar amount of special education funding per district. Same approach as our Title I pull — would let a rep say "this district has $3M in IDEA money that can fund literacy tools for SPED students." |
| **Title IV Part A allocations** | US Dept of Ed | Student Support and Academic Enrichment grants. Can be spent on EdTech, safe schools, and well-rounded education. Smaller pot than Title I but directly applicable to literacy tech purchases. |
| **Title II Part A allocations** | US Dept of Ed | Teacher training and professional development money. Districts could use this to fund PD around implementing a new literacy tool — a different angle for the sales pitch. |
| **Title III funding amounts** | CDE or NCES | We currently use EL enrollment count as a rough indicator of Title III funding. Actual dollar amounts would be more precise. |
| **E-Rate funding** | USAC (FCC) open data | Shows which districts have invested in technology infrastructure (networks, devices). A district with strong E-Rate funding already has the tech in place to actually deploy a digital literacy tool — removes a common barrier to adoption. |

### Non-Financial Data (answering "who needs help?")

| Data | Where To Get It | Why It Would Help the product |
|------|-----------------|-------------------------|
| **IDEA disability breakdowns** | OSEP Section 618 data | Tells you how many students have Specific Learning Disabilities (SLD), which includes dyslexia. Useful for targeting literacy intervention specifically to high-dyslexia districts. |
| **Detailed spending breakdowns** | edfinr with `dataset_type = "full"` | 48 more columns showing how districts allocate spending (instruction vs. admin vs. technology, etc.). Could support a "budget efficiency" analysis but doesn't help with the current qualifying logic. |
