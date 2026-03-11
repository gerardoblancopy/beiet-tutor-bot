"""
BEIET — Core LLM Wrapper.

Integration with Gemini 2.5 Flash API via google-genai SDK.
Handles conversation history, search grounding, and system prompts.
"""

import logging
import math
import re
from google import genai
from google.genai import types

from bot.config import config

logger = logging.getLogger("beiet.llm")


def get_client() -> genai.Client | None:
    if not config.gemini_api_key:
        return None
    return genai.Client(api_key=config.gemini_api_key)


def _extract_retry_seconds(error_text: str) -> int | None:
    """Extract retry delay from Gemini error text when available."""
    patterns = [
        r"retry in ([0-9]+(?:\.[0-9]+)?)s",
        r"'retryDelay': '([0-9]+)s'",
    ]
    for pattern in patterns:
        match = re.search(pattern, error_text, flags=re.IGNORECASE)
        if match:
            try:
                return max(1, math.ceil(float(match.group(1))))
            except (TypeError, ValueError):
                return None
    return None


def _is_quota_error(exc: Exception) -> bool:
    """Best-effort detection for Gemini quota/rate-limit errors."""
    status_code = getattr(exc, "status_code", None)
    text = str(exc).lower()
    return (
        status_code == 429
        or "resource_exhausted" in text
        or "quota exceeded" in text
        or "too many requests" in text
    )


def _user_requested_sources(user_message: str) -> bool:
    """Return True when the user explicitly asks for sources/references/links."""
    text = (user_message or "").strip().lower()
    if not text:
        return False

    # Explicit opt-out wins.
    negative_markers = [
        "sin fuentes",
        "sin referencias",
        "no muestres fuentes",
        "no incluyas fuentes",
        "no incluyas referencias",
        "sin links",
        "sin enlaces",
    ]
    if any(marker in text for marker in negative_markers):
        return False

    source_patterns = [
        r"\bfuentes?\b",
        r"\breferencias?\b",
        r"\bcitas?\b",
        r"\bbibliograf[ií]a\b",
        r"\benlaces?\b",
        r"\blinks?\b",
        r"\bsources?\b",
        r"\breferences?\b",
        r"\bcitations?\b",
        r"de d[oó]nde (sale|proviene|lo sacaste)",
        r"m[uú]estr(a|ame).*(fuentes|referencias|enlaces|links)",
        r"incluy(e|e\s+al\s+final).*(fuentes|referencias|enlaces|links)",
    ]
    return any(re.search(pattern, text) for pattern in source_patterns)


def _rag_context_is_useful(rag_context: str) -> bool:
    """Detect if retrieved RAG context actually contains useful material."""
    text = (rag_context or "").strip().lower()
    if not text:
        return False

    empty_markers = [
        "no se encontraron fragmentos relevantes",
        "no hay documentos cargados",
        "ocurrió un error al consultar el material",
        "búsqueda rag deshabilitada",
        "busqueda rag deshabilitada",
    ]
    return not any(marker in text for marker in empty_markers)


def _user_requested_web_search(user_message: str) -> bool:
    """Return True when the user explicitly asks to search the web."""
    text = (user_message or "").strip().lower()
    if not text:
        return False

    web_patterns = [
        r"busca(r)? en google",
        r"buscar en (la )?web",
        r"en internet",
        r"seg[uú]n (google|internet|la web)",
        r"noticias (de|sobre)",
        r"lo m[aá]s reciente",
        r"informaci[oó]n actualizada",
        r"actualizado (hoy|al d[ií]a)",
    ]
    return any(re.search(pattern, text) for pattern in web_patterns)


async def generate_summary(existing_summary: str, new_conversation: str) -> str | None:
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
        if _is_quota_error(e):
            logger.warning(f"Summary generation skipped due Gemini quota/rate limit: {e}")
        else:
            logger.error(f"Error generating summary: {e}")
        return None


async def generate_response(
    system_prompt: str, 
    context: list, 
    user_message: str,
    rag_context: str = "",
    use_grounding: bool = True,
    media_data: bytes | None = None,
    mime_type: str | None = None
) -> dict:
    """
    Generate a response from the LLM based on conversation history, RAG, and system prompt.
    Supports multimodal input (images and voice).
    """
    client = get_client()
    if not client:
        return {
            "text": "⚠️ Configura GEMINI_API_KEY en `.env` (o `bot.env`) para usar las funciones del tutor.",
            "input_tokens": 0,
            "output_tokens": 0,
            "cost": 0.0,
        }
        
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
    user_parts = []
    if user_message.strip():
        user_parts.append(types.Part.from_text(text=user_message))
        
    if media_data and mime_type:
        user_parts.append(types.Part.from_bytes(data=media_data, mime_type=mime_type))
        logger.info(f"Attached media of type {mime_type} to prompt.")
        
    if not user_parts:
        user_parts.append(types.Part.from_text(text="(Mensaje vacío o Archivo estático sin texto)"))

    if last_role == "user" and contents:
        # If the last history message was user (unlikely unless bot failed previously), append
        contents[-1].parts.extend(user_parts)
    else:
        contents.append(
            types.Content(
                role="user",
                parts=user_parts
            )
        )
    
    # Prioritize RAG. Use Google Search only as fallback or when explicitly requested.
    has_useful_rag = _rag_context_is_useful(rag_context)
    allow_google_search = use_grounding and (
        not has_useful_rag or _user_requested_web_search(user_message)
    )
    tools = [{"google_search": {}}] if allow_google_search else None
    
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
        
        # Token and cost tracking
        input_toks = 0
        output_toks = 0
        est_cost = 0.0
        
        if hasattr(response, "usage_metadata") and response.usage_metadata:
            input_toks = response.usage_metadata.prompt_token_count or 0
            output_toks = response.usage_metadata.candidates_token_count or 0
            # Rough pricing estimate for 2.5 flash: $0.075 / 1M input, $0.30 / 1M output
            est_cost = (input_toks / 1_000_000) * 0.075 + (output_toks / 1_000_000) * 0.30
        
        # Include grounding citations only when the user asks for them.
        if _user_requested_sources(user_message) and hasattr(response, "candidates") and response.candidates:
            candidate = response.candidates[0]
            if hasattr(candidate, "grounding_metadata") and candidate.grounding_metadata:
                chunk_meta = candidate.grounding_metadata.grounding_chunks
                if chunk_meta:
                    source_lines = []
                    for i, chunk in enumerate(chunk_meta):
                        if hasattr(chunk, "web") and chunk.web:
                            source_lines.append(f"- [{chunk.web.title}]({chunk.web.uri})")
                    if source_lines:
                        reply_text += "\n\n🌐 **Fuentes de Búsqueda (Google):**\n"
                        reply_text += "\n".join(source_lines)
                            
        return {
            "text": reply_text,
            "input_tokens": input_toks,
            "output_tokens": output_toks,
            "cost": est_cost
        }
        
    except Exception as e:
        logger.error(f"Error generating tutor response: {e}", exc_info=True)
        if _is_quota_error(e):
            retry_seconds = _extract_retry_seconds(str(e))
            wait_msg = f"Reintenta en ~{retry_seconds}s." if retry_seconds else "Reintenta en unos segundos."
            return {
                "text": (
                    "⚠️ Límite temporal de Gemini alcanzado (429). "
                    f"{wait_msg} Si persiste, revisa cuota/facturación de la API."
                ),
                "input_tokens": 0,
                "output_tokens": 0,
                "cost": 0.0,
            }
        return {
            "text": "⚠️ Hubo un error procesando tu mensaje. Los motores matemáticos están reiniciándose...",
            "input_tokens": 0,
            "output_tokens": 0,
            "cost": 0.0
        }
