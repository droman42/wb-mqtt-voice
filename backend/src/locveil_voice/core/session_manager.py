"""
Session Manager

Unified session ID generation and management across all components.
Provides consistent session ID format and room-scoped session boundaries
for fire-and-forget actions and contextual command resolution.
"""

import uuid
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class SessionManager:
    """Unified session ID generation and management across all components"""
    
    @staticmethod
    def generate_session_id(source: str, room_id: Optional[str] = None, 
                           client_id: Optional[str] = None) -> str:
        """Generate consistent session ID across all components
        
        Single-user system: Room sessions represent physical locations.
        
        Args:
            source: Source component/system generating the session (e.g., "api", "cli", "tts")
            room_id: Room identifier for room-scoped sessions (e.g., "kitchen", "living_room")
            client_id: Client identifier for client-scoped sessions (e.g., "browser_abc123")
            
        Returns:
            Session ID in format:
            - Room-based: "{room_id}_session" (e.g., "kitchen_session") - PRIMARY for IoT
            - Client-based: "{client_id}_session" (e.g., "browser_abc123_session") - For web clients
            - Generated: "{source}_{uuid8}_session" (e.g., "web_a1b2c3d4_session") - Fallback
        """
        if room_id:
            session_id = f"{room_id}_session"
            logger.debug(f"Generated room-scoped session ID: {session_id}")
            return session_id
        elif client_id:
            session_id = f"{client_id}_session"
            logger.debug(f"Generated client-scoped session ID: {session_id}")
            return session_id
        else:
            session_id = f"{source}_{uuid.uuid4().hex[:8]}_session"
            logger.debug(f"Generated fallback session ID: {session_id}")
            return session_id
        
    def validate_session_id(self, session_id: str) -> bool:
        """Validate session ID format and structure
        
        Args:
            session_id: Session ID to validate
            
        Returns:
            True if session ID follows expected format, False otherwise
        """
        is_valid = "_session" in session_id and len(session_id) > 8
        logger.debug(f"Session ID validation: {session_id} -> {is_valid}")
        return is_valid
        
