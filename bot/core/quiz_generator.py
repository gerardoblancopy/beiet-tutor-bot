import os
from io import BytesIO
import json
import logging
from typing import List
from pydantic import BaseModel, Field
from google import genai
from google.genai import types
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.colors import HexColor

from bot.config import config
from bot.core.rag import rag_service

logger = logging.getLogger("beiet.quiz")

# --- Pydantic Schemas for Structured Output ---
class Question(BaseModel):
    statement: str = Field(description="The question statement or mathematical problem")
    option_a: str = Field(description="Multiple choice option A")
    option_b: str = Field(description="Multiple choice option B")
    option_c: str = Field(description="Multiple choice option C")
    option_d: str = Field(description="Multiple choice option D")
    correct_letter: str = Field(description="The letter of the correct option (A, B, C, or D)")
    feedback: str = Field(description="Pedagogical feedback explaining why this is the correct answer and covering common pitfalls")
    lo_code: str | None = Field(description="The Learning Outcome (RA) code this targets, e.g. RA1 or LO1", default=None)

class Quiz(BaseModel):
    title: str = Field(description="Title of the quiz or study guide")
    questions: list[Question] = Field(description="List of questions")


async def generate_quiz_json(subject: str, topic: str, num_questions: int = 3) -> Quiz | None:
    """Uses Gemini to generate a structured JSON quiz based on RAG context."""
    if not config.gemini_api_key:
        logger.error("Missing Gemini API Key for quiz generation.")
        return None

    client = genai.Client(api_key=config.gemini_api_key)
    subject_name = config.SUBJECTS[subject].name if subject in config.SUBJECTS else subject
    
    # Get RAG context
    rag_context = rag_service.retrieve_context(subject, topic, n_results=5)
    
    prompt = f"""
    Eres el Profesor BEIET, experto en la asignatura {subject_name}.
    Crea un cuestionario de opción múltiple (Multiple Choice) sobre el tema "{topic}".
    El cuestionario DEBE tener exactamente {num_questions} preguntas.
    
    Usa el siguiente material de referencia (RAG) para basar tus preguntas. Si no hay suficiente contexto, usa tu conocimiento general del tema de ingeniería de manera rigurosa.
    MATERIAL RAG:
    {rag_context}
    
    Asegúrate de que la retroalimentación (feedback) sea al estilo socrático: explica el por qué pero también invita a reflexionar.
    """
    
    gen_config = types.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema=Quiz,
        temperature=0.7
    )
    
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=gen_config
        )
        return Quiz.model_validate_json(response.text)
    except Exception as e:
        logger.error(f"Error generating quiz: {e}")
        return None


def create_pdf_guide(quiz_data: Quiz) -> BytesIO:
    """Generates a professional PDF study guide using ReportLab."""
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, 
        pagesize=letter,
        rightMargin=50, leftMargin=50,
        topMargin=50, bottomMargin=50
    )
    
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'MainTitle', 
        parent=styles['Heading1'],
        fontSize=20,
        spaceAfter=20,
        textColor=HexColor("#1e3a8a")  # Dark Blue
    )
    question_style = ParagraphStyle(
        'Question', 
        parent=styles['BodyText'],
        fontSize=12,
        spaceBefore=15,
        spaceAfter=10,
        fontName="Helvetica-Bold"
    )
    option_style = ParagraphStyle(
        'Option', 
        parent=styles['BodyText'],
        fontSize=11,
        leftIndent=20,
        spaceAfter=5
    )
    feedback_style = ParagraphStyle(
        'Feedback', 
        parent=styles['BodyText'],
        fontSize=10,
        leftIndent=20,
        spaceBefore=10,
        textColor=HexColor("#065f46"), # Dark Green
        fontName="Helvetica-Oblique"
    )
    
    story = []
    
    # Header
    story.append(Paragraph("BEIET - Tutor Asistente Inteligente", styles['Normal']))
    story.append(Spacer(1, 10))
    story.append(Paragraph(f"Guía de Ejercicios: {quiz_data.title}", title_style))
    story.append(Paragraph("Resuelve los siguientes ejercicios. Al final de cada pregunta encontrarás la pauta y retroalimentación interactiva generada por inteligencia artificial.", styles['Normal']))
    story.append(Spacer(1, 20))
    
    # Body (Questions)
    for i, q in enumerate(quiz_data.questions):
        # Question text
        story.append(Paragraph(f"{i+1}. {q.statement}", question_style))
        
        # Options
        story.append(Paragraph(f"<b>A)</b> {q.option_a}", option_style))
        story.append(Paragraph(f"<b>B)</b> {q.option_b}", option_style))
        story.append(Paragraph(f"<b>C)</b> {q.option_c}", option_style))
        story.append(Paragraph(f"<b>D)</b> {q.option_d}", option_style))
        
        # Spacer before feedback
        story.append(Spacer(1, 15))
        
        # Correct Answer and Feedback (Simulating an upside-down key or inline guide)
        story.append(Paragraph(f"<b>Respuesta Correcta: {q.correct_letter}</b>", feedback_style))
        story.append(Paragraph(f"<i>Retroalimentación del Tutor BEIET:</i> {q.feedback}", feedback_style))
        story.append(Spacer(1, 20))
        
    doc.build(story)
    buffer.seek(0)
    return buffer
