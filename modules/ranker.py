"""
Ranking & Tie-Breaking Module for Resume Ranking System
========================================================

Ranks candidates deterministically using a multi-level sorting strategy:
1. Primary: final_score descending (highest first)
2. Tie-break 1: skill_score descending
3. Tie-break 2: experience_score descending
4. Tie-break 3: candidate_name ascending (alphabetical)

Handles ties using DENSE RANKING: candidates with identical 
(final_score, skill_score, experience_score) get the same rank, 
and the next rank continues sequentially (e.g., 1, 1, 2, 3, 3, 4).

Functions:
  - rank_candidates(candidates) → sorted list
  - assign_ranks(ranked) → add "rank" field with dense ranking
  - get_top_candidates(ranked, top_n=5) → return top N candidates
  - get_ranking_summary(ranked) → return summary stats with distribution

All functions use type hints and have comprehensive docstrings.
"""

import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


def rank_candidates(candidates: List[Dict]) -> List[Dict]:
    """
    Sort candidates deterministically using multi-level tie-breaking.
    
    Sorting priority (in order):
      1. final_score descending (highest first)
      2. skill_score descending (tie-breaker)
      3. experience_score descending (tie-breaker)
      4. candidate_name ascending (alphabetical, last resort)
    
    This ensures deterministic, repeatable ranking across runs.
    No ties are broken randomly — everything is algorithmic.
    
    Args:
        candidates: List of candidate dicts, each with:
            - "final_score": float (0-100)
            - "skill_score": float (0-100)
            - "experience_score": float (0-100)
            - "candidate_name": str (full name)
            - (other fields preserved)
    
    Returns:
        List[Dict]: Same candidates, sorted by the tie-breaking strategy.
                    Order is: highest final_score first, with ties broken deterministically.
    
    Example:
        >>> candidates = [
        ...     {"candidate_name": "Alice", "final_score": 85.5, "skill_score": 90.0, "experience_score": 80.0},
        ...     {"candidate_name": "Bob", "final_score": 85.5, "skill_score": 88.0, "experience_score": 82.0},
        ...     {"candidate_name": "Carol", "final_score": 92.0, "skill_score": 95.0, "experience_score": 85.0},
        ... ]
        >>> ranked = rank_candidates(candidates)
        >>> [c["candidate_name"] for c in ranked]
        ['Carol', 'Alice', 'Bob']  # Carol highest, then Alice (higher skill), then Bob
    """
    if not candidates:
        logger.warning("No candidates provided to rank_candidates()")
        return []
    
    # Sort using tuple key for multi-level sorting
    # negative scores for descending, positive for ascending
    sorted_candidates = sorted(
        candidates,
        key=lambda x: (
            -x.get("final_score", 0),                    # 1. final_score descending (negative for reverse)
            -x.get("skill_score", 0),                    # 2. skill_score descending
            -x.get("experience_score", 0),               # 3. experience_score descending
            x.get("candidate_name", "").lower()          # 4. candidate_name ascending (alphabetical)
        )
    )
    
    logger.debug(f"Ranked {len(sorted_candidates)} candidates")
    return sorted_candidates



def assign_ranks(ranked_candidates: List[Dict]) -> List[Dict]:
    """
    Add rank numbers to sorted candidates, handling ties with dense ranking.
    
    Uses DENSE RANKING (1-2-2-3 style):
      If two candidates have identical (final_score, skill_score, experience_score),
      they are assigned the SAME rank number, and the next rank continues sequentially.
      
    Example with ties:
      Candidate 1: score 95.0, skill 90.0, experience 80.0 → rank 1
      Candidate 2: score 95.0, skill 90.0, experience 80.0 → rank 1 (identical triple)
      Candidate 3: score 90.0, skill 85.0, experience 70.0 → rank 2 (next sequential number)
      Candidate 4: score 85.0, skill 80.0, experience 60.0 → rank 3
    
    Args:
        ranked_candidates: List of candidates that are already sorted by rank_candidates().
                          Each dict should have: final_score, skill_score, experience_score, etc.
    
    Returns:
        List[Dict]: Same candidates with added "rank" field (1, 2, 3...).
                    Returns empty list if input is empty.
    
    Example:
        >>> ranked = [
        ...     {"candidate_name": "Alice", "final_score": 90.0, "skill_score": 85.0, "experience_score": 80.0},
        ...     {"candidate_name": "Bob", "final_score": 90.0, "skill_score": 85.0, "experience_score": 80.0},
        ...     {"candidate_name": "Carol", "final_score": 80.0, "skill_score": 75.0, "experience_score": 70.0},
        ... ]
        >>> with_ranks = assign_ranks(ranked)
        >>> [(c["candidate_name"], c["rank"]) for c in with_ranks]
        [('Alice', 1), ('Bob', 1), ('Carol', 2)]  # Alice & Bob tied at 1, Carol at 2 (dense ranking)
    """
    if not ranked_candidates:
        logger.warning("No candidates provided to assign_ranks()")
        return []
    
    # Create a list to hold candidates with rank field
    ranked_with_numbers = []
    current_rank = 1
    
    for i, candidate in enumerate(ranked_candidates):
        # Check if this candidate has same score trio as previous
        if i > 0:
            prev = ranked_candidates[i - 1]
            curr = candidate
            
            # If score triple is identical, use same rank as previous
            if (
                prev.get("final_score") == curr.get("final_score")
                and prev.get("skill_score") == curr.get("skill_score")
                and prev.get("experience_score") == curr.get("experience_score")
            ):
                # Tied: keep same rank, don't increment
                pass
            else:
                # Not tied: increment to next rank (dense ranking)
                current_rank += 1
        
        # Add rank field to candidate
        candidate_copy = dict(candidate)  # Shallow copy to avoid modifying original
        candidate_copy["rank"] = current_rank
        ranked_with_numbers.append(candidate_copy)
    
    logger.debug(f"Assigned ranks to {len(ranked_with_numbers)} candidates")
    return ranked_with_numbers



def get_top_candidates(ranked: List[Dict], top_n: int = 5) -> List[Dict]:
    """
    Extract the top N candidates from a ranked list.
    
    Args:
        ranked: List of candidates that have been ranked (ideally with "rank" field).
               Assumes this list is already sorted by rank_candidates().
        top_n: Maximum number of top candidates to return. Defaults to 5.
               If top_n is negative or zero, returns empty list.
               If top_n > len(ranked), returns all candidates.
    
    Returns:
        List[Dict]: Up to top_n candidates from the start of the ranked list.
    
    Example:
        >>> ranked = [
        ...     {"candidate_name": "Alice", "final_score": 90.0, "rank": 1},
        ...     {"candidate_name": "Bob", "final_score": 85.0, "rank": 2},
        ...     {"candidate_name": "Carol", "final_score": 80.0, "rank": 3},
        ...     {"candidate_name": "Diana", "final_score": 75.0, "rank": 4},
        ...     {"candidate_name": "Eve", "final_score": 70.0, "rank": 5},
        ... ]
        >>> top_3 = get_top_candidates(ranked, top_n=3)
        >>> len(top_3)
        3
        >>> [c["candidate_name"] for c in top_3]
        ['Alice', 'Bob', 'Carol']
    """
    if not ranked:
        logger.warning("No candidates provided to get_top_candidates()")
        return []
    
    if top_n <= 0:
        logger.warning(f"Invalid top_n value: {top_n}. Returning empty list.")
        return []
    
    # Return up to top_n candidates
    top_candidates = ranked[:top_n]
    logger.debug(f"Extracted top {len(top_candidates)} candidates from {len(ranked)} total")
    return top_candidates



def get_ranking_summary(ranked: List[Dict]) -> Dict:
    """
    Generate summary statistics from a ranked candidate list.
    
    Calculates:
      - total_candidates: Number of candidates ranked
      - top_scorer: Name of highest-ranked candidate
      - average_score: Mean of all final_score values
      - score_distribution: Breakdown by score ranges
          - "excellent(80+)": Count with score >= 80
          - "good(60-79)": Count with score in [60, 79]
          - "average(40-59)": Count with score in [40, 59]
          - "weak(<40)": Count with score < 40
    
    Args:
        ranked: List of candidates (can be ranked or unsorted).
               Each dict should have "final_score" and "candidate_name" fields.
    
    Returns:
        Dict with structure:
        {
            "total_candidates": int,
            "top_scorer": str,
            "average_score": float (rounded to 2 decimals),
            "score_distribution": {
                "excellent(80+)": int,
                "good(60-79)": int,
                "average(40-59)": int,
                "weak(<40)": int
            }
        }
        
        Returns structure with zeros/None if ranked is empty.
    
    Example:
        >>> ranked = [
        ...     {"candidate_name": "Alice", "final_score": 92.5},
        ...     {"candidate_name": "Bob", "final_score": 75.0},
        ...     {"candidate_name": "Carol", "final_score": 68.5},
        ... ]
        >>> summary = get_ranking_summary(ranked)
        >>> summary["total_candidates"]
        3
        >>> summary["top_scorer"]
        'Alice'
        >>> summary["average_score"]
        78.67
        >>> summary["score_distribution"]["excellent(80+)"]
        1
    """
    if not ranked:
        logger.warning("No candidates provided to get_ranking_summary()")
        return {
            "total_candidates": 0,
            "top_scorer": None,
            "average_score": 0.0,
            "score_distribution": {
                "excellent(80+)": 0,
                "good(60-79)": 0,
                "average(40-59)": 0,
                "weak(<40)": 0
            }
        }
    
    total = len(ranked)
    top_scorer = ranked[0].get("candidate_name", "Unknown") if ranked else None
    
    # Calculate average score
    scores = [c.get("final_score", 0) for c in ranked if c.get("final_score") is not None]
    average_score = round(sum(scores) / len(scores), 2) if scores else 0.0
    
    # Distribution by score ranges
    distribution = {
        "excellent(80+)": sum(1 for c in ranked if c.get("final_score", 0) >= 80),
        "good(60-79)": sum(1 for c in ranked if 60 <= c.get("final_score", 0) < 80),
        "average(40-59)": sum(1 for c in ranked if 40 <= c.get("final_score", 0) < 60),
        "weak(<40)": sum(1 for c in ranked if c.get("final_score", 0) < 40)
    }
    
    summary = {
        "total_candidates": total,
        "top_scorer": top_scorer,
        "average_score": average_score,
        "score_distribution": distribution
    }
    
    logger.debug(f"Generated summary for {total} candidates. Top: {top_scorer}, Avg: {average_score}")
    return summary


# Export public functions
__all__ = [
    "rank_candidates",
    "assign_ranks",
    "get_top_candidates",
    "get_ranking_summary"
]
