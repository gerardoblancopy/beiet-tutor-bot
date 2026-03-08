"""
BEIET — Database Models.

SQLAlchemy models for student management, conversation memory,
learning outcome tracking, and quiz results.
"""

from datetime import datetime, timezone

from sqlalchemy import (
    Column, Integer, String, Float, Text, DateTime, Boolean, ForeignKey,
    UniqueConstraint, Index, create_engine
)
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    """Base class for all models."""
    pass


class Student(Base):
    """Registered student with Discord and institutional identity."""
    __tablename__ = "students"

    id = Column(Integer, primary_key=True, autoincrement=True)
    discord_id = Column(String(20), unique=True, nullable=False, index=True)
    rut = Column(String(12), nullable=True)  # Chilean ID
    name = Column(String(100), nullable=False)
    email = Column(String(200), nullable=True)
    subject = Column(String(50), nullable=False, default="optimizacion")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    is_active = Column(Boolean, default=True)

    # Relationships
    messages = relationship("ConversationMessage", back_populates="student", cascade="all, delete-orphan")
    lo_progress = relationship("LOProgress", back_populates="student", cascade="all, delete-orphan")
    quiz_results = relationship("QuizResult", back_populates="student", cascade="all, delete-orphan")
    summaries = relationship("ConversationSummary", back_populates="student", cascade="all, delete-orphan")
    meetings = relationship("ScheduledMeeting", back_populates="student", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Student {self.name} ({self.discord_id})>"


class ConversationMessage(Base):
    """Individual message in a student-bot conversation (persistent memory)."""
    __tablename__ = "conversation_messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False, index=True)
    session_id = Column(String(36), nullable=False, index=True)  # UUID per session
    role = Column(String(20), nullable=False)  # "user", "assistant", "system"
    content = Column(Text, nullable=False)
    subject = Column(String(50), nullable=False)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    has_attachment = Column(Boolean, default=False)
    attachment_type = Column(String(20), nullable=True)  # "image", "voice", "file"
    
    # Token Tracking
    input_tokens = Column(Integer, default=0)
    output_tokens = Column(Integer, default=0)
    cost = Column(Float, default=0.0)

    # Relationships
    student = relationship("Student", back_populates="messages")

    __table_args__ = (
        Index("ix_messages_student_session", "student_id", "session_id"),
    )


class ConversationSummary(Base):
    """Compressed summary of older conversation messages."""
    __tablename__ = "conversation_summaries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False, index=True)
    subject = Column(String(50), nullable=False)
    summary_text = Column(Text, nullable=False)
    message_count = Column(Integer, default=0)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    student = relationship("Student", back_populates="summaries")


class LOProgress(Base):
    """Learning Outcome progress tracking per student per subject."""
    __tablename__ = "lo_progress"

    id = Column(Integer, primary_key=True, autoincrement=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    subject = Column(String(50), nullable=False)
    lo_code = Column(String(10), nullable=False)  # e.g., "RA1", "RB2"
    score = Column(Float, default=0.0)  # 0.0 to 1.0
    attempts = Column(Integer, default=0)
    correct_count = Column(Integer, default=0)
    last_assessed = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)  # LLM-generated assessment notes

    # Relationships
    student = relationship("Student", back_populates="lo_progress")

    __table_args__ = (
        UniqueConstraint("student_id", "subject", "lo_code", name="uq_student_lo"),
        Index("ix_lo_student_subject", "student_id", "subject"),
    )


class QuizResult(Base):
    """Quiz attempt results with per-question breakdown."""
    __tablename__ = "quiz_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    subject = Column(String(50), nullable=False)
    unit = Column(String(50), nullable=True)
    lo_codes = Column(String(100), nullable=True)  # Comma-separated LOs tested
    score = Column(Float, nullable=False)  # 0.0 to 1.0
    total_questions = Column(Integer, nullable=False)
    correct_answers = Column(Integer, nullable=False)
    feedback = Column(Text, nullable=True)  # LLM-generated feedback
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    student = relationship("Student", back_populates="quiz_results")


class ScheduledMeeting(Base):
    """Scheduled meetings between students and professor."""
    __tablename__ = "scheduled_meetings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    subject = Column(String(50), nullable=False)
    scheduled_at = Column(DateTime, nullable=False)
    duration_minutes = Column(Integer, default=30)
    google_event_id = Column(String(200), nullable=True)
    meet_link = Column(String(300), nullable=True)
    topic = Column(Text, nullable=True)
    status = Column(String(20), default="confirmed")  # confirmed, cancelled, completed
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    student = relationship("Student", back_populates="meetings")
