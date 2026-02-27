#!/usr/bin/env python
"""
NLP Pipeline Test Script
========================

Standalone test script to verify the entire no-API-key pipeline works
correctly before deploying to Railway.

Run with: python test_nlp.py
Should complete in under 5 seconds.
"""

import sys
import time
from datetime import datetime


def print_test_header(test_name: str):
    """Print a formatted test section header."""
    print(f"\n{'='*60}")
    print(f"TEST: {test_name}")
    print('='*60)


def print_success(message: str):
    """Print a success message."""
    print(f"✅ {message}")


def print_failure(message: str):
    """Print a failure message."""
    print(f"❌ {message}")


def test_spacy_installation():
    """Test 1: Check spaCy is installed and model is available."""
    print_test_header("spaCy Installation & Model Availability")
    
    try:
        import spacy
        print_success("spaCy library is installed")
        
        try:
            nlp = spacy.load("en_core_web_sm")
            print_success("spaCy model 'en_core_web_sm' is loaded")
            print(f"   Model version: {nlp.meta.get('version', 'unknown')}")
            return True
        except OSError:
            print_failure("spaCy model 'en_core_web_sm' not found")
            print("   Fix: Run 'python -m spacy download en_core_web_sm'")
            return False
            
    except ImportError:
        print_failure("spaCy library not installed")
        print("   Fix: Run 'pip install spacy>=3.7.0'")
        return False


def test_skills_database():
    """Test 2: Test skills_db.py module."""
    print_test_header("Skills Database Module")
    
    try:
        from modules.skills_db import ALL_SKILLS, normalize_skill
        
        # Test 1: Count skills
        skill_count = len(ALL_SKILLS)
        print_success(f"ALL_SKILLS loaded: {skill_count} skills in database")
        if skill_count < 100:
            print_failure(f"Expected at least 100 skills, got {skill_count}")
            return False
        
        # Test 2: normalize_skill function
        test_cases = [
            ("React.js", "react"),
            ("Node.js", "nodejs"),
            ("PostgreSQL", "postgresql"),
            ("k8s", "kubernetes"),
        ]
        
        all_passed = True
        for input_skill, expected in test_cases:
            result = normalize_skill(input_skill)
            if result == expected:
                print_success(f"normalize_skill('{input_skill}') = '{result}'")
            else:
                print_failure(f"normalize_skill('{input_skill}') = '{result}', expected '{expected}'")
                all_passed = False
        
        # Test 3: Check common skills exist
        common_skills = ["python", "javascript", "react", "docker", "git"]
        for skill in common_skills:
            if skill in ALL_SKILLS:
                print_success(f"'{skill}' found in ALL_SKILLS")
            else:
                print_failure(f"'{skill}' NOT found in ALL_SKILLS")
                all_passed = False
        
        return all_passed
        
    except ImportError as e:
        print_failure(f"Could not import skills_db: {e}")
        return False
    except Exception as e:
        print_failure(f"Unexpected error: {e}")
        return False


def test_parse_job_skills():
    """Test 3: Test parse_job_skills() function."""
    print_test_header("Job Description Skill Extraction")
    
    try:
        from modules.skill_extractor import parse_job_skills
        
        sample_jd = """
        We are looking for a Full Stack Developer with strong Python and React skills.
        Experience with PostgreSQL, Docker, and AWS is required.
        Knowledge of Git, REST APIs, and CI/CD pipelines is a plus.
        """
        
        print("Job Description:")
        print(sample_jd.strip())
        print()
        
        skills = parse_job_skills(sample_jd)
        
        print(f"Extracted {len(skills)} skills:")
        print(f"   {', '.join(sorted(skills))}")
        print()
        
        # Check for expected skills
        expected_skills = ["python", "react", "postgresql", "docker", "aws", "git", "rest"]
        all_found = True
        
        for skill in expected_skills:
            if skill in skills:
                print_success(f"Found expected skill: '{skill}'")
            else:
                print_failure(f"Missing expected skill: '{skill}'")
                all_found = False
        
        return all_found
        
    except ImportError as e:
        print_failure(f"Could not import skill_extractor: {e}")
        return False
    except Exception as e:
        print_failure(f"Unexpected error: {e}")
        return False


def test_extract_skills_and_experience():
    """Test 4: Test extract_skills_and_experience() function."""
    print_test_header("Resume Extraction Pipeline")
    
    try:
        from modules.skill_extractor import extract_skills_and_experience
        
        sample_resume = """
        John Smith | john@example.com
        
        EXPERIENCE
        Senior Developer at TechCorp, Jan 2021 – Present
        Backend Developer at StartupX, Jun 2019 – Dec 2020
        
        SKILLS
        Python, Django, React, PostgreSQL, Docker, Git, REST APIs
        
        EDUCATION  
        BS Computer Science, NEDUET, 2019
        """
        
        sample_jd = """
        We are looking for a Full Stack Developer with strong Python and React skills.
        Experience with PostgreSQL, Docker, and AWS is required.
        """
        
        print("Resume:")
        print(sample_resume.strip())
        print()
        
        result = extract_skills_and_experience(sample_resume, sample_jd)
        
        # Print all fields
        print("Extraction Results:")
        print(f"   Candidate Name: {result.get('candidate_name')}")
        print(f"   Email: {result.get('email')}")
        print(f"   Years of Experience: {result.get('years_of_experience')}")
        print(f"   Education: {result.get('education')}")
        print(f"   Skills Found ({len(result.get('skills_found', []))}): {', '.join(result.get('skills_found', []))}")
        print(f"   Relevant Skills ({len(result.get('relevant_skills', []))}): {', '.join(result.get('relevant_skills', []))}")
        print(f"   Missing Skills ({len(result.get('missing_skills', []))}): {', '.join(result.get('missing_skills', []))}")
        print(f"   Experience Details: {result.get('experience_details')}")
        print(f"   Extraction Success: {result.get('extraction_success')}")
        print()
        
        # Validate results
        all_passed = True
        
        if result.get('candidate_name'):
            print_success(f"Candidate name extracted: '{result['candidate_name']}'")
        else:
            print_failure("Candidate name not extracted")
            all_passed = False
        
        if result.get('email') == 'john@example.com':
            print_success(f"Email extracted: '{result['email']}'")
        else:
            print_failure(f"Email not correctly extracted: {result.get('email')}")
            all_passed = False
        
        if result.get('years_of_experience') and result['years_of_experience'] > 4:
            print_success(f"Years of experience calculated: {result['years_of_experience']} years")
        else:
            print_failure(f"Years of experience incorrect: {result.get('years_of_experience')}")
            all_passed = False
        
        expected_skills = ["python", "django", "react", "postgresql", "docker", "git"]
        skills_found = result.get('skills_found', [])
        missing_expected = [s for s in expected_skills if s not in skills_found]
        
        if not missing_expected:
            print_success(f"All expected skills found in resume")
        else:
            print_failure(f"Missing expected skills: {', '.join(missing_expected)}")
            all_passed = False
        
        relevant = result.get('relevant_skills', [])
        if len(relevant) >= 4:
            print_success(f"Relevant skills matched: {len(relevant)} skills")
        else:
            print_failure(f"Too few relevant skills: {len(relevant)}")
            all_passed = False
        
        if result.get('extraction_success'):
            print_success("extraction_success flag is True")
        else:
            print_failure("extraction_success flag is False")
            all_passed = False
        
        return all_passed
        
    except ImportError as e:
        print_failure(f"Could not import skill_extractor: {e}")
        return False
    except Exception as e:
        print_failure(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_gap_analysis():
    """Test 5: Test generate_gap_analysis() function."""
    print_test_header("Gap Analysis Generation")
    
    try:
        from modules.scorer import generate_gap_analysis
        
        # Test all 4 tiers
        test_cases = [
            (85, "Strong Match", "John Doe"),
            (65, "Moderate Match", "Jane Smith"),
            (45, "Weak Match", "Bob Johnson"),
            (25, "Weak Match", "Alice Brown"),
        ]
        
        all_passed = True
        
        for score, expected_tier, name in test_cases:
            mock_candidate = {
                'candidate_name': name,
                'final_score': score,
                'years_of_experience': 5.0,
                'relevant_skills': ['python', 'react', 'docker'],
                'missing_skills': ['aws', 'kubernetes', 'terraform'],
            }
            
            analysis = generate_gap_analysis(mock_candidate, "Sample job description")
            
            print(f"\nScore: {score} (Expected: {expected_tier})")
            print(f"Analysis: {analysis}")
            
            # Check if analysis contains expected tier
            if expected_tier.upper() in analysis.upper():
                print_success(f"Gap analysis contains '{expected_tier}'")
            else:
                print_failure(f"Gap analysis doesn't contain '{expected_tier}'")
                all_passed = False
            
            # Check if analysis is reasonably long (professional)
            if len(analysis) > 100:
                print_success(f"Gap analysis is professional (length: {len(analysis)} chars)")
            else:
                print_failure(f"Gap analysis too short: {len(analysis)} chars")
                all_passed = False
            
            # Check if candidate name is mentioned
            if name in analysis:
                print_success(f"Candidate name '{name}' mentioned in analysis")
            else:
                print_failure(f"Candidate name '{name}' not mentioned")
                all_passed = False
        
        return all_passed
        
    except ImportError as e:
        print_failure(f"Could not import scorer: {e}")
        return False
    except Exception as e:
        print_failure(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests and print summary."""
    print("\n" + "="*60)
    print("ResumRank AI — NLP Pipeline Test Suite")
    print("No API Key Edition")
    print("="*60)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    start_time = time.time()
    
    # Run all tests
    results = {
        "spaCy Installation": test_spacy_installation(),
        "Skills Database": test_skills_database(),
        "Job Skill Parsing": test_parse_job_skills(),
        "Resume Extraction": test_extract_skills_and_experience(),
        "Gap Analysis": test_gap_analysis(),
    }
    
    elapsed_time = time.time() - start_time
    
    # Print summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = sum(results.values())
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")
    
    print("\n" + "-"*60)
    print(f"Results: {passed}/{total} tests passed")
    print(f"Time: {elapsed_time:.2f} seconds")
    print("-"*60)
    
    if passed == total:
        print("\n✅ All tests passed — ready to deploy!")
        return 0
    else:
        print(f"\n❌ {total - passed} test(s) failed — see errors above")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
