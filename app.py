"""
Resume Ranking System - Main Flask Application
===============================================

Flask application that ties together all modules for resume analysis and ranking.

Routes:
  GET  /                    - Upload page
  POST /upload              - Handle file upload
  POST /analyze             - Run analysis pipeline
  GET  /results/<session_id>- Display results
  GET  /export/<session_id> - Download CSV
  GET  /progress/<session_id> - Get progress JSON
  POST /quick-feedback      - Quick skill feedback

Features:
  - Rate limiting: 5 analyses per minute per IP
  - Automatic file cleanup after processing
  - Session cleanup after 1 hour
  - Comprehensive error handling with user-friendly messages
  - Progress tracking for long-running analyses
"""

import os
import logging
import time
import hashlib
from collections import defaultdict
from flask import Flask, render_template, request, jsonify, send_file, redirect
from werkzeug.utils import secure_filename
import uuid
from datetime import datetime, timedelta
from io import BytesIO
from concurrent.futures import ThreadPoolExecutor, as_completed

import config
from modules import pdf_parser, skill_extractor, scorer, ranker, exporter
from modules.session_manager import get_session_manager


# Configure logging
log_level = logging.WARNING if config.is_production() else logging.INFO
logging.basicConfig(
    level=log_level,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.secret_key = config.SECRET_KEY
app.config['MAX_CONTENT_LENGTH'] = config.MAX_UPLOAD_SIZE_MB * 1024 * 1024
app.config['UPLOAD_FOLDER'] = config.UPLOAD_FOLDER

# Create required directories
os.makedirs(config.UPLOAD_FOLDER, exist_ok=True)
os.makedirs(config.RESULTS_FOLDER, exist_ok=True)

# File-based session storage (persists across restarts)
session_manager = get_session_manager()

# Rate limiting: track analyses per IP (max 5 per minute)
# Format: {ip_address: [timestamp1, timestamp2, ...]}
rate_limit_store = defaultdict(list)


# ========== Startup Verification ==========
from modules import verify_nlp_setup

if not verify_nlp_setup():
    logger.error(
        "STARTUP FAILED: spaCy model not found.\n"
        "Fix: Run 'python -m spacy download en_core_web_sm'\n"
        "Railway: The Procfile handles this automatically."
    )
    # Don't exit — let Railway's Procfile handle the download
    # The first request will trigger spaCy to load and may be slow


# ========== Helper Functions ==========

def check_rate_limit(ip_address: str, max_requests: int = 5, window_seconds: int = 60) -> bool:
    """
    Check if an IP address has exceeded the rate limit.
    
    Args:
        ip_address: Client IP address
        max_requests: Maximum requests allowed in time window (default: 5)
        window_seconds: Time window in seconds (default: 60)
    
    Returns:
        bool: True if request allowed, False if rate limit exceeded
    """
    now = time.time()
    cutoff = now - window_seconds
    
    # Remove old timestamps outside the window
    rate_limit_store[ip_address] = [
        ts for ts in rate_limit_store[ip_address] if ts > cutoff
    ]
    
    # Check if limit exceeded
    if len(rate_limit_store[ip_address]) >= max_requests:
        logger.warning(f"Rate limit exceeded for IP {ip_address}")
        return False
    
    # Add current timestamp
    rate_limit_store[ip_address].append(now)
    return True





def cleanup_uploaded_files(session_id: str):
    """
    Delete uploaded files for a session to save disk space.
    
    Args:
        session_id: Session ID to cleanup
    """
    session_data = session_manager.get_results(session_id)
    if not session_data:
        return
    files = session_data.get('files', [])
    
    for filepath in files:
        try:
            if os.path.exists(filepath):
                os.remove(filepath)
                logger.info(f"Deleted file: {filepath}")
        except Exception as e:
            logger.error(f"Failed to delete file {filepath}: {str(e)}")


def cleanup_old_sessions(hours: int = 1):
    """
    Remove old session data to save memory and disk space.
    
    Deletes:
      - Session data from session files
      - Uploaded PDF files
    
    Args:
        hours: Remove sessions older than this many hours (default: 1)
    """
    deleted_count = session_manager.cleanup_old_sessions(hours)
    if deleted_count > 0:
        logger.info(f"Cleaned up {deleted_count} old sessions")


def generate_csv_filename() -> str:
    """
    Generate a timestamped filename for CSV export.
    
    Returns:
        str: Filename like "resumrank_results_2026-02-27_143045.csv"
    """
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    return f"resumrank_results_{timestamp}.csv"


# ========== Routes ==========

@app.route('/')
def index():
    """Render the upload page."""
    return render_template('index.html')


@app.before_request
def enforce_https():
    if config.is_production() and request.headers.get('X-Forwarded-Proto') == 'http':
        return redirect(request.url.replace('http://', 'https://'), code=301)


@app.after_request
def add_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    return response


@app.route('/health')
def health():
    from modules import verify_nlp_setup
    nlp_ready = verify_nlp_setup()
    return jsonify({
        "status": "ok" if nlp_ready else "degraded",
        "app": config.APP_NAME,
        "env": config.APP_ENV,
        "nlp_mode": "spacy_local",
        "nlp_model": config.SPACY_MODEL,
        "nlp_ready": nlp_ready,
        "api_key_required": False
    }), 200 if nlp_ready else 503


@app.route('/upload', methods=['POST'])
def upload():
    """
    Handle file upload.
    
    Expected:
      - files: Multiple PDF files (field name: 'resumes')
      - job_description: Job description text
    
    Returns:
      JSON with session_id, file count, and status
    """
    try:
        # Validate files are provided
        if 'resumes' not in request.files:
            return jsonify({'error': 'No files provided'}), 400
        
        files = request.files.getlist('resumes')
        job_description = request.form.get('job_description', '').strip()
        
        if not files or len(files) == 0:
            return jsonify({'error': 'No files selected'}), 400
        
        # Validate job description word count (minimum 20 words)
        if not job_description:
            return jsonify({'error': 'Job description is required'}), 400
        
        word_count = len(job_description.split())
        if word_count < 20:
            return jsonify({
                'error': f'Job description too short ({word_count} words). Please provide at least 20 words for accurate analysis.'
            }), 400
        
        # Check for duplicate PDFs using MD5 hash
        file_hashes = {}
        duplicates = []
        
        for file in files:
            # Read content for hashing
            file.seek(0)
            content = file.read()
            file.seek(0)  # Reset for later saving
            
            file_hash = hashlib.md5(content).hexdigest()
            
            if file_hash in file_hashes:
                duplicates.append(file.filename)
                logger.warning(f"⚠️ Duplicate detected: {file.filename} matches {file_hashes[file_hash]}")
            else:
                file_hashes[file_hash] = file.filename
        
        if duplicates:
            return jsonify({
                'error': f'Duplicate files detected: {", ".join(duplicates)}. Please remove duplicates and try again.'
            }), 400
        
        # Validate and save files
        session_id = str(uuid.uuid4())
        saved_files = []
        
        for file in files:
            # Validate file type
            if not file.filename or not config.is_allowed_file(file.filename):
                return jsonify({'error': f'Invalid file type: {file.filename}'}), 400
            
            # Validate file size
            file.seek(0, os.SEEK_END)
            file_size = file.tell()
            file.seek(0)
            
            if file_size > config.MAX_UPLOAD_SIZE_MB * 1024 * 1024:
                return jsonify({
                    'error': f'File too large: {file.filename} ({file_size / (1024*1024):.1f}MB)'
                }), 400
            
            # Save file with unique name
            filename = secure_filename(file.filename)
            unique_filename = f"{session_id}_{filename}"
            filepath = os.path.join(config.UPLOAD_FOLDER, unique_filename)
            file.save(filepath)
            saved_files.append(filepath)
            logger.info(f"Saved file: {unique_filename}")
        
        # Store session data
        session_manager.set_results(session_id, {
            'job_description': job_description,
            'files': saved_files,
            'status': 'uploaded',
            'created_at': datetime.now()
        })

        logger.info(f"Session {session_id}: {len(saved_files)} files uploaded")
        
        session_manager.set_progress(session_id, 'Files uploaded', 0)
        
        return jsonify({
            'session_id': session_id,
            'files_uploaded': len(saved_files),
            'status': 'success'
        }), 200
    
    except Exception as e:
        logger.error(f"Upload error: {str(e)}")
        return jsonify({'error': 'Upload failed. Please try again.'}), 500


@app.route('/analyze', methods=['POST'])
def analyze():
    """
    Run the full analysis pipeline.
    
    Expected JSON:
      - session_id: Session ID from /upload
      - job_description: Job description (optional, uses uploaded one if not provided)
    
    Returns:
      JSON with ranked results
      
    Rate Limited: Max 5 analyses per minute per IP
    """
    try:
        # Rate limiting check
        client_ip = request.remote_addr
        if not check_rate_limit(client_ip):
            return jsonify({
                'error': 'Rate limit exceeded. Maximum 5 analyses per minute. Please wait and try again.'
            }), 429
        
        data = request.get_json()
        session_id = data.get('session_id')
        
        session_data = session_manager.get_results(session_id)
        if not session_id or not session_data:
            return jsonify({'error': 'Invalid session ID'}), 400
        job_description = session_data.get('job_description', '')
        file_paths = session_data.get('files', [])
        
        if not file_paths:
            return jsonify({'error': 'No files in session'}), 400
        
        # Run pipeline
        logger.info(f"Starting analysis for session {session_id} (IP: {client_ip})")
        session_manager.set_progress(session_id, 'Starting analysis', 5)
        
        pipeline_result = run_full_pipeline(file_paths, job_description, session_id)
        
        # Store results
        session_data['results'] = pipeline_result
        session_data['status'] = 'completed'
        session_data['completed_at'] = datetime.now()
        session_manager.set_results(session_id, session_data)
        
        session_manager.set_progress(session_id, 'Analysis complete', 100)


        
        # Cleanup uploaded files after successful processing
        cleanup_uploaded_files(session_id)
        
        # Cleanup old sessions (runs periodically on each analysis)
        cleanup_old_sessions(hours=1)
        
        return jsonify({
            'session_id': session_id,
            'status': 'success',
            'results': pipeline_result
        }), 200
        
    except Exception as e:
        logger.error(f"Analysis error: {str(e)}", exc_info=True)
        
        # Update progress to show error
        if 'session_id' in locals() and session_id:
            session_manager.set_progress(session_id, 'Error occurred', 0, error=str(e))
        
        return jsonify({
            'error': 'Analysis failed. Please try again or contact support.',
            'details': str(e) if app.debug else None
        }), 500


@app.route('/results/<session_id>')
def results(session_id):
    """
    Display ranking results.
    
    Args:
      session_id: Session ID from upload
    
    Returns:
      HTML page with results table or error page
    """
    try:
        session_data = session_manager.get_results(session_id)
        if not session_data:
            return render_template(
                'error.html',
                error='Session not found. The session may have expired or the ID is invalid.'
            ), 404
        
        if 'results' not in session_data:
            return render_template(
                'error.html',
                error='Results not ready. Please wait for analysis to complete.'
            ), 400
        
        results_data = session_data['results']
        
        return render_template(
            'results.html',
            ranked_candidates=results_data.get('ranked_candidates', []),
            summary=results_data.get('summary', {}),
            session_id=session_id
        ), 200
        
    except Exception as e:
        logger.error(f"Results display error for session {session_id}: {str(e)}", exc_info=True)
        return render_template(
            'error.html',
            error='Failed to load results. Please try again.'
        ), 500


@app.route('/export/<session_id>')
def export(session_id):
    """
    Download results as CSV.
    
    Args:
      session_id: Session ID from upload
    
    Returns:
      CSV file download or error JSON
    """
    try:
        session_data = session_manager.get_results(session_id)
        if not session_data:
            return jsonify({'error': 'Session not found'}), 404
        
        if 'results' not in session_data:
            return jsonify({'error': 'Results not ready'}), 400
        
        candidates = session_data['results'].get('ranked_candidates', [])
        
        if not candidates:
            return jsonify({'error': 'No candidates to export'}), 400
        
        # Generate CSV content
        csv_content = exporter.get_csv_as_string(candidates)
        
        # Create download response
        csv_bytes = BytesIO(csv_content.encode('utf-8'))
        filename = generate_csv_filename()
        
        return send_file(
            csv_bytes,
            mimetype='text/csv',
            as_attachment=True,
            download_name=filename
        ), 200
        
    except Exception as e:
        logger.error(f"Export error for session {session_id}: {str(e)}", exc_info=True)
        return jsonify({
            'error': 'Failed to export results. Please try again.'
        }), 500


@app.route('/progress/<session_id>')
def progress(session_id):
    """Get analysis progress."""
    progress_data = session_manager.get_progress(session_id)
    return jsonify(progress_data), 200


@app.route('/quick-feedback', methods=['POST'])
def quick_feedback():
    """
    Generate quick skill feedback for a resume.
    
    Expected JSON:
      - resume_text: Resume text (or paste)
      - job_description: Job description
    
    Returns:
      Quick score estimate and missing skills
    """
    try:
        data = request.get_json()
        resume_text = data.get('resume_text', '').strip()
        job_description = data.get('job_description', '').strip()
        
        if not resume_text or not job_description:
            return jsonify({'error': 'Resume and job description required'}), 400

        # Quick extraction
        candidate_data = skill_extractor.extract_skills_and_experience(
            resume_text,
            job_description
        )
        
        # Quick scoring
        job_skills = skill_extractor.parse_job_skills(job_description)
        score_breakdown = scorer.generate_score_breakdown(candidate_data, job_skills)
        
        return jsonify({
            'score': score_breakdown.get('final_score'),
            'skill_match': score_breakdown.get('skill_match_percent'),
            'missing_skills': candidate_data.get('missing_skills', [])[:3]  # Top 3
        }), 200
    
    except Exception as e:
        logger.error(f"Quick feedback error: {str(e)}")
        return jsonify({'error': 'Quick feedback failed. Please try again.'}), 500


@app.errorhandler(400)
def bad_request(e):
    """Handle 400 Bad Request errors."""
    return render_template(
        'error.html',
        error='Bad request. Please check your input and try again.'
    ), 400


@app.errorhandler(404)
def not_found(e):
    """Handle 404 Not Found errors."""
    return render_template(
        'error.html',
        error='Page not found. The requested resource does not exist.'
    ), 404


@app.errorhandler(429)
def rate_limit_exceeded(e):
    """Handle 429 Too Many Requests errors."""
    return render_template(
        'error.html',
        error='Too many requests. Please wait a moment and try again. (Max 5 analyses per minute)'
    ), 429


@app.errorhandler(500)
def server_error(e):
    """Handle 500 Internal Server Error."""
    logger.error(f"Internal server error: {str(e)}", exc_info=True)
    return render_template(
        'error.html',
        error='An error occurred. Please try again.'
    ), 500


@app.errorhandler(413)
def request_entity_too_large(e):
    """Handle 413 Payload Too Large errors."""
    return render_template(
        'error.html',
        error=f'File too large. Maximum upload size is {config.MAX_UPLOAD_SIZE_MB}MB per file.'
    ), 413


def _clean_filename_to_name(filename: str) -> str:
    """
    Extract a clean candidate name from a saved upload filename.
    
    Uploaded files are saved as: {session_id}_{original_filename}.pdf
    e.g. "2430e19d-43f9-43bc-8a8_Sarah_Ahmed_Resume.pdf"
    
    Strategy:
    1. Remove .pdf extension
    2. Remove the session UUID prefix (format: 8-4-4-4-12 hex chars followed by _)
    3. Remove common resume words: "Resume", "CV", "Email", "Biodata"
    4. Replace underscores and hyphens with spaces
    5. Title-case the result
    6. Strip extra whitespace
    
    Examples:
        "2430e19d-43f9-43bc-b8a8-00d59ab4fc4d_Sarah_Ahmed_Email.pdf"
        → "Sarah Ahmed"
        
        "abc123_John_Smith_Resume.pdf"
        → "John Smith"
        
        "Ali_Hassan_CV.pdf"  (no UUID)
        → "Ali Hassan"
    
    Args:
        filename: Saved upload filename (with or without UUID prefix)
    
    Returns:
        str: Clean candidate name
    """
    import re
    
    # Remove extension
    name = filename.replace('.pdf', '').replace('.PDF', '')
    
    # Remove UUID prefix (format: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx_)
    # UUID pattern: 8hex-4hex-4hex-4hex-12hex
    uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}_'
    name = re.sub(uuid_pattern, '', name, flags=re.IGNORECASE)
    
    # Remove common resume suffix words (case-insensitive)
    # These words appear in filenames but aren't part of the name
    noise_words = [
        '_Resume', '_CV', '_Email', '_Biodata', '_Application',
        '_Updated', '_Final', '_New', '_2024', '_2025', '_2026',
        '-Resume', '-CV', '-Email',
        ' Resume', ' CV', ' Email',
    ]
    for word in noise_words:
        name = name.replace(word, '').replace(word.lower(), '').replace(word.upper(), '')
    
    # Replace underscores and hyphens with spaces
    name = name.replace('_', ' ').replace('-', ' ')
    
    # Title-case and strip
    name = ' '.join(word.capitalize() for word in name.split())
    
    return name.strip() or "Unknown Candidate"


def _is_valid_extracted_name(name: str) -> bool:
    """Validate extracted candidate names and reject skill/header-like values."""
    import re

    if not name or not isinstance(name, str):
        return False

    normalized = ' '.join(name.strip().split())
    lowered = normalized.lower()

    if not normalized:
        return False

    invalid_terms = {
        'asp.net core', 'asp.net', 'docker', 'javascript', 'python', 'java', 'react', 'sql',
        'aws', 'azure', 'apache', 'skills', 'experience', 'education', 'resume', 'cv',
        'full stack', 'backend', 'frontend', 'developer', 'engineer'
    }

    if lowered in invalid_terms:
        return False

    parts = normalized.split()
    if len(parts) < 2 or len(parts) > 4:
        return False

    for part in parts:
        cleaned = part.replace('.', '').replace('-', '').replace("'", '')
        if not re.match(r'^[A-Za-z]+$', cleaned):
            return False

    return True


def run_full_pipeline(file_paths, job_description, session_id):
    """
    Orchestrate the complete analysis pipeline using local NLP (spaCy).
    
    Pipeline steps:
      1. Parse PDFs in parallel (ThreadPoolExecutor)
      2. Extract skills locally using spaCy NLP + keyword matching
      3. Score each candidate
      4. Generate gap analyses using rule-based templates
      5. Rank candidates deterministically
      6. Generate summary statistics
    
    Args:
      file_paths: List of PDF file paths
      job_description: Job description text
      session_id: Session ID for progress tracking
    
    Returns:
      dict with ranked_candidates, summary, job_skills, total_processed, processing_time
      
    Raises:
      Exception: If critical pipeline step fails
    """
    import time
    
    start_time = time.time()
    candidates = []
    failed_files = []
    
    try:
        # Step 1: Parse PDFs in parallel (PDF parsing doesn't hit API, safe to parallelize)
        logger.info(f"[Pipeline] Step 1: Parsing {len(file_paths)} PDFs")
        session_manager.set_progress(session_id, 'Parsing PDFs', 10)
        
        with ThreadPoolExecutor(max_workers=4) as executor:
            parse_tasks = {executor.submit(pdf_parser.extract_text, fp): fp for fp in file_paths}
            
            for future in as_completed(parse_tasks):
                fp = parse_tasks[future]
                try:
                    result = future.result()
                    
                    if result.get('extraction_success') and len(result.get('cleaned_text', '')) > 50:
                        candidates.append({
                            'file_path': fp,
                            'raw_text': result.get('cleaned_text', ''),
                            'page_count': result.get('page_count', 0),
                            'candidate_name': _clean_filename_to_name(os.path.basename(fp)),
                            'is_scanned': result.get('is_scanned', False)
                        })
                        logger.info(f"Successfully parsed: {os.path.basename(fp)}")
                    else:
                        failed_files.append(fp)
                        logger.warning(f"Failed to extract text from: {os.path.basename(fp)}")
                        
                except Exception as e:
                    failed_files.append(fp)
                    logger.error(f"Error parsing {os.path.basename(fp)}: {str(e)}")
        
        if not candidates:
            raise Exception(
                "No resumes could be parsed successfully. Please ensure PDFs contain text (not scanned images)."
            )
        
        logger.info(f"[Pipeline] Parsed {len(candidates)} resumes successfully, {len(failed_files)} failed")
        
        # Step 2: Extract skills using local spaCy NLP (no API calls, instant processing)
        logger.info(f"[Pipeline] Step 2: Extracting skills with local NLP")
        session_manager.set_progress(
            session_id,
            f'Extracting skills (0/{len(candidates)})',
            30
        )
        
        # Parse job skills once using spaCy keyword matching
        job_skills = skill_extractor.parse_job_skills(job_description)
        logger.info(f"Job requires {len(job_skills)} skills: {', '.join(job_skills[:5])}...")
        
        for i, candidate in enumerate(candidates):
            try:
                fallback_name = candidate.get('candidate_name')
                candidate_data = skill_extractor.extract_skills_and_experience(
                    candidate['raw_text'],
                    job_description
                )

                extracted_name = candidate_data.get('candidate_name')
                if not _is_valid_extracted_name(extracted_name):
                    candidate_data['candidate_name'] = fallback_name

                candidate.update(candidate_data)
                
                logger.info(
                    f"Extracted skills for candidate {i+1}/{len(candidates)}: "
                    f"{candidate_data.get('candidate_name', 'Unknown')}"
                )
                
                # Update progress
                progress_percent = 30 + int((i + 1) / len(candidates) * 25)
                session_manager.set_progress(
                    session_id,
                    f'Extracting skills ({i+1}/{len(candidates)})',
                    progress_percent
                )
                    
            except Exception as e:
                logger.error(f"Skill extraction failed for candidate {i+1}: {str(e)}")
                # Use fallback data
                candidate.update({
                    'candidate_name': candidate.get('candidate_name', 'Unknown'),
                    'email': None,
                    'skills_found': [],
                    'years_of_experience': 0,
                    'relevant_skills': [],
                    'missing_skills': job_skills,
                    'extraction_failed': True
                })
        
        # Step 3: Score candidates
        logger.info(f"[Pipeline] Step 3: Scoring {len(candidates)} candidates")
        session_manager.set_progress(session_id, 'Scoring candidates', 60)
        
        for candidate in candidates:
            try:
                score_breakdown = scorer.generate_score_breakdown(candidate, job_skills)
                candidate.update(score_breakdown)
            except Exception as e:
                logger.error(f"Scoring failed for {candidate.get('candidate_name')}: {str(e)}")
                # Assign zero scores
                candidate.update({
                    'skill_score': 0,
                    'experience_score': 0,
                    'final_score': 0,
                    'matched_skills': [],
                    'missing_skills': job_skills
                })
        
        # Step 4: Generate gap analyses using rule-based templates (instant, no API calls)
        logger.info(f"[Pipeline] Step 4: Generating gap analyses")
        session_manager.set_progress(session_id, 'Generating gap analyses', 75)
        
        try:
            # Template-based gap analysis — no API calls, instant processing
            analyses = scorer.generate_all_gap_analyses(
                candidates,
                job_description
            )
            for candidate, analysis in zip(candidates, analyses):
                candidate['gap_analysis'] = analysis
        except Exception as e:
            logger.error(f"Gap analysis generation failed: {str(e)}")
            # Fallback: use simple text summaries
            for candidate in candidates:
                candidate['gap_analysis'] = f"Score: {candidate.get('final_score', 0):.1f}/100"
        
        # Step 5: Rank candidates deterministically
        logger.info(f"[Pipeline] Step 5: Ranking candidates")
        session_manager.set_progress(session_id, 'Ranking candidates', 90)
        
        ranked = ranker.rank_candidates(candidates)
        ranked = ranker.assign_ranks(ranked)
        
        # Step 6: Generate summary statistics
        logger.info(f"[Pipeline] Step 6: Generating summary")
        summary = ranker.get_ranking_summary(ranked)
        
        elapsed = time.time() - start_time
        logger.info(
            f"[Pipeline] Completed in {elapsed:.2f}s - "
            f"Processed: {len(candidates)}, Failed: {len(failed_files)}, "
            f"Top scorer: {summary.get('top_scorer')} ({summary.get('average_score'):.1f} avg)"
        )
        
        return {
            'ranked_candidates': ranked,
            'summary': summary,
            'job_skills': job_skills,
            'total_processed': len(candidates),
            'failed_count': len(failed_files),
            'processing_time_seconds': round(elapsed, 2)
        }
        
    except Exception as e:
        logger.error(f"[Pipeline] Critical error: {str(e)}", exc_info=True)
        session_manager.set_progress(session_id, 'Error', 0, error=str(e))
        raise


# ========== Application Startup ==========

# Development only — Railway uses gunicorn (see Procfile)
# Do NOT set debug=True in production

if __name__ == "__main__":
    logger.info("Starting Resume Ranking System")
    logger.info(f"Upload folder: {config.UPLOAD_FOLDER}")
    logger.info(f"Max upload size: {config.MAX_UPLOAD_SIZE_MB}MB")
    logger.info("Mode: Local NLP (spaCy) — no API key required")

    # Run Flask app
    app.run(debug=not config.is_production(), port=config.PORT, host=config.HOST)
