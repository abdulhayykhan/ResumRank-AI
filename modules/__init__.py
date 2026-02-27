"""
Resume Ranking System - Modules Package
========================================

This package contains all core modules for the resume ranking analysis pipeline:
- pdf_parser: Extract text from PDF resumes
- skill_extractor: Use local spaCy NLP to extract skills and experience
- scorer: Calculate weighted skill and experience scores
- ranker: Sort candidates with deterministic tie-breaking
- exporter: Export results to CSV format
- skills_db: Tech skills knowledge base for local NLP extraction
"""

from . import pdf_parser
from . import skill_extractor
from . import scorer
from . import ranker
from . import exporter
from . import skills_db

__all__ = [
    'pdf_parser',
    'skill_extractor',
    'scorer',
    'ranker',
    'exporter',
    'skills_db'
]


def verify_nlp_setup() -> bool:
    """
    Verify spaCy model is installed and loadable.
    Called once on app startup.
    Returns True if ready, False if model needs downloading.
    """
    try:
        import spacy
        spacy.load("en_core_web_sm")
        return True
    except OSError:
        import logging
        logging.getLogger(__name__).error(
            "spaCy model 'en_core_web_sm' not found. "
            "Run: python -m spacy download en_core_web_sm"
        )
        return False
