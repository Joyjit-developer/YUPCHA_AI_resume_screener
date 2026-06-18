# main.py
# ─────────────────────────────────────────────
# FastAPI backend with PostgreSQL integration.
# All routes for uploading, screening, comparing.
# ─────────────────────────────────────────────

import os
import shutil
from fastapi import FastAPI, File, UploadFile, HTTPException, Form, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime

from parser import extract_text
from screener import screen_resume, rank_candidates
from models import JobDescription, CandidateResult, ScreeningResponse
from database import create_tables, get_db, JobDB, ResumeDB

# ── Create FastAPI app ─────────────────────────
app = FastAPI(
    title="AI Resume Screener",
    description="Upload resumes and get AI-powered candidate rankings stored in PostgreSQL",
    version="2.0.0"
)

# ── CORS — allows frontend to talk to backend ──
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)

# ── Create uploads folder ──────────────────────
os.makedirs("uploads", exist_ok=True)

# ── Create DB tables on startup ────────────────
@app.on_event("startup")
def startup():
    create_tables()
    print("✅ Database tables created/verified")


# ─────────────────────────────────────────────
# ROUTE 1: Health check
# ─────────────────────────────────────────────

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

@app.get("/", response_class=HTMLResponse)
async def home():
   file_path = os.path.join(BASE_DIR, "index.html")
   with open(file_path, "r", encoding="utf-8") as f:
     return f.read()
   
       

# ─────────────────────────────────────────────
# ROUTE 2: Screen resumes (main endpoint)
# POST /screen
# Accepts: multiple resume files + job details
# Saves: job + resumes + AI results to PostgreSQL
# Returns: ranked candidates
# ─────────────────────────────────────────────
@app.post("/screen", response_model=ScreeningResponse)
def screen_resumes(
    files: List[UploadFile] = File(...),
    job_title: str = Form(...),
    job_description: str = Form(...),
    required_skills: str = Form(...),
    min_experience_years: int = Form(0),
    db: Session = Depends(get_db)
):
    # ── Validate file types ────────────────────
    for file in files:
        ext = os.path.splitext(file.filename)[1].lower()
        if ext not in [".pdf", ".docx"]:
            raise HTTPException(
                status_code=400,
                detail=f"'{file.filename}' is not supported. Only PDF and DOCX allowed."
            )

    # ── Parse skills string to list ────────────
    # "Python, FastAPI, SQL" → ["Python", "FastAPI", "SQL"]
    skills_list = [s.strip() for s in required_skills.split(",") if s.strip()]

    # ── Save job to database ───────────────────
    job_record = JobDB(
        title=job_title,
        description=job_description,
        required_skills=skills_list,
        min_experience_years=min_experience_years
    )
    db.add(job_record)
    db.commit()
    db.refresh(job_record)          # get the auto-generated job ID

    # ── Build job object for AI ────────────────
    job = JobDescription(
        title=job_title,
        description=job_description,
        required_skills=skills_list,
        min_experience_years=min_experience_years
    )

    results = []

    for file in files:
        # Step 1: Save file temporarily
        file_path = f"uploads/{file.filename}"
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Step 2: Extract text from resume
        try:
            resume_text = extract_text(file_path)
            print(f"✅ Parsed {file.filename} — {len(resume_text)} characters extracted")
            if not resume_text.strip():
                print(f"❌ Empty text from {file.filename}")
                os.remove(file_path)
                continue
        except Exception as e:
            print(f"❌ PARSE ERROR for {file.filename}: {type(e).__name__}: {e}")
            if os.path.exists(file_path):
                os.remove(file_path)
            continue

        # Step 3: Send to AI for scoring
        try:
            result = screen_resume(resume_text, job, file.filename)
            print(f"✅ AI scored {file.filename} — Score: {result.score}")
        except Exception as e:
            print(f"❌ AI ERROR for {file.filename}: {type(e).__name__}: {e}")
            if os.path.exists(file_path):
                os.remove(file_path)
            continue

        # Step 4: Save result to PostgreSQL
        resume_record = ResumeDB(
            job_id=job_record.id,
            filename=file.filename,
            candidate_name=result.candidate_name,
            resume_text=resume_text,
            score=result.score,
            matched_skills=result.matched_skills,
            missing_skills=result.missing_skills,
            experience_years=result.experience_years,
            summary=result.summary,
            recommendation=result.recommendation
        )
        db.add(resume_record)
        db.commit()

        results.append(result)

        # Step 5: Delete temp file
        os.remove(file_path)

    if not results:
        raise HTTPException(status_code=422, detail="No resumes could be processed.")

    # ── Rank by score and return ───────────────
    ranked = rank_candidates(results)

    return ScreeningResponse(
        job_title=job_title,
        total_resumes=len(ranked),
        ranked_candidates=ranked
    )


# ─────────────────────────────────────────────
# ROUTE 3: Get all past jobs
# GET /jobs
# Returns list of all jobs ever screened
# ─────────────────────────────────────────────
@app.get("/jobs")
def get_all_jobs(db: Session = Depends(get_db)):
    jobs = db.query(JobDB).order_by(JobDB.created_at.desc()).all()
    return [
        {
            "id": j.id,
            "title": j.title,
            "required_skills": j.required_skills,
            "min_experience_years": j.min_experience_years,
            "created_at": j.created_at
        }
        for j in jobs
    ]


# ─────────────────────────────────────────────
# ROUTE 4: Compare all resumes for a job
# GET /jobs/{job_id}/resumes
# Returns all candidates for one job, ranked
# Useful for comparing resumes side by side
# ─────────────────────────────────────────────
@app.get("/jobs/{job_id}/resumes")
def get_resumes_for_job(job_id: int, db: Session = Depends(get_db)):
    # Check job exists
    job = db.query(JobDB).filter(JobDB.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail=f"Job ID {job_id} not found.")

    # Get all resumes for this job, sorted by score
    resumes = (
        db.query(ResumeDB)
        .filter(ResumeDB.job_id == job_id)
        .order_by(ResumeDB.score.desc())
        .all()
    )

    return {
        "job_id": job_id,
        "job_title": job.title,
        "required_skills": job.required_skills,
        "total_candidates": len(resumes),
        "candidates": [
            {
                "id": r.id,
                "filename": r.filename,
                "candidate_name": r.candidate_name,
                "score": r.score,
                "matched_skills": r.matched_skills,
                "missing_skills": r.missing_skills,
                "experience_years": r.experience_years,
                "summary": r.summary,
                "recommendation": r.recommendation,
                "uploaded_at": r.uploaded_at
            }
            for r in resumes
        ]
    }


# ─────────────────────────────────────────────
# ROUTE 5: Delete a job and its resumes
# DELETE /jobs/{job_id}
# ─────────────────────────────────────────────
@app.delete("/jobs/{job_id}")
def delete_job(job_id: int, db: Session = Depends(get_db)):
    job = db.query(JobDB).filter(JobDB.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail=f"Job ID {job_id} not found.")

    db.query(ResumeDB).filter(ResumeDB.job_id == job_id).delete()
    db.delete(job)
    db.commit()

    return {"message": f"Job {job_id} and all its resumes deleted successfully."}