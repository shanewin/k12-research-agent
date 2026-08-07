from models.district import DistrictProfile
from dataclasses import asdict
import json
import csv
import io

class OutputFormatter:
    @staticmethod
    def to_markdown(profile: DistrictProfile) -> str:
        if not profile.intelligence_brief:
            return "# No brief generated."
            
        enrollment = f"{profile.total_enrollment:,}" if profile.total_enrollment else "N/A"
        revenue = f"${profile.total_revenue:,.0f}" if profile.total_revenue else "$0"
        fed_rev = f"${profile.rev_fed_total:,.0f}" if profile.rev_fed_total else "$0"
        white = f"{profile.enrollment_white_pct:.1f}%" if profile.enrollment_white_pct else "N/A"
        black = f"{profile.enrollment_black_pct:.1f}%" if profile.enrollment_black_pct else "N/A"
        hisp = f"{profile.enrollment_hispanic_pct:.1f}%" if profile.enrollment_hispanic_pct else "N/A"
        asian = f"{profile.enrollment_asian_pct:.1f}%" if profile.enrollment_asian_pct else "N/A"

        md = f"{profile.intelligence_brief}\n\n"
        md += "---\n### DATA APPENDIX (80+ Data Points)\n"
        md += f"**ICP Score:** {profile.icp_score}/100\n"
        md += f"**Total Enrollment:** {enrollment}\n"
        md += f"**Total Revenue:** {revenue} (Fed: {fed_rev})\n"
        md += f"**Demographics**: White: {white} | Black: {black} | Hispanic: {hisp} | Asian: {asian}\n"
        md += f"**Locale:** {profile.locale_type}\n"
        md += f"**Current SIS:** {profile.sis} | **LMS:** {profile.lms}\n"
        md += f"**Decision Makers:** {len(profile.contacts)} identified\n"
        
        if profile.board_meeting_report:
            md += f"**Board Meetings Scanned:** {profile.board_meeting_report.meetings_analyzed} ({profile.board_meeting_report.platform})\n"
            
        return md

    @staticmethod
    def to_json(profile: DistrictProfile) -> str:
        """Exhaustive export of all ~130 potential data points."""
        return json.dumps(asdict(profile), indent=2, default=str)

    @staticmethod
    def to_csv(profile: DistrictProfile) -> str:
        """Flattened export of key data points for spreadsheet analysis."""
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=[
            "district_name", "state", "nces_id", "total_enrollment", "total_revenue", 
            "rev_fed_total", "rev_state_total", "rev_local_total", "per_pupil_expenditure",
            "enrollment_white_pct", "enrollment_black_pct", "enrollment_hispanic_pct", "enrollment_asian_pct",
            "icp_score", "signal_strength", "recommended_action", "sis", "lms", "ecosystem",
            "board_platform", "meetings_analyzed", "timeline_summary"
        ])
        writer.writeheader()
        
        row = {
            "district_name": profile.district_name,
            "state": profile.state,
            "nces_id": profile.nces_id,
            "total_enrollment": profile.total_enrollment,
            "total_revenue": profile.total_revenue,
            "rev_fed_total": profile.rev_fed_total,
            "rev_state_total": profile.rev_state_total,
            "rev_local_total": profile.rev_local_total,
            "per_pupil_expenditure": profile.per_pupil_expenditure,
            "enrollment_white_pct": profile.enrollment_white_pct,
            "enrollment_black_pct": profile.enrollment_black_pct,
            "enrollment_hispanic_pct": profile.enrollment_hispanic_pct,
            "enrollment_asian_pct": profile.enrollment_asian_pct,
            "icp_score": profile.icp_score,
            "signal_strength": profile.signal_strength,
            "recommended_action": profile.recommended_action,
            "sis": profile.sis,
            "lms": profile.lms,
            "ecosystem": profile.ecosystem,
            "board_platform": profile.board_meeting_report.platform if profile.board_meeting_report else "unknown",
            "meetings_analyzed": profile.board_meeting_report.meetings_analyzed if profile.board_meeting_report else 0,
            "timeline_summary": profile.board_meeting_report.timeline_summary if profile.board_meeting_report else ""
        }
        writer.writerow(row)
        return output.getvalue()
