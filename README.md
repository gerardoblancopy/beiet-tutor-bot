# BEIET — Discord Tutor Bot 🎓

Adaptive University Tutor Agent for Discord, supporting RAG knowledge bases, optimization solving, student progress tracking, and multimodal interactions.

## Features

- **Personalized Tutoring**: Adapts explanations based on student's persistent learning outcome (LO/RA) progress.
- **RAG Knowledge Base**: Answers grounded in subject-specific documents (ChromaDB).
- **Optimization Solver**: Parses text and handwritten images to solve linear/nonlinear optimization problems in Python.
- **Multimodal**: Supports voice messages and image processing via Gemini 2.5 Flash.
- **Google Calendar**: Students can check availability and book meetings with the professor directly through Discord.
- **Quiz Generation**: Auto-generates unit quizzes and exports them to PDF.

## Subjects
Initially built for:
- **Métodos de Optimización**
- **Mercados Eléctricos**

## Setup

1. Clone the repository
2. Create virtual environment: `python -m venv venv`
3. Install dependencies: `pip install -r requirements.txt`
4. Copy `.env.example` to `.env` and configure your credentials:
   - `DISCORD_TOKEN`: From Discord Developer Portal
   - `GEMINI_API_KEY`: From Google AI Studio
5. Run the bot: `python -m bot.main`

## Architecture
Built with Pycord, SQLAlchemy (SQLite async), ChromaDB, google-genai, and PuLP/Pyomo.

Designed for self-hosting on Hugging Face Spaces (Docker).
