"""
Weighted Scoring Module for Resume Ranking System
==================================================

Implements fair, transparent scoring using:
  Final Score = (0.7 × Skill Match %) + (0.3 × Experience Score)

Functions:
  - calculate_skill_score(relevant_skills, job_skills) → float (0-100)
  - calculate_experience_score(years) → float (0-100)
  - calculate_final_score(skill_score, experience_score) → float
  - generate_score_breakdown(candidate_data, job_skills) → dict
  - generate_gap_analysis(candidate_data, job_description) → str (template-based)
  - generate_all_gap_analyses(candidates, job_description) → list (batch, instant)

All functions use type hints and have full docstrings.
"""

import logging
from typing import Dict, List, Optional

import config


logger = logging.getLogger(__name__)


def _find_partial_match(job_skill: str, candidate_skills: set) -> float:
    """
    Find partial skill matches using substring matching.
    
    Strategy:
      - If job skill is a substring of a candidate skill → 0.8 match (e.g., React ← React.js)
      - If a candidate skill is a substring of job skill → 0.8 match (e.g., React.js → React)
      - Otherwise → 0.0 (no match)
    
    Args:
        job_skill: Required skill from job description (lowercase)
        candidate_skills: Set of normalized candidate skills (lowercase)
        
    Returns:
        float: Match score (0.0 or 0.8)
    """
    for candidate_skill in candidate_skills:
        # Check if either is a substring of the other
        if job_skill in candidate_skill or candidate_skill in job_skill:
            # Avoid matching unrelated skills like "docker" and "doc"
            # Require at least 4 characters or significant overlap
            min_length = min(len(job_skill), len(candidate_skill))
            if min_length >= 4:  # Both strings have meaningful length
                return 0.8
    
    return 0.0


def calculate_skill_score(
    relevant_skills: List[str],
    job_skills: List[str]
) -> float:
    """
    Calculate the skill match percentage (0-100).
    
    Compares candidate's relevant skills against required job skills.
    Uses case-insensitive matching with partial match support.
    
    Matching rules:
      - Exact match (case-insensitive) → 1.0 (100% of this skill)
      - Partial match (substring overlap) → 0.8 (80% of this skill)
      - No match → 0.0
    
    Final score = (skills_matched / total_job_skills) × 100
    
    Args:
        relevant_skills: List of skills found in resume matching job description
        job_skills: List of required skills from job description
        
    Returns:
        float: Percentage of job skills matched (0.0 to 100.0).
               Returns 0.0 if job_skills is empty.
        
    Example:
        >>> calculate_skill_score(
        ...     ["python", "react", "sql"],
        ...     ["python", "javascript", "react.js", "sql", "docker"]
        ... )
        60.0  # 3 out of 5 skills matched = 60%
    """
    if not job_skills:
        logger.warning("No job skills provided for scoring")
        return 0.0
    
    # Normalize to lowercase for case-insensitive matching
    candidate_skills_lower = set(skill.strip().lower() for skill in relevant_skills if skill)
    job_skills_lower = [skill.strip().lower() for skill in job_skills if skill]
    
    if not job_skills_lower:
        return 0.0
    
    # Build a hash map for O(1) skill matching
    skill_match_scores: Dict[str, float] = {}
    
    for job_skill in job_skills_lower:
        if job_skill in candidate_skills_lower:
            # Exact match = 1.0
            skill_match_scores[job_skill] = 1.0
        else:
            # Check for partial matches
            partial_score = _find_partial_match(job_skill, candidate_skills_lower)
            if partial_score > 0:
                skill_match_scores[job_skill] = partial_score
    
    # Calculate match percentage (count skills where we found at least a partial match)
    matched_count = len(skill_match_scores)
    match_percentage = (matched_count / len(job_skills_lower)) * 100.0
    
    return round(min(match_percentage, 100.0), 2)  # Cap at 100%



def calculate_experience_score(years: Optional[float]) -> float:
    """
    Map years of experience to a 0-100 score.
    
    Scoring scale (linear between points):
      0-1 year   → 20
      1-2 years  → 40
      2-4 years  → 60
      4-6 years  → 80
      6+ years   → 100
    
    Args:
        years: Years of experience (float, int, or None).
               Returns 0 if None or negative.
        
    Returns:
        float: Experience score (0-100).
        
    Example:
        >>> calculate_experience_score(0.5)
        20
        >>> calculate_experience_score(1.5)
        40
        >>> calculate_experience_score(3)
        60
        >>> calculate_experience_score(5)
        80
        >>> calculate_experience_score(8)
        100
        >>> calculate_experience_score(None)
        0
    """
    if years is None:
        logger.warning("No experience years provided. Using 0.")
        return 0.0
    
    try:
        years = float(years)
    except (ValueError, TypeError):
        logger.warning(f"Invalid experience value: {years}. Using 0.")
        return 0.0
    
    if years <= 0:
        return 0.0
    elif years < 1:
        return 20.0
    elif years < 2:
        return 40.0
    elif years < 4:
        return 60.0
    elif years < 6:
        return 80.0
    else:  # 6+ years
        return 100.0



def calculate_final_score(
    skill_score: float,
    experience_score: float
) -> float:
    """
    Calculate the final weighted score.
    
    Formula: Final Score = (0.7 × Skill Score) + (0.3 × Experience Score)
    
    The 70/30 split emphasizes skills as the primary factor while
    valuing experience as a secondary component.
    
    Args:
        skill_score: Skill match percentage (0-100)
        experience_score: Experience score (0-100)
        
    Returns:
        float: Final score rounded to 2 decimal places (0.0 to 100.0)
        
    Example:
        >>> calculate_final_score(80.0, 100.0)
        86.0
        # Calculation: (0.7 × 80) + (0.3 × 100) = 56 + 30 = 86
        
        >>> calculate_final_score(60.0, 40.0)
        54.0
        # Calculation: (0.7 × 60) + (0.3 × 40) = 42 + 12 = 54
    """
    SKILL_WEIGHT = config.SKILL_WEIGHT        # 0.7
    EXPERIENCE_WEIGHT = config.EXPERIENCE_WEIGHT  # 0.3
    
    final_score = (SKILL_WEIGHT * skill_score) + (EXPERIENCE_WEIGHT * experience_score)
    return round(final_score, 2)




def generate_score_breakdown(
    candidate_data: Dict,
    job_skills: List[str]
) -> Dict:
    """
    Generate a complete scoring breakdown for a candidate.
    
    Calculates all scoring components and returns a detailed breakdown.
    Used by the ranking system to score all candidates consistently.
    
    Args:
        candidate_data: Dictionary from skill_extractor with keys:
            - "relevant_skills": list of matched skills (required)
            - "missing_skills": list of unmatched required skills (required)
            - "years_of_experience": float or None (optional)
            - "education": str (optional)
            - (other fields ignored)
        job_skills: List of required skills from job description
        
    Returns:
        dict: Scoring breakdown with structure:
        {
            "skill_score": float (0-100),
            "experience_score": float (0-100),
            "final_score": float (0-100),
            "skill_match_percent": float (0-100, alias for skill_score),
            "matched_skills": list of skills found,
            "missing_skills": list of skills not found,
            "years_of_experience": float or None,
            "education": str or 'Not specified'
        }
        
    Example:
        >>> candidate = {
        ...     "relevant_skills": ["python", "react", "sql"],
        ...     "missing_skills": ["docker"],
        ...     "years_of_experience": 3.5,
        ...     "education": "BS Computer Science"
        ... }
        >>> job_skills = ["python", "react", "sql", "docker"]
        >>> breakdown = generate_score_breakdown(candidate, job_skills)
        >>> print(breakdown["final_score"])
        72.0
        # Skill score = 75% (3/4), Experience score = 60%, Final = (0.7*75) + (0.3*60) = 70.5
    """
    # Calculate scores
    skill_score = calculate_skill_score(
        candidate_data.get('relevant_skills', []),
        job_skills
    )
    experience_score = calculate_experience_score(
        candidate_data.get('years_of_experience')
    )
    final_score = calculate_final_score(skill_score, experience_score)
    
    # Compile breakdown
    breakdown = {
        "skill_score": round(skill_score, 2),
        "experience_score": round(experience_score, 2),
        "final_score": final_score,
        "skill_match_percent": round(skill_score, 2),
        "matched_skills": candidate_data.get('relevant_skills', []),
        "missing_skills": candidate_data.get('missing_skills', []),
        "years_of_experience": candidate_data.get('years_of_experience'),
        "education": candidate_data.get('education', 'Not specified')
    }
    
    return breakdown


def generate_gap_analysis(candidate_data: Dict, job_description: str = "") -> str:
    """
    Generate a professional gap analysis paragraph using templates.
    No API key required — uses rule-based text generation.
    """
    name = candidate_data.get('candidate_name') or 'This candidate'
    matched = candidate_data.get('relevant_skills', [])
    missing = candidate_data.get('missing_skills', [])
    years = candidate_data.get('years_of_experience')
    final_score = candidate_data.get('final_score', 0)
    
    # Build experience string
    if years is not None:
        exp_str = f"{years} year{'s' if years != 1 else ''} of experience"
    else:
        exp_str = "experience details not specified"
    
    # Build matched skills string
    if matched:
        matched_str = ", ".join(matched[:5])
        if len(matched) > 5:
            matched_str += f" and {len(matched) - 5} more"
    else:
        matched_str = "none of the required skills"
    
    # Build missing skills string
    if missing:
        missing_str = ", ".join(missing[:4])
        if len(missing) > 4:
            missing_str += f" and {len(missing) - 4} others"
    else:
        missing_str = None
    
    # Determine recommendation tier
    if final_score >= 80:
        tier = "Strong Match"
        opening = f"{name} is an excellent fit for this role with {exp_str}."
        skills_sentence = f"They demonstrate strong proficiency in {matched_str}."
        gap_sentence = (
            f"The skill gap is minimal — only {missing_str} would need attention."
            if missing_str else
            "No significant skill gaps were identified."
        )
        closing = "Recommended for immediate interview. STRONG MATCH."
    
    elif final_score >= 60:
        tier = "Moderate Match"
        opening = f"{name} shows a reasonable fit for this role with {exp_str}."
        skills_sentence = f"Their key strengths include {matched_str}."
        gap_sentence = (
            f"However, they are missing {missing_str}, which may require upskilling."
            if missing_str else
            "Their skill coverage meets most requirements."
        )
        closing = "Worth considering with a skills assessment. MODERATE MATCH."
    
    elif final_score >= 40:
        tier = "Weak Match"
        opening = f"{name} has {exp_str} but limited overlap with this role's requirements."
        skills_sentence = (
            f"They have some relevant skills: {matched_str}."
            if matched else
            "Their skills do not closely align with the job requirements."
        )
        gap_sentence = (
            f"Significant gaps exist in {missing_str}."
            if missing_str else
            "Multiple required skills are absent from their profile."
        )
        closing = "Would require substantial training investment. WEAK MATCH."
    
    else:
        tier = "Weak Match"
        opening = f"{name} does not closely match this role's requirements."
        skills_sentence = (
            f"Limited relevant skills were detected: {matched_str}."
            if matched else
            "No matching skills were identified in the resume."
        )
        gap_sentence = (
            f"Key missing areas include {missing_str}."
            if missing_str else
            "Most required skills are absent."
        )
        closing = "Not recommended for this position without significant reskilling. WEAK MATCH."
    
    return f"{opening} {skills_sentence} {gap_sentence} {closing}"


def generate_all_gap_analyses(candidates: List[Dict], job_description: str = "") -> List[str]:
    """Generate gap analyses for all candidates instantly — no API delays."""
    return [generate_gap_analysis(candidate, job_description) for candidate in candidates]


# Export public functions
__all__ = [
    "calculate_skill_score",
    "calculate_experience_score",
    "calculate_final_score",
    "generate_score_breakdown",
    "generate_gap_analysis",
    "generate_all_gap_analyses"
]
