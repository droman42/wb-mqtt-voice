"""
Audio Playback Intent Handler - Music and audio control commands

Handles audio playback control commands that were previously hardcoded
in AudioComponent. Delegates to AudioComponent for actual functionality.
"""

import asyncio
import logging
import time
import uuid
from pathlib import Path
from typing import List, Dict, Optional

from .base import IntentHandler
from ..models import Intent, IntentResult
from ..context_models import UnifiedConversationContext
from ..ports import AudioPort

logger = logging.getLogger(__name__)


class AudioPlaybackIntentHandler(IntentHandler):
    """
    Handles audio playback intents - music/audio control commands.
    
    Features:
    - Audio playback control (play, stop)
    - Audio provider switching
    - Audio provider information display
    """
    
    def __init__(self):
        super().__init__()
        self._audio_component: Optional[AudioPort] = None

    # Build dependency methods (TODO #5 Phase 2)
    @classmethod
    def get_python_dependencies(cls) -> List[str]:
        """Audio playback handler needs no external dependencies"""
        return []
        
    @classmethod
    def get_platform_dependencies(cls) -> Dict[str, List[str]]:
        """Audio playback handler has no system dependencies"""
        return {
            "linux.ubuntu": [],
            "linux.alpine": [],
            "macos": [],
            "windows": []
        }
    async def execute(self, intent: Intent, context: UnifiedConversationContext) -> IntentResult:
        """Execute audio playback intent"""
        # Use donation-driven routing exclusively
        return await self.execute_with_donation_routing(intent, context)
        
    async def _handle_play_audio(self, intent: Intent, context: UnifiedConversationContext) -> IntentResult:
        """Handle audio playback request with fire-and-forget action execution"""
        # Phase 2 TODO16: No more stop command parsing - handlers only receive resolved intents
        
        # Extract audio file or track information
        audio_file = intent.entities.get("file", intent.entities.get("track", "default_audio"))
        source = intent.entities.get("source", "local")
        
        # Use language from context (detected by NLU)
        language = context.language
        
        # Use fire-and-forget action execution for audio playback
        playback_id = f"audio_{int(time.time() * 1000)}_{uuid.uuid4().hex[:6]}"
        action_metadata = await self.execute_fire_and_forget_with_context(
            self._start_audio_playback_action,
            action_name=playback_id,
            domain="audio",
            context=context,
            audio_file=audio_file,
            source=source,
            language=language
        )
        
        # Immediate response
        response_text = self._get_template("start_playback", language, audio_file=audio_file)
        
        return self.create_action_result(
            response_text=response_text,
            action_name=playback_id,
            domain="audio",
            should_speak=True,
            action_metadata=action_metadata
        )
        
    async def _handle_stop_audio(self, intent: Intent, context: UnifiedConversationContext) -> IntentResult:
        """
        Handle domain-specific audio stop intent (audio.stop).
        
        Phase 2 TODO16: Standardized stop handling - only receives resolved intents.
        """
        # Determine language
        language = context.language
        
        # Use fire-and-forget action execution for stopping audio
        stop_id = f"audio_stop_all_{int(time.time() * 1000)}_{uuid.uuid4().hex[:6]}"
        action_metadata = await self.execute_fire_and_forget_with_context(
            self._stop_audio_playback_action,
            action_name=stop_id,
            domain="audio",
            context=context,
            language=language
        )
        
        return self.create_action_result(
            response_text=self._get_template("stop_audio", language),
            action_name=stop_id,
            domain="audio",
            should_speak=True,
            action_metadata=action_metadata
        )
    
    async def _handle_pause_audio(self, intent: Intent, context: UnifiedConversationContext) -> IntentResult:
        """
        Handle domain-specific audio pause intent (audio.pause).
        
        Phase 2 TODO16: Standardized contextual command handling.
        """
        language = context.language
        
        # Use fire-and-forget action execution for pausing audio
        pause_id = f"audio_pause_{int(time.time() * 1000)}_{uuid.uuid4().hex[:6]}"
        action_metadata = await self.execute_fire_and_forget_with_context(
            self._pause_audio_playback_action,
            action_name=pause_id,
            domain="audio",
            context=context,
            language=language
        )
        
        return self.create_action_result(
            response_text=self._get_template("pause_audio", language),
            action_name=pause_id,
            domain="audio",
            should_speak=True,
            action_metadata=action_metadata
        )
    
    async def _handle_resume_audio(self, intent: Intent, context: UnifiedConversationContext) -> IntentResult:
        """
        Handle domain-specific audio resume intent (audio.resume).
        
        Phase 2 TODO16: Standardized contextual command handling.
        """
        language = context.language
        
        # Use fire-and-forget action execution for resuming audio
        resume_id = f"audio_resume_{int(time.time() * 1000)}_{uuid.uuid4().hex[:6]}"
        action_metadata = await self.execute_fire_and_forget_with_context(
            self._resume_audio_playback_action,
            action_name=resume_id,
            domain="audio",
            context=context,
            language=language
        )
        
        return self.create_action_result(
            response_text=self._get_template("resume_audio", language),
            action_name=resume_id,
            domain="audio",
            should_speak=True,
            action_metadata=action_metadata
        )
        
    async def _handle_switch_audio_provider(self, intent: Intent, context: UnifiedConversationContext) -> IntentResult:
        """Handle audio provider switching request"""
        audio_component = await self._get_audio_component()
        if not audio_component:
            return self._error_result(context, "Audio component not available")
        
        # Extract provider name from intent entities or text
        provider_name = intent.entities.get("provider")
        if not provider_name:
            provider_name = audio_component.parse_provider_name_from_text(intent.raw_text)
        
        if not provider_name:
            return self._error_result(context, "Provider name not specified")
        
        # Use language from context (detected by NLU)
        language = context.language
        
        success = audio_component.set_default_provider(provider_name)
        
        # Create appropriate response message
        if success:
            message = self._get_template("provider_switched", language, provider_name=provider_name)
        else:
            available = ", ".join(audio_component.providers.keys())
            message = self._get_template("provider_unknown", language, available=available)
        
        self.logger.info(f"Audio provider switch to {provider_name} - success: {success}")
        
        return IntentResult(
            text=message,
            should_speak=True,
            metadata={
                "action": "switch_provider",
                "provider": provider_name,
                "success": success,
                "language": language
            },
            success=success
        )
        
    async def _handle_list_audio_providers(self, intent: Intent, context: UnifiedConversationContext) -> IntentResult:
        """Handle audio providers information request"""
        audio_component = await self._get_audio_component()
        if not audio_component:
            return self._error_result(context, "Audio component not available")
        
        info = audio_component.get_providers_info()
        
        # Use language from context (detected by NLU)
        language = context.language
        
        self.logger.info(f"Audio providers info requested")
        
        return IntentResult(
            text=info,
            should_speak=True,
            metadata={
                "action": "list_providers",
                "language": language
            },
            success=True
        )
    
    async def _get_audio_component(self) -> Optional[AudioPort]:
        """Return the injected audio capability port (QUAL-24).

        Injected by the application via
        IntentComponent.post_initialize_handler_dependencies; the domain never
        reaches into core for it.
        """
        return self._audio_component
    def _resolve_media_file(self, name: str) -> Optional[Path]:
        """Resolve a media name to a file in the local audio library `<assets_root>/audio/` (e.g. a
        timer-done chime). Returns None if absent.

        PROVISIONAL: the text→media mapping is intentionally minimal and will be replaced — only the
        *playback wiring* downstream of this is final. `name` originates from an utterance, so it is
        clamped to a single safe filename (no separators / `..` / NUL) and the resolved path is verified
        to stay inside the media directory — an utterance must not read outside it."""
        loader = self.get_asset_loader()
        assets_root = getattr(loader, "assets_root", None) if loader else None
        if not assets_root:
            return None
        if not name or name in (".", "..") or "/" in name or "\\" in name or "\x00" in name:
            return None
        media_dir = (Path(assets_root) / "audio").resolve()
        for candidate in (name, f"{name}.wav", f"{name}.mp3", f"{name}.ogg"):
            resolved = (media_dir / candidate).resolve()
            if resolved.parent == media_dir and resolved.is_file():
                return resolved
        return None

    async def _start_audio_playback_action(self, audio_file: str, source: str, language: str) -> bool:
        """Fire-and-forget audio playback: resolve the media file from the local library and play it
        through the audio port. Returns True only when playback was actually dispatched."""
        try:
            if source != "local":
                self.logger.warning(f"Audio source '{source}' not supported (local media library only)")
                return False
            audio_component = await self._get_audio_component()
            if not audio_component:
                self.logger.error("Audio component not available for playback")
                return False
            path = self._resolve_media_file(audio_file)
            if path is None:
                self.logger.warning(f"Media file not found in the audio library: {audio_file!r}")
                return False
            await audio_component.play_file(path)
            self.logger.info(f"🎵 Audio playback started: {path}")
            return True
        except Exception as e:
            self.logger.error(f"Audio playback action failed: {e}")
            raise  # BUG-19: `return False` here recorded the action as SUCCESS in the store

    async def _pause_audio_playback_action(self, language: str) -> bool:
        """Pause audio playback action"""
        audio_component = await self._get_audio_component()
        if not audio_component:
            logger.error("Audio component not available for pause action")
            return False
        
        try:
            # Pause current audio playback
            await audio_component.pause_audio()
            logger.info("Audio playback paused successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to pause audio playback: {e}")
            return False
    
    async def _resume_audio_playback_action(self, language: str) -> bool:
        """Resume audio playback action"""
        audio_component = await self._get_audio_component()
        if not audio_component:
            logger.error("Audio component not available for resume action")
            return False
        
        try:
            # Resume current audio playback
            await audio_component.resume_audio()
            logger.info("Audio playback resumed successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to resume audio playback: {e}")
            return False

    async def _stop_audio_playback_action(self, language: str) -> bool:
        """Fire-and-forget audio stop: stop all active playback through the audio port."""
        try:
            audio_component = await self._get_audio_component()
            if not audio_component:
                self.logger.warning("Audio component not available for stop operation")
                return False
            await audio_component.stop_playback()
            self.logger.info("🛑 Audio playback stopped")
            return True
        except Exception as e:
            self.logger.error(f"Audio stop action failed: {e}")
            return False
    
    # Build dependency methods (TODO #5 Phase 2)
    # Configuration metadata: No configuration needed
    # This handler delegates to Audio component for all functionality
    # No get_config_schema() method = no configuration required
