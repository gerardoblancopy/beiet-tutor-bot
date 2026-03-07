"""
BEIET — Placeholder LLM Wrapper.

Integration with Gemini 2.5 Flash API via google-genai SDK.
"""

import logging
from bot.config import config

logger = logging.getLogger("beiet.llm")

# TODO: Add actual google-genai implementation
# For Phase 1, we just stub out the functions used by memory.py

async def generate_summary(existing_summary: str, new_conversation: str) -> str:
    """
    Summarize a conversation excerpt.
    """
    if not config.gemini_api_key:
        return "<Mock Summary: Missing API Key>"
        
    logger.info("Generating conversation summary using LLM...")
    
    # Mock implementation for Phase 1
    # Real implementation comes in Phase 4
    
    return f"{existing_summary}\n[Added summary of {len(new_conversation.splitlines())} lines]"


async def generate_response(system_prompt: str, context: list[dict], user_message: str) -> str:
    """
    Generate a response from the LLM based on context.
    """
    if not config.gemini_api_key:
        return "⚠️ Configura GEMINI_API_KEY en el archivo `.env` para usar las funciones del tutor."
        
    # Mock implementation
    return "Esta es una respuesta simulada del tutor BEIET. Fase de integración LLM pendiente."
