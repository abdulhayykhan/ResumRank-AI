"""
PDF Parser Module
=================

Extracts text from PDF resume files using pdfplumber.
Handles multi-page PDFs, tables, special characters, and edge cases.
"""

import os
import logging
from pathlib import Path
from typing import Dict, Tuple

try:
    import pdfplumber
except ImportError:
    raise ImportError("pdfplumber not installed. Run: pip install pdfplumber")


logger = logging.getLogger(__name__)


def extract_text(file_path: str) -> Dict[str, any]:
    """
    Extract text from a PDF file.
    
    Args:
        file_path (str): Path to the PDF file
        
    Returns:
        dict: {
            "raw_text": extracted text as-is,
            "cleaned_text": cleaned and normalized text,
            "page_count": number of pages in PDF,
            "extraction_success": boolean indicating success
        }
        
    Raises:
        FileNotFoundError: If file doesn't exist
        Exception: On PDF parsing errors
    """
    result = {
        "raw_text": "",
        "cleaned_text": "",
        "page_count": 0,
        "extraction_success": False
    }
    
    try:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"PDF file not found: {file_path}")
        
        # Extract text from all pages
        raw_texts = []
        with pdfplumber.open(file_path) as pdf:
            result["page_count"] = len(pdf.pages)
            
            for page in pdf.pages:
                # Extract regular text
                page_text = page.extract_text()
                if page_text:
                    raw_texts.append(page_text)
                
                # Extract tables if present
                tables = page.extract_tables()
                if tables:
                    for table in tables:
                        for row in table:
                            row_text = " | ".join(str(cell) if cell else "" for cell in row)
                            raw_texts.append(row_text)
        
        raw_text = "\n".join(raw_texts)
        cleaned = clean_text(raw_text)
        
        # EDGE CASE 1: Check if extraction was successful (detect scanned/image PDFs)
        # Threshold: < 100 characters indicates likely scanned image
        if len(cleaned.strip()) < 100:
            logger.warning(
                f"⚠️  Scanned PDF detected: {file_path} has < 100 characters of text. "
                f"This is likely a scanned image PDF with no extractable text."
            )
            result["extraction_success"] = False
            result["is_scanned"] = True
            result["raw_text"] = raw_text
            result["cleaned_text"] = cleaned
            return result
        
        result["raw_text"] = raw_text
        result["cleaned_text"] = cleaned
        result["extraction_success"] = True
        result["is_scanned"] = False
        
    except Exception as e:
        logger.error(f"Error extracting text from {file_path}: {str(e)}")
        result["extraction_success"] = False
    
    return result


def clean_text(raw_text: str) -> str:
    """
    Clean and normalize extracted PDF text.
    
    Args:
        raw_text (str): Raw text extracted from PDF
        
    Returns:
        str: Cleaned text
    """
    import re
    
    # Normalize line endings
    text = raw_text.replace('\r\n', '\n')
    
    # Remove excessive whitespace
    text = re.sub(r'\n\s*\n', '\n', text)
    text = re.sub(r'[ \t]+', ' ', text)
    
    # Normalize bullet points
    text = re.sub(r'[•◦▪▸→]', '-', text)
    
    # Remove page numbers and common headers/footers
    text = re.sub(r'^Page \d+\s*$', '', text, flags=re.MULTILINE)
    text = re.sub(r'^(Page \d+ of \d+)\s*$', '', text, flags=re.MULTILINE)
    
    # Strip leading/trailing whitespace for each line
    lines = [line.strip() for line in text.split('\n')]
    text = '\n'.join(lines)
    
    # Remove consecutive blank lines
    text = re.sub(r'\n\n+', '\n\n', text)
    
    return text.strip()
