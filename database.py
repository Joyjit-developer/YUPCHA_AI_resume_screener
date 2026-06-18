from sqlalchemy import (
    create_engine, Column, Integer, String,
    Text, DateTime, JSON
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

# ── Database URL from .env ─────────────────────
# Format: postgresql://username:password@localhost:5432/dbname
DATABASE_URL = os.getenv("DATABASE_URL")

# ── Create engine (connection to PostgreSQL) ───
engine = create_engine(DATABASE_URL)

# ── Session factory ────────────────────────────
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# ── Base class for all models ──────────────────
Base = declarative_base()


# ── Table 1: Jobs ──────────────────────────────
class JobDB(Base):
    """
    Stores each job description posted by recruiter.
    One job can have many resumes screened against it.
    """
    __tablename__ = "jobs"

    id                  = Column(Integer, primary_key=True, index=True)
    title               = Column(String(200), nullable=False)
    description         = Column(Text, nullable=False)
    required_skills     = Column(JSON, nullable=False)   # stored as JSON array
    min_experience_years = Column(Integer, default=0)
    created_at          = Column(DateTime, default=datetime.utcnow)


# ── Table 2: Resumes ───────────────────────────
class ResumeDB(Base):
    """
    Stores each uploaded resume and its AI screening result.
    Linked to a job via job_id so you can compare all
    resumes for the same job side by side.
    """
    __tablename__ = "resumes"

    id               = Column(Integer, primary_key=True, index=True)
    job_id           = Column(Integer, nullable=False)   # links to jobs table
    filename         = Column(String(300), nullable=False)
    candidate_name   = Column(String(200), default="Unknown")
    resume_text      = Column(Text, nullable=False)      # raw extracted text
    score            = Column(Integer, default=0)        # AI score 0-100
    matched_skills   = Column(JSON, default=[])          # ["Python", "FastAPI"]
    missing_skills   = Column(JSON, default=[])          # ["SQL", "Docker"]
    experience_years = Column(String(100), default="Not mentioned")
    summary          = Column(Text, default="")
    recommendation   = Column(String(50), default="Reject")
    uploaded_at      = Column(DateTime, default=datetime.utcnow)


# ── Create all tables ──────────────────────────
def create_tables():
    """
    Call this once on startup.
    Creates jobs and resumes tables if they don't exist.
    Safe to call multiple times — won't duplicate tables.
    """
    Base.metadata.create_all(bind=engine)


# ── Dependency for FastAPI routes ──────────────
def get_db():
    """
    Gives a database session to each API request.
    Automatically closes the session when request is done.
    Used as: db: Session = Depends(get_db)
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()