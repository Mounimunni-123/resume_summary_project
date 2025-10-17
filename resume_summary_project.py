from fastapi import FastAPI
from pydantic import BaseModel, Field
from typing import List, Dict, Optional

import math, re

app = FastAPI(title="AI Resume Summary Generator", version="1.0")

# ---------- Data Models ----------
class Experience(BaseModel):
    role: str
    company: str
    start: Optional[str] = None
    end: Optional[str] = None
    bullets: List[str] = []
    metrics: Dict[str, float] = {}

class Project(BaseModel):
    name: str
    description: str
    tech: List[str] = []
    metrics: Dict[str, float] = {}

class Profile(BaseModel):
    name: str
    current_title: str
    years_experience: Optional[float] = None
    skills: List[str] = []
    experiences: List[Experience] = []
    projects: List[Project] = []
    education: List[str] = []
    certifications: List[str] = []

# ---------- Core Logic ----------
def _score_entry(metrics: Dict[str, float], bullets: List[str]) -> float:
    score = 0.0
    for k, v in metrics.items():
        try:
            val = float(v)
            if val <= 0:
                continue
            score += math.log1p(val)
        except Exception:
            continue
    score += 0.2 * len(bullets)
    return score

def _clean_text(s: str) -> str:
    return re.sub(r"\s+", " ", s.strip())

def generate_resume_summary(profile: Profile, tone: str = "concise", max_sentences: int = 3) -> str:
    years = f"{profile.years_experience:g}-year " if profile.years_experience else ""
    intro_parts = []
    intro_parts.append(f"{years}{profile.current_title}" if profile.current_title else f"{years}professional")
    top_skills = ", ".join(profile.skills[:5]) if profile.skills else ""

    candidates = []
    for exp in profile.experiences:
        score = _score_entry(exp.metrics, exp.bullets)
        summary_text = " ".join(exp.bullets[:2]) if exp.bullets else ""
        candidates.append((score, f"{exp.role} at {exp.company}", summary_text, exp.metrics))
    for proj in profile.projects:
        score = _score_entry(proj.metrics, [proj.description])
        candidates.append((score, f"Project: {proj.name}", proj.description, proj.metrics))
    candidates.sort(key=lambda x: x[0], reverse=True)

    sentences = []
    # --- Intro sentence ---
    if tone == "concise":
        intro = f"{profile.name} — {intro_parts[0]} with expertise in {top_skills}."
    elif tone == "technical":
        intro = f"{profile.name} is a {intro_parts[0]} focused on {top_skills} and building scalable systems."
    elif tone == "leadership":
        intro = f"{profile.name} is a {intro_parts[0]} who leads cross-functional teams to deliver measurable impact in {top_skills}."
    else:
        intro = f"{profile.name} — {intro_parts[0]} with expertise in {top_skills}."
    sentences.append(_clean_text(intro))

    # --- Highlights ---
    i = 0
    for score, label, desc, metrics in candidates:
        if i >= max_sentences - 1:
            break
        metric_parts = []
        for k, v in metrics.items():
            if isinstance(v, (int, float)):
                if abs(v) >= 1_000_000:
                    formatted = f"{v/1_000_000:.1f}M {k}"
                elif abs(v) >= 1_000:
                    formatted = f"{v/1000:.1f}k {k}"
                else:
                    formatted = f"{int(v):,} {k}"
            else:
                formatted = f"{v} {k}"
            metric_parts.append(formatted)
        metric_str = ", ".join(metric_parts)

        if tone == "concise":
            sent = f"Delivered {metric_str} as {label}." if metric_str else f"{label}: {desc[:120]}"
        elif tone == "technical":
            sent = f"As {label}, built systems that achieved {metric_str}." if metric_str else f"As {label}, {desc[:120]}"
        elif tone == "leadership":
            sent = f"Led initiatives as {label}, driving {metric_str} and aligning teams to strategic goals." if metric_str else f"Led {label} to deliver: {desc[:120]}"
        else:
            sent = f"{label}: {desc[:120]}"
        sentences.append(_clean_text(sent))
        i += 1

    if len(sentences) < max_sentences:
        if profile.education:
            sentences.append(f"Holds {profile.education[0]}.")
        elif profile.certifications:
            sentences.append(f"Certified in {profile.certifications[0]}.")
    final = " ".join(sentences[:max_sentences])
    final = re.sub(r"\s+", " ", final).strip()
    if not final.endswith("."):
        final += "."
    return final

# ---------- API Endpoint ----------
@app.post("/generate-summary")
def generate_summary(profile: Profile, tone: str = "concise", max_sentences: int = 3):
    summary = generate_resume_summary(profile, tone, max_sentences)
    return {"summary": summary, "tone": tone, "sentences": max_sentences}
