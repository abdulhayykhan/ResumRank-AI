"""
CSV Export Module for Resume Ranking System
============================================

Exports ranking results and summary statistics to CSV format.
Supports both file export and in-memory string export for browser downloads.

Features:
  - Proper CSV formatting with unicode handling
  - Semicolon-separated skills (safer than comma for CSV)
  - In-memory export for direct browser downloads
  - Summary statistics export
  - Automatic directory creation
  - Comprehensive error handling and logging

Functions:
  - format_skills_for_csv(skills) → skill string with "; " separators
  - export_to_csv(ranked_candidates, output_path) → file path
  - get_csv_as_string(ranked_candidates) → CSV string (in-memory)
  - export_summary_csv(summary, output_path) → file path

All functions use type hints and have comprehensive docstrings.
"""

import csv
import logging
import os
from datetime import datetime
from io import StringIO
from typing import Dict, List

try:
    import pandas as pd
except ImportError:
    pd = None

logger = logging.getLogger(__name__)



def export_to_csv(
    ranked_candidates: List[Dict],
    output_path: str = "results/ranking_results.csv"
) -> str:
    """
    Export ranked candidates to a CSV file.
    
    Creates the output directory if it doesn't exist.
    Handles unicode characters in candidate names properly using UTF-8 encoding.
    Returns the full file path of the created CSV file.
    
    CSV columns (in order):
      Rank | Candidate Name | Email | Final Score | Skill Score |
      Experience Score | Years Experience | Matched Skills | Missing Skills |
      Recommendation
    
    Args:
        ranked_candidates: List of candidate dicts (from ranker.assign_ranks()).
                          Each dict should have: rank, candidate_name, email,
                          final_score, skill_score, experience_score,
                          years_of_experience, matched_skills, missing_skills,
                          gap_analysis
        output_path: File path for output CSV.
                    Defaults to "results/ranking_results.csv"
                    Directory is created automatically if missing.
    
    Returns:
        str: Full absolute path to the created CSV file.
             Can be used for frontend download or logging.
    
    Example:
        >>> candidates = [
        ...     {
        ...         "rank": 1,
        ...         "candidate_name": "Alice",
        ...         "email": "alice@example.com",
        ...         "final_score": 92.5,
        ...         "skill_score": 95.0,
        ...         "experience_score": 88.0,
        ...         "years_of_experience": 4.5,
        ...         "matched_skills": ["Python", "React"],
        ...         "missing_skills": ["Docker"],
        ...         "gap_analysis": "Strong match..."
        ...     }
        ... ]
        >>> path = export_to_csv(candidates, "my_results.csv")
        >>> os.path.exists(path)
        True
    """
    if not ranked_candidates:
        logger.warning("No candidates to export")
        return ""
    
    # Ensure output directory exists
    _ensure_output_directory(output_path)
    
    # Get CSV content as string
    csv_content = get_csv_as_string(ranked_candidates)
    
    try:
        # Write CSV file with UTF-8 encoding for unicode support
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            f.write(csv_content)
        
        absolute_path = os.path.abspath(output_path)
        logger.info(f"Exported {len(ranked_candidates)} candidates to {absolute_path}")
        return absolute_path
        
    except Exception as e:
        logger.error(f"Failed to export CSV to {output_path}: {str(e)}")
        raise



def format_skills_for_csv(skills: List[str]) -> str:
    """
    Format a skills list as a semicolon-separated CSV-safe string.
    
    Joins skills with "; " (semicolon + space) separator.
    This is safer for CSV parsing than comma-separated since skills might contain commas.
    Handles None and empty lists gracefully.
    
    Args:
        skills: List of skill strings to format.
               Can be None or empty list.
    
    Returns:
        str: Skills joined with "; " separator.
             Returns empty string if skills is None or empty.
    
    Example:
        >>> format_skills_for_csv(["Python", "React", "SQL"])
        'Python; React; SQL'
        
        >>> format_skills_for_csv([])
        ''
        
        >>> format_skills_for_csv(None)
        ''
        
        >>> format_skills_for_csv(["Java", "Spring Boot", "PostgreSQL"])
        'Java; Spring Boot; PostgreSQL'
    """
    if not skills:
        return ""
    
    # Filter out None/empty values and join with separator
    valid_skills = [str(s).strip() for s in skills if s]
    return "; ".join(valid_skills)



def _ensure_output_directory(output_path: str) -> None:
    """
    Create the output directory if it doesn't exist.
    
    Args:
        output_path: Full file path (e.g., "results/ranking_results.csv")
    """
    output_dir = os.path.dirname(output_path)
    if output_dir and not os.path.exists(output_dir):
        try:
            os.makedirs(output_dir, exist_ok=True)
            logger.debug(f"Created output directory: {output_dir}")
        except Exception as e:
            logger.error(f"Failed to create directory {output_dir}: {str(e)}")
            raise


def get_csv_as_string(ranked_candidates: List[Dict]) -> str:
    """
    Generate CSV content as a string without saving to disk.
    Perfect for streaming to browser or returning via API.
    
    Returns CSV with these columns in order:
      Rank | Candidate Name | Email | Final Score | Skill Score | 
      Experience Score | Years Experience | Matched Skills | Missing Skills | 
      Recommendation
    
    Handles unicode characters in names properly using UTF-8 encoding.
    
    Args:
        ranked_candidates: List of candidate dicts with all scoring data.
                          Should have been ranked by ranker.rank_candidates().
                          Each dict should include:
                            - rank, candidate_name, email, final_score, skill_score,
                              experience_score, years_of_experience, matched_skills,
                              missing_skills, gap_analysis
    
    Returns:
        str: CSV content with proper headers and data rows.
             Empty string if ranked_candidates is empty.
    
    Example:
        >>> candidates = [
        ...     {
        ...         "rank": 1, 
        ...         "candidate_name": "Alice Chen",
        ...         "email": "alice@example.com",
        ...         "final_score": 92.5,
        ...         "skill_score": 95.0,
        ...         "experience_score": 88.0,
        ...         "years_of_experience": 4.5,
        ...         "matched_skills": ["Python", "React"],
        ...         "missing_skills": ["Docker"],
        ...         "gap_analysis": "Strong match..."
        ...     }
        ... ]
        >>> csv_str = get_csv_as_string(candidates)
        >>> "Alice Chen" in csv_str and "92.5" in csv_str
        True
    """
    if not ranked_candidates:
        logger.warning("No candidates provided to get_csv_as_string()")
        return ""
    
    # Use StringIO for in-memory CSV generation
    output = StringIO()
    
    # CSV column headers in exact order
    fieldnames = [
        "Rank",
        "Candidate Name",
        "Email",
        "Final Score",
        "Skill Score",
        "Experience Score",
        "Years Experience",
        "Matched Skills",
        "Missing Skills",
        "Recommendation"
    ]
    
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    
    # Write each candidate row
    for candidate in ranked_candidates:
        row = {
            "Rank": candidate.get("rank", ""),
            "Candidate Name": candidate.get("candidate_name", "Unknown"),
            "Email": candidate.get("email", ""),
            "Final Score": round(candidate.get("final_score", 0), 2),
            "Skill Score": round(candidate.get("skill_score", 0), 2),
            "Experience Score": round(candidate.get("experience_score", 0), 2),
            "Years Experience": candidate.get("years_of_experience", ""),
            "Matched Skills": format_skills_for_csv(candidate.get("matched_skills", [])),
            "Missing Skills": format_skills_for_csv(candidate.get("missing_skills", [])),
            # Truncate gap analysis to first 200 chars for CSV cell size management
            "Recommendation": (candidate.get("gap_analysis", "")[:200] 
                             if candidate.get("gap_analysis") else "")
        }
        writer.writerow(row)
    
    csv_string = output.getvalue()
    logger.debug(f"Generated CSV string for {len(ranked_candidates)} candidates")
    return csv_string



def export_summary_csv(
    summary: Dict,
    output_path: str = "results/ranking_summary.csv"
) -> str:
    """
    Export ranking summary statistics to a CSV file.
    
    Creates a simple 2-column CSV with key-value pairs for easy reading.
    
    CSV structure:
      Metric | Value
      ------|-------
      Total Candidates | 5
      Top Scorer | Alice
      Average Score | 78.5
      Excellent (80+) | 2
      Good (60-79) | 2
      Average (40-59) | 1
      Weak (<40) | 0
      Export Date | 2026-02-27 14:30:45
    
    Args:
        summary: Summary dict from ranker.get_ranking_summary().
                Should have structure:
                {
                  "total_candidates": int,
                  "top_scorer": str,
                  "average_score": float,
                  "score_distribution": {
                    "excellent(80+)": int,
                    "good(60-79)": int,
                    "average(40-59)": int,
                    "weak(<40)": int
                  }
                }
        output_path: File path for summary CSV.
                    Defaults to "results/ranking_summary.csv"
    
    Returns:
        str: Full absolute path to the created summary CSV file.
    
    Example:
        >>> summary = {
        ...     "total_candidates": 5,
        ...     "top_scorer": "Alice",
        ...     "average_score": 78.5,
        ...     "score_distribution": {
        ...         "excellent(80+)": 2,
        ...         "good(60-79)": 2,
        ...         "average(40-59)": 1,
        ...         "weak(<40)": 0
        ...     }
        ... }
        >>> path = export_summary_csv(summary)
        >>> os.path.exists(path)
        True
    """
    if not summary:
        logger.warning("No summary data to export")
        return ""
    
    # Ensure output directory exists
    _ensure_output_directory(output_path)
    
    try:
        # Prepare summary rows
        rows = [
            ["Metric", "Value"],
            ["Total Candidates", summary.get("total_candidates", 0)],
            ["Top Scorer", summary.get("top_scorer", "N/A")],
            ["Average Score", round(summary.get("average_score", 0), 2)],
            ["Excellent (80+)", summary.get("score_distribution", {}).get("excellent(80+)", 0)],
            ["Good (60-79)", summary.get("score_distribution", {}).get("good(60-79)", 0)],
            ["Average (40-59)", summary.get("score_distribution", {}).get("average(40-59)", 0)],
            ["Weak (<40)", summary.get("score_distribution", {}).get("weak(<40)", 0)],
            ["Export Date", datetime.now().strftime("%Y-%m-%d %H:%M:%S")]
        ]
        
        # Write summary CSV using csv module for proper formatting
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerows(rows)
        
        absolute_path = os.path.abspath(output_path)
        logger.info(f"Exported summary statistics to {absolute_path}")
        return absolute_path
        
    except Exception as e:
        logger.error(f"Failed to export summary CSV to {output_path}: {str(e)}")
        raise


# Export public functions
__all__ = [
    "format_skills_for_csv",
    "get_csv_as_string",
    "export_to_csv",
    "export_summary_csv"
]
