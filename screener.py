# screener.py
import os
import json
from groq import Groq
from dotenv import load_dotenv
from models import JobDescription, CandidateResult

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))


def screen_resume(resume_text: str, job: JobDescription, filename: str) -> CandidateResult:
    """
    Sends resume + JD to Groq AI.
    Returns structured result with:
    - score based on real evidence from resume
    - matched/missing skills with proof
    - evidence-based recommendation with reasons
    """

    prompt = f"""
You are a strict and experienced technical recruiter with 10 years of hiring experience.
Your job is to evaluate resumes ONLY based on evidence found in the resume text.
Do NOT assume or guess skills that are not explicitly mentioned.

═══════════════════════════════════════
JOB TITLE: {job.title}

JOB DESCRIPTION:
{job.description}

REQUIRED SKILLS: {", ".join(job.required_skills)}
MINIMUM EXPERIENCE REQUIRED: {job.min_experience_years} years
═══════════════════════════════════════

RESUME CONTENT:
{resume_text}
═══════════════════════════════════════

INSTRUCTIONS:
1. Read the resume carefully word by word
2. For each required skill, check if it is EXPLICITLY mentioned
3. Calculate score based on:
   - Skills match     : 50 points total (divide equally per skill)
   - Experience match : 25 points (full if meets min, partial if close)
   - Education        : 15 points
   - Overall quality  : 10 points
4. Recommendation rules (be strict):
   - "Strong Hire" : score >= 75 AND meets experience requirement
   - "Maybe"       : score 50-74 OR missing 1-2 skills but strong otherwise
   - "Reject"      : score < 50 OR missing more than half required skills
5. evidence_summary must quote EXACT phrases from the resume as proof

Return ONLY a valid JSON object. No markdown, no explanation, no extra text.

{{
    "candidate_name": "Full name from resume or Unknown",
    "score": <integer 0-100 calculated strictly>,
    "matched_skills": ["only skills explicitly found in resume"],
    "missing_skills": ["required skills NOT found anywhere in resume"],
    "experience_years": "exact text found e.g. 3 years or Not mentioned",
    "education": "degree and institution from resume or Not mentioned",
    "summary": "2-3 sentence professional summary based only on resume facts",
    "evidence_summary": "Quote 2-3 specific lines from resume that support your score. e.g. Candidate states X, Y project used Z",
    "strengths": ["specific strength 1", "specific strength 2"],
    "weaknesses": ["specific gap 1", "specific gap 2"],
    "recommendation": "Strong Hire or Maybe or Reject",
    "recommendation_reason": "1-2 sentence explanation of why this recommendation, citing specific evidence"
}}
"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a strict technical recruiter. "
                    "Evaluate resumes only on explicit evidence. "
                    "Never assume skills. Always return valid JSON only."
                )
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0.1,        # very low = consistent, factual, strict
        max_tokens=1200
    )

    raw = response.choices[0].message.content.strip()

    # ── Clean markdown fences if AI adds them ──
    if "```" in raw:
        parts = raw.split("```")
        for part in parts:
            part = part.strip()
            if part.startswith("json"):
                part = part[4:].strip()
            if part.startswith("{"):
                raw = part
                break

    raw = raw.strip()

    # ── Parse JSON ─────────────────────────────
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        # Return safe fallback if JSON is broken
        return CandidateResult(
            filename=filename,
            candidate_name="Parse Error",
            score=0,
            matched_skills=[],
            missing_skills=job.required_skills,
            experience_years="Unknown",
            education="Unknown",
            summary="Could not parse AI response for this resume.",
            evidence_summary="No evidence extracted.",
            strengths=[],
            weaknesses=["Could not analyze resume"],
            recommendation="Reject",
            recommendation_reason="Resume could not be processed by AI."
        )

    # ── Enforce recommendation rules strictly ──
    score = int(data.get("score", 0))
    missing = data.get("missing_skills", [])
    recommendation = data.get("recommendation", "Reject")

    # Override AI recommendation if it breaks rules
    if score >= 75 and len(missing) == 0:
        recommendation = "Strong Hire"
    elif score >= 75 and len(missing) <= 1:
        recommendation = "Strong Hire"
    elif score >= 50:
        recommendation = "Maybe"
    else:
        recommendation = "Reject"

    return CandidateResult(
        filename=filename,
        candidate_name=data.get("candidate_name", "Unknown"),
        score=score,
        matched_skills=data.get("matched_skills", []),
        missing_skills=missing,
        experience_years=data.get("experience_years", "Not mentioned"),
        education=data.get("education", "Not mentioned"),
        summary=data.get("summary", ""),
        evidence_summary=data.get("evidence_summary", ""),
        strengths=data.get("strengths", []),
        weaknesses=data.get("weaknesses", []),
        recommendation=recommendation,
        recommendation_reason=data.get("recommendation_reason", "")
    )


def rank_candidates(results: list) -> list:
    """
    Ranks candidates by score (highest first).
    For equal scores, Strong Hire comes before Maybe before Reject.
    """
    recommendation_order = {"Strong Hire": 0, "Maybe": 1, "Reject": 2}

    return sorted(
        results,
        key=lambda x: (
            -x.score,                                          # higher score first
            recommendation_order.get(x.recommendation, 3)     # then by recommendation
        )
    )