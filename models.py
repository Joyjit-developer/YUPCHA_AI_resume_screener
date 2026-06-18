# models.py
from pydantic import BaseModel
from typing import List, Optional


class JobDescription(BaseModel):
    title: str
    description: str
    required_skills: List[str]
    min_experience_years: int = 0


class CandidateResult(BaseModel):
    filename: str
    candidate_name: str
    score: int
    matched_skills: List[str]
    missing_skills: List[str]
    experience_years: Optional[str]
    education: Optional[str] = "Not mentioned"
    summary: str
    evidence_summary: Optional[str] = ""       # exact quotes from resume
    strengths: Optional[List[str]] = []        # specific strengths found
    weaknesses: Optional[List[str]] = []       # specific gaps found
    recommendation: str
    recommendation_reason: Optional[str] = ""  # why this recommendation


class ScreeningResponse(BaseModel):
    job_title: str
    total_resumes: int
    ranked_candidates: List[CandidateResult]