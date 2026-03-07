"""
BEIET — Core LLM Wrapper.

Integration with Gemini 2.5 Flash API via google-genai SDK.
Handles conversation history, search grounding, and system prompts.
"""

import logging
from google import genai
from google.genai import types

from bot.config import config

logger = logging.getLogger("beiet.llm")


def get_client() -> genai.Client | None:
    if not config.gemini_api_key:
        return None
    return genai.Client(api_key=config.gemini_api_key)


async def generate_summary(existing_summary: str, new_conversation: str) -> str:
    """
    Summarize a conversation excerpt to fit into persistent memory chunks.
    """
    client = get_client()
    if not client:
        return "<Mock Summary: Missing API Key>"
        
    logger.info("Generating conversation summary using LLM...")
    
    prompt = f"""Resuma de manera concisa la siguiente conversación entre el Estudiante y el Tutor.
Mantenga los puntos clave de aprendizaje, las dudas del estudiante y el progreso.
Resumen Anterior:
{existing_summary}

Nueva Conversación a integrar:
{new_conversation}
"""
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )
        return response.text
    except Exception as e:
        logger.error(f"Error generating summary: {e}")
        return existing_summary


async def generate_response(
    system_prompt: str, 
    context: list, 
    user_message: str,
    rag_context: str = "",
    use_grounding: bool = True
) -> str:
    """
    Generate a response from the LLM based on conversation history, RAG, and system prompt.
    """
    client = get_client()
    if not client:
        return "⚠️ Configura GEMINI_API_KEY en el archivo `.env` para usar las funciones del tutor."
        
    # Append RAG to system prompt to enforce grounding
    full_system_instruction = system_prompt
    if rag_context:
        full_system_instruction += f"\n\nCONTEXTO DE REFERENCIA OBLIGATORIO (RAG):\n{rag_context}"
        
    # Build contents array from DB messages
    # context is a list of dicts: [{"role": "user", "content": "..."}]
    contents = []
    
    # Track the last role to prevent consecutive roles (Gemini requires alternation)
    last_role = None
    
    for msg in context:
        # Map 'assistant' and 'system' from DB to 'model' for Gemini
        role = "user" if msg.get("role") == "user" else "model"
        
        content_text = msg.get("content") or ""
        
        if last_role == role:
            # If consecutive roles, append to the last message instead
            contents[-1].parts[0].text += f"\n\n{content_text}"
        else:
            contents.append(
                types.Content(
                    role=role,
                    parts=[types.Part.from_text(text=content_text)]
                )
            )
            last_role = role
            
    # Add the current user message
    if last_role == "user":
        # If the last history message was user (unlikely unless bot failed previously), append
        contents[-1].parts[0].text += f"\n\n{user_message}"
    else:
        contents.append(
            types.Content(
                role="user",
                parts=[types.Part.from_text(text=user_message)]
            )
        )
    
    # Configure tools for Google Search (Search Grounding)
    tools = [{"google_search": {}}] if use_grounding else None
    
    gen_config = types.GenerateContentConfig(
        system_instruction=full_system_instruction,
        tools=tools,
        max_output_tokens=1024,  # Keep responses concise
        temperature=0.7  # Playful, engaging, but mathematically precise
    )
    
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=contents,
            config=gen_config
        )
        
        reply_text = response.text
        
        # Format grounding citations if they exist
        if hasattr(response, "candidates") and response.candidates:
            candidate = response.candidates[0]
            if hasattr(candidate, "grounding_metadata") and candidate.grounding_metadata:
                chunk_meta = candidate.grounding_metadata.grounding_chunks
                if chunk_meta:
                    reply_text += "\n\n🌐 **Fuentes de Búsqueda (Google):**\n"
                    for i, chunk in enumerate(chunk_meta):
                        if hasattr(chunk, "web") and chunk.web:
                            reply_text += f"- [{chunk.web.title}]({chunk.web.uri})\n"
                            
        return reply_text
        
    except Exception as e:
        logger.error(f"Error generating tutor response: {e}", exc_info=True)
        return "⚠️ Hubo un error procesando tu mensaje. Los motores matemáticos están reiniciándose..."
