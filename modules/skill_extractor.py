"""
Skill Extraction Module — No API Key Edition

Extracts structured information (skills, experience, education) from resumes
using local NLP processing (spaCy) and keyword matching from skills database.
No API keys required — everything runs offline.

Uses:
    - spaCy en_core_web_sm for NER (named entity recognition)
    - Regex date parsing for experience calculation
    - Skills database for skill matching (500+ technologies)
    - Rule-based templates for gap analysis

Functions:
    - extract_skills_and_experience(resume_text, job_description) → dict
    - parse_job_skills(job_description) → list[str]
    - _calculate_years_experience(text) → float or None
    - _extract_name(text, nlp) → str or None
    - _extract_email(text) → str or None
"""

import re
import logging
from datetime import datetime
from typing import Dict, List, Optional

# Import skills database utilities
from modules.skills_db import ALL_SKILLS, SKILL_ALIASES, normalize_skill, get_all_skill_variations

# Configure logging
logger = logging.getLogger(__name__)

# Terms that are likely skills/technologies, not person names
_NON_NAME_TERMS = {
    "asp.net", "asp.net core", "dotnet", ".net", "docker", "javascript", "typescript",
    "python", "java", "react", "angular", "vue", "node", "nodejs", "sql", "mysql",
    "postgresql", "mongodb", "redis", "aws", "azure", "gcp", "kubernetes", "jenkins",
    "terraform", "apache", "nginx", "django", "flask", "spring", "springboot", "golang",
    "backend", "frontend", "fullstack", "developer", "engineer", "resume", "curriculum vitae",
    "skills", "experience", "education", "summary", "profile", "objective"
}


def _is_plausible_person_name(name: Optional[str]) -> bool:
    """Validate that extracted name looks like a human name, not a skill/header."""
    if not name or not isinstance(name, str):
        return False

    cleaned = " ".join(name.strip().split())
    if not cleaned:
        return False

    lowered = cleaned.lower()

    # Hard reject obvious non-name markers
    if any(token in lowered for token in ["@", "http", "www", "linkedin", "github", "portfolio", "phone", "email"]):
        return False

    # Reject exact known non-name terms
    if lowered in _NON_NAME_TERMS:
        return False

    parts = cleaned.split()

    # Most resumes include first + last name; reject single-word extractions
    if len(parts) < 2 or len(parts) > 4:
        return False

    # Must contain alphabetic characters and only common name punctuation
    for part in parts:
        stripped = part.replace(".", "").replace("-", "").replace("'", "")
        if not stripped.isalpha():
            return False

    # Reject if too many parts look like technical keywords
    tech_like_parts = {"asp", "net", "core", "docker", "javascript", "python", "java", "sql", "aws", "azure", "apache", "react", "node"}
    if sum(1 for p in parts if p.lower().replace('.', '') in tech_like_parts) >= 1:
        return False

    return True


# ============================================================================
# HELPER: Calculate Years of Experience from Date Ranges (spaCy Mode)
# ============================================================================

def _calculate_years_experience(text: str) -> float:
    """
    Extract and sum work experience from resume text.
    
    Finds all date ranges in the resume and calculates total months of 
    experience. Uses the "max span" approach to handle overlapping dates:
    finds the earliest start date and latest end date across all entries
    to avoid double-counting jobs held simultaneously.
    
    Handles multiple date formats:
    - "Jan 2020 – Mar 2023" / "January 2020 - March 2023"
    - "2019 – 2022" / "2019-2022"
    - "2021 – Present" / "2020 - Current" / "2019 – now"
    - "03/2020 – 06/2023" (MM/YYYY format)
    - "March 2020 to June 2023"
    
    Edge cases:
    - Ignores date ranges in education sections (Bachelor, Master, PhD, etc)
    - Returns 0.0 if no work experience dates found
    - Caps result at 40 years maximum (sanity check for data errors)
    
    Args:
        text: Resume text to parse
        
    Returns:
        float: Years of experience rounded to 1 decimal (e.g., 5.5, or 0.0 if not found)
        
    Example:
        >>> text = "Software Engineer, Jan 2020 – Present\\nIntern, Jun 2019 – Dec 2019"
        >>> _calculate_years_experience(text)
        5.5  # (approx, depending on current date)
    """
    
    if not text or not isinstance(text, str):
        return 0.0
    
    # Convert to lowercase for case-insensitive matching
    text_lower = text.lower()
    
    # Define education keywords — date ranges near these are excluded
    education_keywords = {
        "bachelor", "master", "phd", "degree", "university", "college",
        "b.s.", "b.e.", "m.s.", "gpa", "graduation", "graduate",
        "diploma", "institute", "school", "coursework"
    }
    
    # List to store all found date ranges (as tuples of datetime objects)
    date_ranges = []
    
    # ========== REGEX PATTERNS FOR DATE EXTRACTION ==========
    
    # Pattern 1: Full month name + year (e.g., "January 2020")
    # Matches: "January 2020", "jan 2020", "Jan 2020" (case-insensitive)
    month_full = r"(?:january|february|march|april|may|june|july|august|september|october|november|december)"
    pattern_full_month = rf"({month_full})\s+(\d{{4}})"
    
    # Pattern 2: Short month name + year (e.g., "Jan 2020")
    month_short = r"(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)"
    pattern_short_month = rf"({month_short})\.?\s+(\d{{4}})"
    
    # Pattern 3: Month number + year (e.g., "03/2020", "3/2020")
    pattern_month_num = r"(\d{1,2})/(\d{4})"
    
    # Pattern 4: Year only (e.g., "2020")
    pattern_year_only = r"\b(\d{4})\b"
    
    # Date separators: various forms of dash/hyphen/to
    separator = r"\s*(?:–|-|to)\s*"
    
    # End date markers: "present", "current", "now", "today"
    present_markers = r"(?:present|current|now|today)"
    
    # ========== MAIN DATE RANGE FINDING LOGIC ==========
    
    # Build combined pattern to find date ranges
    # Looks for: [date1] [separator] [date2 or present marker]
    
    # Pattern: Full-month ranges (e.g., "January 2020 – March 2023")
    combined_full = rf"({month_full})\s+(\d{{4}}){separator}(?:({month_full})\s+(\d{{4}})|({present_markers}))"
    
    # Pattern: Short-month ranges (e.g., "Jan 2020 – Mar 2023")
    combined_short = rf"({month_short})\.?\s+(\d{{4}}){separator}(?:({month_short})\.?\s+(\d{{4}})|({present_markers}))"
    
    # Pattern: MM/YYYY ranges (e.g., "03/2020 – 06/2023")
    combined_month_num = rf"(\d{{1,2}})/(\d{{4}}){separator}(?:(\d{{1,2}})/(\d{{4}})|({present_markers}))"
    
    # Pattern: Year-only ranges (e.g., "2019 – 2022")
    combined_year_only = rf"\b(\d{{4}}){separator}(?:(\d{{4}})|({present_markers}))\b"
    
    # Month abbreviation map for parsing
    month_map = {
        "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
        "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12,
        "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
        "jul": 7, "aug": 8, "sep": 9, "sept": 9, "oct": 10, "nov": 11, "dec": 12
    }
    
    def is_education_context(match_text: str, full_text: str, match_start: int) -> bool:
        """Check if date range is in education section."""
        # Get surrounding context (500 chars before and after)
        context_start = max(0, match_start - 500)
        context_end = min(len(full_text), match_start + len(match_text) + 500)
        context = full_text[context_start:context_end].lower()
        
        # If context contains education keywords, likely education
        return any(keyword in context for keyword in education_keywords)
    
    def parse_month_year(month_str: str, year_str: str) -> Optional[tuple]:
        """Parse month and year strings to (month, year) tuple."""
        try:
            month = month_map.get(month_str.lower().rstrip('.'), None)
            year = int(year_str)
            if month and 1 <= month <= 12 and year >= 1900:
                return (month, year)
        except (ValueError, KeyError):
            pass
        return None
    
    def date_tuple_to_datetime(month: int, year: int) -> datetime:
        """Convert (month, year) tuple to datetime object (first day of month)."""
        return datetime(year, month, 1)
    
    # ========== SEARCH FOR ALL DATE RANGE PATTERNS ==========
    
    # Search for full-month ranges
    for match in re.finditer(combined_full, text, re.IGNORECASE):
        groups = match.groups()
        # groups: (start_month, start_year, end_month_or_none, end_year_or_none, present_marker_or_none)
        
        start_m = parse_month_year(groups[0], groups[1])
        if not start_m:
            continue
        
        # Check if in education context
        if is_education_context(match.group(0), text_lower, match.start()):
            continue
        
        # Parse end date
        if groups[4]:  # present/current/now marker
            end_date = datetime.now()
        elif groups[2] and groups[3]:  # end month + year provided
            end_m = parse_month_year(groups[2], groups[3])
            if not end_m:
                continue
            end_date = date_tuple_to_datetime(end_m[0], end_m[1])
        else:
            continue
        
        start_date = date_tuple_to_datetime(start_m[0], start_m[1])
        
        # Validate date range (end >= start)
        if end_date >= start_date:
            date_ranges.append((start_date, end_date))
    
    # Search for short-month ranges
    for match in re.finditer(combined_short, text, re.IGNORECASE):
        groups = match.groups()
        # groups: (start_month, start_year, end_month_or_none, end_year_or_none, present_marker_or_none)
        
        start_m = parse_month_year(groups[0], groups[1])
        if not start_m:
            continue
        
        if is_education_context(match.group(0), text_lower, match.start()):
            continue
        
        if groups[4]:  # present marker
            end_date = datetime.now()
        elif groups[2] and groups[3]:  # end month + year provided
            end_m = parse_month_year(groups[2], groups[3])
            if not end_m:
                continue
            end_date = date_tuple_to_datetime(end_m[0], end_m[1])
        else:
            continue
        
        start_date = date_tuple_to_datetime(start_m[0], start_m[1])
        
        if end_date >= start_date:
            date_ranges.append((start_date, end_date))
    
    # Search for MM/YYYY ranges
    for match in re.finditer(combined_month_num, text, re.IGNORECASE):
        groups = match.groups()
        # groups: (start_month, start_year, end_month_or_none, end_year_or_none, present_marker_or_none)
        
        try:
            start_month = int(groups[0])
            start_year = int(groups[1])
            if not (1 <= start_month <= 12 and start_year >= 1900):
                continue
        except (ValueError, TypeError):
            continue
        
        if is_education_context(match.group(0), text_lower, match.start()):
            continue
        
        if groups[4]:  # present marker
            end_date = datetime.now()
        elif groups[2] and groups[3]:  # end month + year provided
            try:
                end_month = int(groups[2])
                end_year = int(groups[3])
                if not (1 <= end_month <= 12 and end_year >= 1900):
                    continue
                end_date = datetime(end_year, end_month, 1)
            except (ValueError, TypeError):
                continue
        else:
            continue
        
        start_date = datetime(start_year, start_month, 1)
        
        if end_date >= start_date:
            date_ranges.append((start_date, end_date))
    
    # Search for year-only ranges
    for match in re.finditer(combined_year_only, text):
        groups = match.groups()
        # groups: (start_year, end_year_or_none, present_marker_or_none)
        
        try:
            start_year = int(groups[0])
            if start_year < 1900 or start_year > datetime.now().year:
                continue
        except (ValueError, TypeError):
            continue
        
        if is_education_context(match.group(0), text_lower, match.start()):
            continue
        
        if groups[2]:  # present marker
            end_date = datetime.now()
        elif groups[1]:  # end year provided
            try:
                end_year = int(groups[1])
                if end_year < 1900 or end_year > datetime.now().year:
                    continue
                end_date = datetime(end_year, 1, 1)
            except (ValueError, TypeError):
                continue
        else:
            continue
        
        start_date = datetime(start_year, 1, 1)
        
        if end_date >= start_date:
            date_ranges.append((start_date, end_date))
    
    # ========== NO DATES FOUND ==========
    if not date_ranges:
        return 0.0
    
    # ========== USE MAX SPAN APPROACH ==========
    # Find earliest start and latest end to avoid double-counting overlaps
    earliest_start = min(dr[0] for dr in date_ranges)
    latest_end = max(dr[1] for dr in date_ranges)
    
    # Calculate total months
    months_diff = (latest_end.year - earliest_start.year) * 12 + \
                  (latest_end.month - earliest_start.month)
    
    # Convert to years (float)
    years = months_diff / 12.0
    
    # Round to 1 decimal place
    years = round(years, 1)
    
    # Cap at 40 years max (sanity check)
    if years > 40:
        logger.warning(
            f"Experience calculation returned {years} years (> 40). "
            "Capping at 40 years. Check resume for data errors."
        )
        return 40.0
    
    return max(0.0, years)


# ============================================================================
# HELPER 2: Extract Candidate Name using spaCy NER + Regex Fallback
# ============================================================================

def _extract_name(text: str, nlp) -> Optional[str]:
    """
    Extract candidate name from resume text.
    
    Strategy (tries in order, returns first success):
    1. Use spaCy Named Entity Recognition (NER) to find first PERSON entity
       in the first 300 characters (names typically appear at the top)
    2. Regex fallback: look for 2-3 capitalized words at the very start of 
       the text (first non-empty line)
    3. Return None if nothing found
    
    Args:
        text: Resume text to parse
        nlp: Pre-loaded spaCy model (en_core_web_sm) to avoid reload overhead
        
    Returns:
        str: Candidate name (e.g., "John Smith")
        None: If no name found
        
    Example:
        >>> nlp = spacy.load("en_core_web_sm")
        >>> text = "John Smith\\njohn@example.com\\n\\nExperience..."
        >>> _extract_name(text, nlp)
        'John Smith'
    """
    
    if not text or not isinstance(text, str):
        return None
    
    # ========== STRATEGY 1: spaCy NER ==========
    # Process only the first 300 chars (names appear at top of resume)
    text_head = text[:300]
    
    try:
        doc = nlp(text_head)
        
        # Look for the first PERSON entity
        for ent in doc.ents:
            if ent.label_ == "PERSON":
                name = ent.text.strip()
                
                # Clean up the name: remove newlines, extra whitespace, and common non-name words
                name = ' '.join(name.split())  # Remove newlines and collapse whitespace
                
                # Filter out if name contains email/phone/etc keywords
                name_lower = name.lower()
                if any(keyword in name_lower for keyword in ['email', 'phone', 'linkedin', 'github', 'portfolio', 'website', '@']):
                    continue

                if _is_plausible_person_name(name):
                    return name
    except Exception as e:
        logger.debug(f"spaCy NER failed: {e}. Falling back to regex.")
    
    # ========== STRATEGY 2: Regex Fallback ==========
    # Look for 2-3 capitalized words at the very start (first non-empty line)
    lines = text.split('\n')
    
    for line in lines:
        line = line.strip()
        
        # Skip empty lines and common headers
        if not line or line.lower() in {'resume', 'cv', 'curriculum vitae', 'education', 'experience'}:
            continue
        
        # Extract capitalized words (potential name)
        # Pattern: Match 2-3 consecutive capitalized words at the start
        # Examples: "John Smith", "Mary Jane Watson", "Dr. John Smith"
        
        # Remove email/phone/urls from the line first
        line_clean = re.sub(r'[^\w\s\-\.]', '', line)
        words = line_clean.split()
        
        # Collect capitalized words
        cap_words = []
        for word in words:
            # Check if word starts with capital letter (and is not just numbers/symbols)
            if word and word[0].isupper() and any(c.isalpha() for c in word):
                cap_words.append(word)
            elif cap_words:
                # Stop collecting once we hit a non-capitalized word
                break
        
        # If we found 2-4 capitalized words, maybe a name
        if 2 <= len(cap_words) <= 4:
            name = ' '.join(cap_words)
            # Filter out common non-name words and technical terms
            if _is_plausible_person_name(name):
                return name
    
    return None


# ============================================================================
# HELPER 3: Extract Email Address using Regex
# ============================================================================

def _extract_email(text: str) -> Optional[str]:
    """
    Extract email address from resume text using regex.
    
    Uses standard email pattern matching to find first valid email address.
    Handles most common variations (dots, hyphens, underscores, numbers).
    
    Args:
        text: Resume text to parse
        
    Returns:
        str: First email found (e.g., "john.smith@example.com")
        None: If no email found
        
    Example:
        >>> text = "John Smith\\njohn.smith@example.com\\nPhone: 555-1234"
        >>> _extract_email(text)
        'john.smith@example.com'
    """
    
    if not text or not isinstance(text, str):
        return None
    
    # Email regex pattern: standard RFC-like email matching
    # Matches: user@domain.extension
    # Supports: dots, underscores, hyphens in local part; hyphens in domain
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b'
    
    # Find first email match
    match = re.search(email_pattern, text)
    
    if match:
        email = match.group(0).strip()
        return email
    
    return None


# ============================================================================
# SPACY MODEL CACHING — Load Once, Reuse for All Extractions
# ============================================================================

_NLP_MODEL = None
"""Module-level cache for spaCy model to avoid reloading on each call."""


def _get_nlp():
    """
    Get cached spaCy model or load it if not already loaded.
    
    Lazy loads en_core_web_sm model on first use to keep startup fast.
    Subsequent calls return cached model for speed.
    
    Returns:
        spacy.Language: Loaded spaCy language model
        
    Raises:
        OSError: If model not installed (run: python -m spacy download en_core_web_sm)
    """
    global _NLP_MODEL
    
    if _NLP_MODEL is None:
        try:
            import spacy
            _NLP_MODEL = spacy.load("en_core_web_sm")
            logger.info("✓ spaCy model loaded successfully")
        except OSError as e:
            logger.error(
                f"spaCy model 'en_core_web_sm' not found. "
                f"Install with: python -m spacy download en_core_web_sm\n{e}"
            )
            raise
    
    return _NLP_MODEL


# ============================================================================
# FUNCTION 1: Parse Job Skills from Text
# ============================================================================

def parse_job_skills(job_description: str) -> List[str]:
    """
    Extract and normalize tech skills from job description text.
    
    Uses keyword matching against the skills database with word-boundary
    regex to avoid partial matches (e.g., "r" won't match "react").
    
    Handles skill aliases: if both "react" and "react.js" are found,
    counts them as the same skill "react" (deduplicated).
    
    Args:
        job_description: Job posting text to extract skills from
        
    Returns:
        list[str]: Sorted list of unique normalized skill names
        Example: ["aws", "django", "docker", "kubernetes", "python", "react"]
        
    Example:
        >>> jd = "Senior Engineer with React, Python, and AWS expertise"
        >>> parse_job_skills(jd)
        ['aws', 'python', 'react']
    """
    
    if not job_description or not isinstance(job_description, str):
        return []
    
    # Convert to lowercase for case-insensitive matching
    text_lower = job_description.lower()
    
    # Set to collect matched skills (avoids duplicates)
    matched_skills = set()
    
    # ========== STRATEGY 1: Check ALL_SKILLS with word boundaries ==========
    # Build regex pattern for each skill with word boundaries
    # Word boundary \b ensures "r" doesn't match "react", "go" doesn't match "good"
    
    for skill in ALL_SKILLS:
        # Escape special regex characters in skill name
        # e.g., "c++" becomes "c\+\+" to match literally
        escaped_skill = re.escape(skill.lower())
        
        # Pattern with word boundaries: \b matches at word start/end
        pattern = r'\b' + escaped_skill + r'\b'
        
        # Check if skill appears in text
        if re.search(pattern, text_lower):
            # Normalize the skill (apply aliases)
            normalized = normalize_skill(skill)
            matched_skills.add(normalized)
    
    # ========== STRATEGY 2: Also check SKILL_ALIASES variations ==========
    # Some aliases might appear that aren't in ALL_SKILLS directly
    # e.g., "react.js" might appear but we store it under "react"
    
    for alias, canonical in SKILL_ALIASES.items():
        escaped_alias = re.escape(alias.lower())
        pattern = r'\b' + escaped_alias + r'\b'
        
        if re.search(pattern, text_lower):
            # Normalize to canonical form
            normalized = normalize_skill(canonical)
            matched_skills.add(normalized)
    
    # Return sorted list of unique skills
    return sorted(list(matched_skills))


# ============================================================================
# FUNCTION 2: Main Extraction — Skills + Experience + Metadata
# ============================================================================

def extract_skills_and_experience(resume_text: str, job_description: str) -> Dict:
    """
    Extract comprehensive candidate information from resume.
    
    Combines multiple techniques:
    - spaCy NER for name extraction
    - Regex for email detection
    - Keyword matching for skills (against 500+ tech skills)
    - Regex date parsing for experience years
    - Simple regex for education level
    
    Returns identical output structure to previous Gemini version so
    downstream pipeline (scoring, ranking) needs no changes.
    
    Args:
        resume_text: Complete resume text (plain text)
        job_description: Job posting text for skill matching
        
    Returns:
        dict with keys:
            - candidate_name: str or None (e.g., "John Smith")
            - email: str or None (e.g., "john@example.com")
            - skills_found: [str] (e.g., ["python", "react", "docker"])
            - years_of_experience: float (e.g., 5.5, or 0.0 if not found)
            - education: str or None (e.g., "Bachelor of Science")
            - relevant_skills: [str] (skills in both resume AND job)
            - missing_skills: [str] (skills in job but NOT resume)
            - experience_details: str or None (template text)
            - extraction_success: bool (True if name OR skills found)
            
    Example:
        >>> result = extract_skills_and_experience(resume, jd)
        >>> result['candidate_name']
        'John Smith'
        >>> result['years_of_experience']
        5.5
        >>> len(result['skills_found'])
        12
    """
    
    # Initialize fallback response (returned if extraction completely fails)
    fallback_response = {
        "candidate_name": None,
        "email": None,
        "skills_found": [],
        "years_of_experience": 0.0,
        "education": None,
        "relevant_skills": [],
        "missing_skills": [],
        "experience_details": None,
        "extraction_success": False
    }
    
    # Validate input
    if not resume_text or not isinstance(resume_text, str):
        return fallback_response
    
    try:
        # ========== STEP 1: Load spaCy model ==========
        nlp = _get_nlp()
        
        # ========== STEP 2: Extract candidate name ==========
        candidate_name = _extract_name(resume_text, nlp)
        
        # ========== STEP 3: Extract email ==========
        email = _extract_email(resume_text)
        
        # ========== STEP 4 & 5: Extract skills from BOTH resume and job ==========
        skills_found = parse_job_skills(resume_text)
        job_skills = parse_job_skills(job_description)
        
        # ========== STEP 6: Calculate relevant skills ==========
        # Skills that appear in BOTH resume AND job description
        # Normalize both sides before comparing
        relevant_skills = []
        for resume_skill in skills_found:
            for job_skill in job_skills:
                if normalize_skill(resume_skill) == normalize_skill(job_skill):
                    relevant_skills.append(resume_skill)
                    break
        
        relevant_skills = sorted(list(set(relevant_skills)))  # Remove duplicates
        
        # ========== STEP 7: Calculate missing skills ==========
        # Skills in job description that are NOT in resume
        missing_skills = []
        for job_skill in job_skills:
            job_normalized = normalize_skill(job_skill)
            found = False
            for resume_skill in skills_found:
                if normalize_skill(resume_skill) == job_normalized:
                    found = True
                    break
            if not found:
                missing_skills.append(job_skill)
        
        missing_skills = sorted(list(set(missing_skills)))  # Remove duplicates
        
        # ========== STEP 8: Extract years of experience ==========
        years_of_experience = _calculate_years_experience(resume_text)
        
        # ========== STEP 9: Extract education level ==========
        # Regex patterns for degree names
        # Matches: "B.S.", "Bachelor of Science", "Master's", "PhD", etc.
        education = None
        education_patterns = [
            r"(?:B\.?S\.?|Bachelor)[^,\n]*",  # Bachelor's degree
            r"(?:M\.?S\.?|Master)[^,\n]*",    # Master's degree
            r"(?:Ph\.?D\.?|PhD)[^,\n]*",       # PhD
            r"(?:M\.?B\.?A\.?|MBA)[^,\n]*",   # MBA
            r"(?:B\.?E\.?|B\.?Tech\.?)[^,\n]*", # Bachelor of Engineering
            r"(?:B\.?C\.?S\.?|BSCS)[^,\n]*",   # Bachelor of CS
        ]
        
        resume_lower = resume_text.lower()
        for pattern in education_patterns:
            match = re.search(pattern, resume_text, re.IGNORECASE)
            if match:
                education = match.group(0).strip()
                break
        
        # ========== STEP 10: Build experience details ==========
        experience_details = None
        if years_of_experience is not None and skills_found:
            # Simple template (not AI-generated)
            skill_snippet = ", ".join(skills_found[:5])
            if len(skills_found) > 5:
                skill_snippet += f" and {len(skills_found) - 5} more"
            
            experience_details = f"{years_of_experience} year{'s' if years_of_experience != 1 else ''} of experience. Skills include: {skill_snippet}."
        
        # ========== STEP 11: Determine extraction success ==========
        # Success if we found name OR found skills
        extraction_success = (candidate_name is not None) or (len(skills_found) > 0)
        
        # ========== BUILD RESPONSE ==========
        return {
            "candidate_name": candidate_name,
            "email": email,
            "skills_found": sorted(skills_found),
            "years_of_experience": years_of_experience,
            "education": education,
            "relevant_skills": relevant_skills,
            "missing_skills": missing_skills,
            "experience_details": experience_details,
            "extraction_success": extraction_success
        }
    
    except Exception as e:
        # Log the error but don't crash — return fallback response
        logger.error(f"Extraction failed: {e}", exc_info=True)
        fallback_response["extraction_success"] = False
        return fallback_response


# Export public functions
__all__ = [
    "extract_skills_and_experience",
    "parse_job_skills",
]
