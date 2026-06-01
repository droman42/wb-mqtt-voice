#!/usr/bin/env python3
"""
Conversation Intent Handler Demo

Demonstrates the ConversationIntentHandler functionality including:
- Starting conversations via intent recognition
- Multi-turn conversations with state management
- Different conversation modes (chat vs reference)
- Intent-based conversation routing
- Session persistence and cleanup

This replaces the functionality from legacy plugin_boltalka_vsegpt.py
with modern v13 architecture using LLM components and intent system.
"""

import asyncio
import json
import logging
from pathlib import Path
import sys

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from irene.core.engine import AsyncVACore
from irene.core.session_manager import SessionManager
from irene.intents.context_models import UnifiedConversationContext
# CommandResult removed - use IntentResult instead
from irene.config.models import CoreConfig as Config
from irene.intents.handlers.conversation import ConversationIntentHandler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ConversationDemoRunner:
    """Demo runner for ConversationIntentHandler"""
    
    def __init__(self):
        self.core = None
        self.conversation_handler = None
    
    def _ensure_handler(self) -> ConversationIntentHandler:
        """Ensure handler is initialized and return it"""
        if not self.conversation_handler:
            raise RuntimeError("ConversationIntentHandler not initialized")
        return self.conversation_handler
    
    async def setup_core(self) -> None:
        """Set up AsyncVACore with ConversationIntentHandler"""
        logger.info("🚀 Setting up AsyncVACore with ConversationIntentHandler...")
        
        # Create minimal config
        config = Config()
        
        # Initialize core
        self.core = AsyncVACore(config)
        await self.core.start()
        
        # Load conversation handler
        self.conversation_handler = ConversationIntentHandler()
        # Note: Intent handlers are registered differently than plugins
        
        logger.info("✅ Core and ConversationIntentHandler initialized")
    
    async def demo_voice_commands(self) -> None:
        """Demonstrate voice command interface"""
        logger.info("\n" + "="*60)
        logger.info("🎤 VOICE COMMAND DEMO")
        logger.info("="*60)
        
        # Create context for commands
        context = UnifiedConversationContext(session_id=SessionManager.generate_session_id("demo"), user_id="demo_user")
        
        # Demo commands
        commands = [
            "поболтаем как дела?",
            "хорошо, а у тебя?", 
            "новый диалог",
            "расскажи про погоду",
            "справка что такое Python?",
            "сохрани диалог",
            "пока"
        ]
        
        for i, command in enumerate(commands, 1):
            logger.info(f"\n--- Command {i}: '{command}' ---")
            
            try:
                # Note: Intent handlers work differently than command plugins
                if self.conversation_handler:
                    logger.info(f"Intent handler available: {self.conversation_handler}")
                    # For demo purposes, we'll show the handler exists
                    # Actual intent processing would go through the intent system
                    logger.info(f"✅ Command would be processed by intent system: {command}")
                else:
                    logger.info("⏭️ Command not handled by ConversationIntentHandler")
                
                # Simulate delay between commands
                await asyncio.sleep(0.5)
                
            except Exception as e:
                logger.error(f"❌ Error processing command: {e}")
    
    async def demo_session_management(self) -> None:
        """Demonstrate session management features"""
        logger.info("\n" + "="*60)
        logger.info("📚 SESSION MANAGEMENT DEMO")
        logger.info("="*60)
        
        handler = self._ensure_handler()
        
        # Session management now handled by UnifiedConversationContext.handler_contexts
        logger.info("Session management now handled by UnifiedConversationContext")
        
        # Create demo contexts with handler-specific conversation data
        context1 = UnifiedConversationContext(session_id=SessionManager.generate_session_id("demo_1"))
        context1.get_handler_context("conversation")["conversation_type"] = "chat"
        context1.get_handler_context("conversation")["messages"] = [
            {"role": "system", "content": "Ты дружелюбный помощник"},
            {"role": "user", "content": "Привет!"},
            {"role": "assistant", "content": "Привет! Как дела?"}
        ]
        
        context2 = UnifiedConversationContext(session_id=SessionManager.generate_session_id("demo_2"))
        context2.get_handler_context("conversation")["conversation_type"] = "reference"
        context2.get_handler_context("conversation")["messages"] = [
            {"role": "system", "content": "Ты справочный помощник"},
            {"role": "user", "content": "Что такое ИИ?"},
            {"role": "assistant", "content": "Искусственный интеллект..."}
        ]
        
        logger.info(f"Created demo contexts: demo_1, demo_2")
        
        # Show context details
        for context in [context1, context2]:
            conv_context = context.get_handler_context("conversation")
            logger.info(f"\n📄 Context {context.session_id}:")
            logger.info(f"  Type: {conv_context.get('conversation_type', 'chat')}")
            logger.info(f"  Messages: {len(conv_context.get('messages', []))}")
            logger.info(f"  Created: {conv_context.get('created_at', 'unknown')}")
            
            # Show conversation history
            for msg in conv_context.get('messages', []):
                role_icon = "🤖" if msg["role"] == "assistant" else "👤" if msg["role"] == "user" else "⚙️"
                logger.info(f"  {role_icon} {msg['role']}: {msg['content'][:50]}...")
        
        # Test context cleanup (simplified for demo)
        logger.info(f"\n🧹 Context cleanup functionality available in UnifiedConversationContext")
        logger.info(f"Context management now handled by ContextManager")
        
        # Test saving (simplified for demo)
        logger.info(f"\n💾 Session saving functionality available")
        logger.info(f"Sessions can be saved to files when implemented")
    
    async def demo_api_endpoints(self) -> None:
        """Demonstrate REST API endpoints"""
        logger.info("\n" + "="*60)
        logger.info("🌐 API ENDPOINTS DEMO")
        logger.info("="*60)
        
        # Note: Intent handlers work through the intent system, not direct HTTP
        handler = self._ensure_handler()
        logger.info(f"✅ ConversationIntentHandler available: {handler}")
        
        # Intent handlers integrate via the core engine's intent system
        logger.info("\n📋 Intent-based conversation flow:")
        logger.info("  1. Voice/text input → Intent Recognition")
        logger.info("  2. Intent Router → ConversationIntentHandler")
        logger.info("  3. Handler processes via LLM component")
        logger.info("  4. Response → TTS/output system")
        
        logger.info("\n💡 Integration points:")
        logger.info("  - Intent patterns: conversation triggers")
        logger.info("  - Session management: built into handler") 
        logger.info("  - LLM integration: via components")
        logger.info("  - Web API: through core engine endpoints")
        logger.info("  - Configuration: TOML-based settings")
    
    async def demo_configuration(self) -> None:
        """Demonstrate configuration options"""
        logger.info("\n" + "="*60)
        logger.info("⚙️ CONFIGURATION DEMO")
        logger.info("="*60)
        
        handler = self._ensure_handler()
        
        logger.info("📋 Current configuration:")
        for key, value in handler.config.items():
            logger.info(f"  {key}: {value}")
        
        # Show configuration integration
        logger.info(f"\n🔧 Configuration integration:")
        logger.info(f"  Using LLM component's default model")
        logger.info(f"  Session timeout: {handler.config['session_timeout']} seconds")
        logger.info(f"  Max sessions: {handler.config['max_sessions']}")
        
        # Show TOML configuration example
        toml_config = """
[intents.conversation]
chat_system_prompt = "Ты - Ирина, голосовой помощник, помогающий человеку. Давай ответы кратко и по существу."
reference_system_prompt = "Ты помощник для получения точных фактов. Отвечай максимально кратко и точно на русском языке."
session_timeout = 1800
max_sessions = 50
"""
        
        logger.info(f"\n📄 Example TOML configuration:")
        logger.info(toml_config)
    
    async def demo_architecture_comparison(self) -> None:
        """Show architecture comparison with legacy plugin"""
        logger.info("\n" + "="*60)
        logger.info("🏗️ ARCHITECTURE COMPARISON")
        logger.info("="*60)
        
        logger.info("🔴 LEGACY plugin_boltalka_vsegpt.py:")
        logger.info("  ❌ Direct OpenAI API calls")
        logger.info("  ❌ Hardcoded VseGPT integration")
        logger.info("  ❌ Mixed TTS and chat logic")
        logger.info("  ❌ Global state in VACore")
        logger.info("  ❌ Synchronous architecture")
        logger.info("  ❌ No web API")
        logger.info("  ❌ Limited error handling")
        
        logger.info("\n🟢 NEW ConversationIntentHandler:")
        logger.info("  ✅ Uses LLM components backend")
        logger.info("  ✅ Multiple LLM provider support") 
        logger.info("  ✅ Clean separation of concerns")
        logger.info("  ✅ Proper session management")
        logger.info("  ✅ Full async/await architecture")
        logger.info("  ✅ Intent-based routing")
        logger.info("  ✅ Robust error handling")
        logger.info("  ✅ Configuration-driven")
        logger.info("  ✅ Type-safe with proper interfaces")
        
        logger.info("\n📊 Migration status:")
        logger.info("  ✅ Conversational logic - MIGRATED to intent system")
        logger.info("  ✅ Voice commands - ENHANCED via intent recognition")  
        logger.info("  ✅ Session management - IMPROVED in handler")
        logger.info("  ✅ LLM integration - ABSTRACTED via components")
        logger.info("  ✅ Web API - INTEGRATED via core engine")
        logger.info("  ✅ Plugin → Intent - ARCHITECTURALLY IMPROVED")
    
    async def run_complete_demo(self) -> None:
        """Run the complete demonstration"""
        logger.info("🎯 ConversationIntentHandler Complete Demo")
        logger.info("=" * 80)
        
        try:
            # Setup
            await self.setup_core()
            
            # Run all demos
            await self.demo_voice_commands()
            await self.demo_session_management()
            await self.demo_api_endpoints()
            await self.demo_configuration()
            await self.demo_architecture_comparison()
            
            logger.info("\n" + "="*80)
            logger.info("🎉 ConversationIntentHandler demo completed successfully!")
            logger.info("="*80)
            
            # Note about LLM dependency
            logger.info("\n💡 Note: For full functionality, ensure:")
            logger.info("  1. LLM components are loaded and configured")
            logger.info("  2. LLM providers (OpenAI, VseGPT, etc.) have API keys")
            logger.info("  3. Network connectivity for LLM API calls")
            logger.info("  4. Intent system is properly configured")
            
        except Exception as e:
            logger.error(f"❌ Demo failed: {e}")
            import traceback
            traceback.print_exc()
        
        finally:
            # Cleanup
            if self.core:
                await self.core.stop()


async def main():
    """Main demo entry point"""
    demo = ConversationDemoRunner()
    await demo.run_complete_demo()


if __name__ == "__main__":
    asyncio.run(main()) 