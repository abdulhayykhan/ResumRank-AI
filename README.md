# ResumRank AI (Transparent Skill-Based Resume Ranking System)

A role-aware resume ranking web app built with Flask, spaCy NLP, and Vanilla JS. ResumRank AI was developed as part of the **Ramadan Hackathon 2026** by **CIS Community NEDUET**. It showcases local NLP processing, deterministic scoring algorithms, multi-stage pipeline design, and transparent result generation in a full-stack context.

---

## Overview

The project demonstrates practical NLP and web engineering applied to a real hiring problem: parsing PDF resumes, extracting skills and experience using local language models, scoring candidates against a job description, and ranking them with full explainability. Features emphasize how backend processing maps to real-world HR entities (resumes, job requirements, skill gaps, experience levels) with clear pipeline stages and no reliance on external AI APIs.

---

## System Architecture

![System Architecture & Logic Diagram](static/System%20Architecture%20%26%20Logic%20Diagram.png)

---

## Features

- **PDF Parsing**: Multi-page text and table extraction using pdfplumber; detects and warns on scanned/image-only PDFs (< 100 characters extracted).
- **Local NLP Extraction**: spaCy `en_core_web_sm` for named entity recognition; regex date-range parsing for experience calculation; 500+ tech skill keyword database with alias resolution.
- **Deterministic Scoring**: Transparent formula — `Final Score = (Skill Match × 70%) + (Experience Score × 30%)`; every score is reproducible, auditable, and explainable.
- **Intelligent Ranking**: Multi-level tie-breaking — final score → skill score → experience score → alphabetical name; identical triple scores receive the same rank number.
- **Gap Analysis**: Template-based human-readable explanations per candidate across four tiers — Strong Match (80+), Moderate Match (60–79), Weak Match (40–59), and Not Recommended (< 40).
- **Results Dashboard**: Sortable rankings table, color-coded score badges, skill pills (matched/missing), expandable per-candidate gap analysis rows, and summary statistics bar.
- **CSV Export**: Timestamped download with candidate names, scores, matched/missing skills, gap analysis text, and experience years.
- **Duplicate Detection**: MD5 hash check on uploaded files; blocks identical resumes in the same batch regardless of filename.
- **Rate Limiting**: 5 analyses per minute per IP enforced in-memory with rolling time windows.
- **Auto Cleanup**: Uploaded files deleted immediately after processing; sessions and results expire after 1 hour.
- **No API Keys Required**: Entire pipeline runs locally — no Gemini, no OpenAI, no external services, no cost.

---

## Technologies Used

| Component | Purpose |
|---|---|
| Python / Flask | Web framework, routing, pipeline orchestration |
| spaCy en_core_web_sm | Local NLP — named entity recognition and skill extraction |
| pdfplumber | PDF text and table extraction |
| Pandas / NumPy | CSV generation and data manipulation |
| Gunicorn | Production WSGI server |
| Custom CSS (dark theme) | Professional UI, responsive layout, no framework dependencies |
| Vanilla JS | Drag-drop upload, real-time progress polling, results table sorting |

---

## Project Structure

```
ResumRank/
├── app.py                   # Flask app, routes, pipeline orchestrator, session management
├── config.py                # Constants, scoring weights, environment settings
├── .env.example             # Environment variable template
├── .gitignore               # Ignore rules for temp/test artifacts
├── .railwayignore           # Railway ignore rules
├── requirements.txt         # Python dependencies
├── runtime.txt              # Python version pin (3.11)
├── Procfile                 # Railway deployment command
├── railway.json             # Railway platform config
├── test_nlp.py              # Pipeline verification test suite (5 tests)
│
├── modules/
│   ├── __init__.py          # Package imports + spaCy setup verification
│   ├── skills_db.py         # 500+ tech skills database with aliases and normalization
│   ├── skill_extractor.py   # spaCy NLP + regex extraction pipeline
│   ├── scorer.py            # Weighted scoring engine + gap analysis templates
│   ├── ranker.py            # Deterministic ranking and tie-breaking logic
│   ├── pdf_parser.py        # PDF text extraction with edge case handling
│   ├── session_manager.py   # File-based session persistence for Railway deployments
│   └── exporter.py          # CSV generation and formatting
│
├── templates/
│   ├── index.html           # Upload page with drag-drop and real-time progress bar
│   ├── results.html         # Rankings dashboard with sorting and CSV export
│   └── error.html           # Error page template
│
├── static/
│   ├── css/style.css        # Dark professional theme
│   ├── js/main.js           # Drag-drop, progress polling, column sorting
│   └── favicon.svg          # Bar chart logo icon
│
└── README.md
```

---

## Installation and Setup

1. Clone the repo and navigate into the project folder.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Download the spaCy language model (one-time, ~150MB):
   ```bash
   python -m spacy download en_core_web_sm
   ```
4. (Optional) Create a `.env` file for custom settings:
   ```
   APP_ENV=development
   SECRET_KEY=your-dev-secret
   PORT=5000
   ```
5. Run the development server:
   ```bash
   python app.py
   ```
6. Open [http://localhost:5000](http://localhost:5000) in your browser.

Environment variables (optional locally, required in production):
- `SECRET_KEY` — Flask session secret; generate with `python -c "import secrets; print(secrets.token_hex(32))"`
- `APP_ENV` — Set to `production` on Railway; defaults to `development`
- `PORT` — Set automatically by Railway; defaults to `5000`

---

## Usage Guide

1. **Upload Resumes** — Drag and drop up to 10 PDF files onto the upload zone (or click Browse). Files are validated for type, size (max 10MB), and duplicates before saving.
2. **Paste Job Description** — Enter the full job posting including required skills, experience, and responsibilities (minimum 20 words for reliable extraction).
3. **Analyze** — Click Analyze and watch real-time progress as PDFs are parsed, skills extracted, scored, and ranked.
4. **Review Results** — View the ranked table showing final scores, skill match percentages, experience scores, years, matched skills, and missing skills per candidate.
5. **Expand Gap Analysis** — Click any candidate row to see a full written explanation of their strengths, gaps, and hire recommendation.
6. **Export** — Download a timestamped CSV for use in your ATS or hiring workflow.

---

## NLP and Scoring Concepts Illustrated

| Concept | How It Appears in ResumRank AI |
|---|---|
| Named Entity Recognition | spaCy PERSON entities extract candidate names from resume headers |
| Regex-based Date Parsing | Date range patterns calculate years of experience from work history |
| Keyword Matching | Word-boundary regex matches 500+ skills against resume and job text |
| Alias Resolution | Skill aliases normalize variations (React.js → react, k8s → kubernetes) |
| Education Context Filtering | Proximity heuristic excludes education-section dates from experience calculation |
| Fallback Chains | Name extraction tries NER → regex → cleaned filename as progressive fallbacks |
| Weighted Scoring | Two-component formula with configurable weights (70/30 split) |
| Deterministic Ranking | Multi-key sort guarantees identical input always produces identical output |

### Deeper Pipeline Walkthrough

- **Skill extraction accuracy**: Word-boundary matching (`\bpython\b`) prevents false positives — "r" won't match "react", "go" won't match "good". All known aliases for a skill are checked independently and deduplicated before scoring, so "React.js" and "React" in the same resume count once.
- **Experience calculation**: All date ranges in a resume are parsed across four formats (full month name, abbreviated month, MM/YYYY, year-only). Education-context ranges are filtered by checking for proximity to keywords (university, bachelor, degree, gpa). The max-span approach (earliest start date → latest end date) avoids double-counting overlapping jobs.
- **Gap analysis tiers**: Candidates scoring 80+ receive "Strong Match" with immediate interview recommendation; 60–79 "Moderate Match" with skills-assessment suggestion; 40–59 "Weak Match" with training caveat; below 40 "Not Recommended" with specific missing areas listed.
- **Deterministic ranking**: The multi-key sort `(-final_score, -skill_score, -experience_score, name)` guarantees the same input always produces the same ranking, making results auditable and reproducible.
- **Tied ranks**: Candidates sharing identical (final_score, skill_score, experience_score) receive the same rank number and subsequent ranks are skipped (e.g., 1, 1, 3), not compressed.
- **Session isolation**: Each analysis gets a UUID; results, progress, and uploaded files are keyed to that UUID and cleaned up independently without affecting concurrent sessions.

### Data Integrity and Reliability Notes

- **Input validation before processing**: File type, file size, job description word count, and MD5 duplicate hashes are all checked before any file is saved or pipeline invoked.
- **Graceful degradation**: If spaCy NER fails to extract a name, the extractor falls back to regex, then to a cleaned version of the filename — the pipeline never crashes on a missing field.
- **Batch resilience**: If skill extraction fails for one candidate in a batch, that candidate receives zero scores and a fallback entry; other candidates still score and rank correctly.
- **Safe cleanup**: File deletion and session removal use patterns that don't raise if a key or file is already gone — idempotent by design.
- **Scanned PDF handling**: PDFs yielding fewer than 100 characters are flagged as likely scanned images with a visible warning badge; they receive a fallback empty extraction rather than crashing.

### Performance Notes

| Scenario | Typical Time |
|---|---|
| Parse 1 PDF | 0.5–2 sec |
| Extract skills (1 resume) | 0.3–1 sec |
| Score + rank 5 resumes | < 1 sec |
| Full pipeline (5 resumes) | 5–10 sec total |

No network latency. No rate limits. No API quotas.

### Suggested Experiments

- Extend the skills database (`skills_db.py`) with domain-specific skills and observe how scoring shifts for resumes in that domain.
- Adjust the scoring weights in `config.py` (`SKILL_WEIGHT`, `EXPERIENCE_WEIGHT`) and re-run the same batch to compare ranking outcomes.
- Add a new experience tier (e.g., 8+ years → 110) and observe how it affects candidates with long careers.
- Test the education-context filter by adding a resume where work dates and graduation dates overlap — confirm the experience calculation excludes the degree years.
- Run `test_nlp.py` after modifying an alias in `skills_db.py` to see the validation catch broken canonical mappings.

---

## Testing

```bash
python test_nlp.py
```

Runs 5 verification tests covering the full pipeline:

1. **spaCy Installation** — model loads without error and version is confirmed
2. **Skills Database** — all 500+ skills present, aliases resolve to valid canonicals, `validate_skills_database()` passes
3. **Job Skill Parsing** — expected skills extracted from a sample job description
4. **Resume Extraction** — name, email, experience years, skills found, relevant/missing skills all parse correctly from a sample resume
5. **Gap Analysis** — all four scoring tiers produce correctly labelled, appropriately worded output

All 5 tests pass after model download. Expected output:
```
Results: 5/5 tests passed
✅ All tests passed — ready to deploy!
```

---

## Deployment

### Railway (Free Tier)

1. Push to GitHub.
2. Connect the repo to [Railway](https://railway.app).
3. Add environment variables in the Railway dashboard:
   - `APP_ENV` = `production`
   - `SECRET_KEY` = *(generate a random 32-byte hex string)*
4. Railway detects the `Procfile` automatically. The spaCy model downloads on first start (~30 seconds cold start).

**Cost:** Free on Railway Starter (500 hours/month included).

### Local Development

```bash
python app.py
# Runs on http://localhost:5000
```

---

## Author

[Abdul Hayy Khan](https://www.linkedin.com/in/abdul-hayy-khan/)  
abdulhayykhan.1@gmail.com

---

## License

This project is open-source and available for educational and commercial use under the **MIT License**.
