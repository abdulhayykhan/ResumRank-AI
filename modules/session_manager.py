"""
Session Manager for Resume Ranking System
==========================================

File-based session storage to persist data across server restarts.
Uses JSON files in a sessions folder to store results and progress.

This ensures that on Railway or other cloud platforms, sessions aren't
lost when the application restarts or scales.
"""

import json
import os
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, Any
from pathlib import Path

logger = logging.getLogger(__name__)


class SessionManager:
    """Manages session data with file-based persistence."""
    
    def __init__(self, storage_dir: str = "sessions"):
        """
        Initialize session manager.
        
        Args:
            storage_dir: Directory to store session JSON files
        """
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(exist_ok=True)
        logger.info(f"SessionManager initialized with storage: {self.storage_dir}")
    
    def _get_session_path(self, session_id: str, store_type: str = "results") -> Path:
        """Get file path for a session."""
        return self.storage_dir / f"{session_id}_{store_type}.json"
    
    def set_results(self, session_id: str, data: Dict) -> None:
        """
        Store results data for a session.
        
        Args:
            session_id: Unique session identifier
            data: Session data to store (will be JSON serialized)
        """
        try:
            filepath = self._get_session_path(session_id, "results")
            
            # Add timestamp for cleanup
            data['_stored_at'] = datetime.now().isoformat()
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, default=str)
                
            logger.debug(f"Stored results for session {session_id}")
        except Exception as e:
            logger.error(f"Failed to store results for {session_id}: {e}")
    
    def get_results(self, session_id: str) -> Optional[Dict]:
        """
        Retrieve results data for a session.
        
        Args:
            session_id: Unique session identifier
            
        Returns:
            Session data dict or None if not found
        """
        try:
            filepath = self._get_session_path(session_id, "results")
            
            if not filepath.exists():
                return None
            
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            logger.debug(f"Retrieved results for session {session_id}")
            return data
        except Exception as e:
            logger.error(f"Failed to retrieve results for {session_id}: {e}")
            return None
    
    def has_results(self, session_id: str) -> bool:
        """Check if session results exist."""
        return self._get_session_path(session_id, "results").exists()
    
    def set_progress(self, session_id: str, step: str, percent: int, error: str = None) -> None:
        """
        Store progress data for a session.
        
        Args:
            session_id: Unique session identifier
            step: Current processing step description
            percent: Progress percentage (0-100)
            error: Optional error message
        """
        try:
            filepath = self._get_session_path(session_id, "progress")
            
            data = {
                'step': step,
                'percent': percent,
                'updated_at': datetime.now().isoformat()
            }
            
            if error:
                data['error'] = error
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
                
            logger.debug(f"Stored progress for session {session_id}: {percent}%")
        except Exception as e:
            logger.error(f"Failed to store progress for {session_id}: {e}")
    
    def get_progress(self, session_id: str) -> Dict[str, Any]:
        """
        Retrieve progress data for a session.
        
        Args:
            session_id: Unique session identifier
            
        Returns:
            Progress data dict with 'step' and 'percent' keys
            Returns default if not found
        """
        try:
            filepath = self._get_session_path(session_id, "progress")
            
            if not filepath.exists():
                return {'step': 'Initializing', 'percent': 0}
            
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            return data
        except Exception as e:
            logger.error(f"Failed to retrieve progress for {session_id}: {e}")
            return {'step': 'Initializing', 'percent': 0}
    
    def delete_session(self, session_id: str) -> None:
        """
        Delete all data for a session.
        
        Args:
            session_id: Unique session identifier
        """
        try:
            for store_type in ['results', 'progress']:
                filepath = self._get_session_path(session_id, store_type)
                if filepath.exists():
                    filepath.unlink()
            
            logger.debug(f"Deleted session {session_id}")
        except Exception as e:
            logger.error(f"Failed to delete session {session_id}: {e}")
    
    def cleanup_old_sessions(self, hours: int = 1) -> int:
        """
        Remove sessions older than specified hours.
        
        Args:
            hours: Maximum age of sessions in hours
            
        Returns:
            Number of sessions cleaned up
        """
        try:
            cutoff_time = datetime.now() - timedelta(hours=hours)
            cleaned_count = 0
            
            # Check all result files
            for filepath in self.storage_dir.glob("*_results.json"):
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    stored_at_str = data.get('_stored_at')
                    if stored_at_str:
                        stored_at = datetime.fromisoformat(stored_at_str)
                        
                        if stored_at < cutoff_time:
                            # Extract session_id from filename
                            session_id = filepath.stem.replace('_results', '')
                            self.delete_session(session_id)
                            cleaned_count += 1
                except Exception as e:
                    logger.warning(f"Failed to cleanup {filepath}: {e}")
            
            if cleaned_count > 0:
                logger.info(f"Cleaned up {cleaned_count} old sessions (>{hours}h)")
            
            return cleaned_count
        except Exception as e:
            logger.error(f"Session cleanup failed: {e}")
            return 0


# Global session manager instance
_session_manager = None


def get_session_manager() -> SessionManager:
    """Get or create the global session manager instance."""
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager()
    return _session_manager
