import io
import re
from typing import Dict, List, Tuple

from PyPDF2 import PdfReader


SKILL_KEYWORDS = {
    "python",
    "java",
    "javascript",
    "typescript",
    "react",
    "next.js",
    "node.js",
    "flask",
    "django",
    "fastapi",
    "sql",
    "postgresql",
    "mysql",
    "mongodb",
    "docker",
    "kubernetes",
    "aws",
    "gcp",
    "azure",
    "terraform",
    "langchain",
    "llm",
    "machine learning",
    "pytorch",
    "tensorflow",
    "redis",
    "graphql",
    "git",
    "ci/cd",
}


def extract_text_from_pdf(file_bytes: bytes) -> str:
    reader = PdfReader(io.BytesIO(file_bytes))
    pages: List[str] = []
    for page in reader.pages:
        page_text = page.extract_text() or ""
        pages.append(page_text)
    return "\n".join(pages).strip()


def parse_resume_text(resume_text: str) -> Dict:
    lines = [line.strip() for line in resume_text.splitlines() if line.strip()]
    lower = resume_text.lower()

    name = _extract_name(lines)
    email = _extract_email(resume_text)
    phone = _extract_phone(resume_text)
    skills = _extract_skills(lower)
    education = _extract_section(lines, ["education"])
    experience = _extract_section(lines, ["experience", "work history", "professional experience"])

    return {
        "name": name or "Not mentioned in resume",
        "email": email or "Not mentioned in resume",
        "phone": phone or "Not mentioned in resume",
        "skills": skills,
        "education": education,
        "experience": experience,
    }


def match_required_skills(parsed_data: Dict, required_skills: List[str]) -> Dict:
    normalized_resume_skills = {s.lower() for s in parsed_data.get("skills", [])}
    required = [s.strip().lower() for s in required_skills if s.strip()]

    matched = [s for s in required if s in normalized_resume_skills]
    missing = [s for s in required if s not in normalized_resume_skills]
    score = (len(matched) / len(required)) if required else 0.0

    return {
        "matched_skills": matched,
        "missing_skills": missing,
        "match_score": round(score, 3),
    }


def infer_intent(message: str) -> str:
    m = message.lower()
    if "summary" in m or "summarize" in m:
        return "summarize_resume"
    if "fit" in m or "evaluate" in m or "hire" in m:
        return "candidate_evaluation"
    if "skill" in m or "stack" in m:
        return "skill_query"
    if "experience" in m:
        return "experience_query"
    if "education" in m or "degree" in m:
        return "education_query"
    return "general_query"


def extract_required_skills_from_query(message: str) -> List[str]:
    text = message.lower()
    if ":" in text:
        text = text.split(":", 1)[1]
    parts = re.split(r"[,/]| and ", text)
    result = []
    for part in parts:
        token = part.strip()
        token = re.sub(r"[^a-z0-9.+#\- ]", "", token)
        if 2 <= len(token) <= 30 and token:
            if token in SKILL_KEYWORDS or token in {"go", "c++", "c#", "rust"}:
                result.append(token)
    return list(dict.fromkeys(result))


def missing_data_fields(parsed_data: Dict, intent: str, required_skills: List[str] = None) -> List[str]:
    missing: List[str] = []
    if parsed_data.get("name") == "Not mentioned in resume":
        missing.append("name")
    if intent == "education_query" and not parsed_data.get("education"):
        missing.append("education")
    if intent == "experience_query" and not parsed_data.get("experience"):
        missing.append("experience")
    if intent == "skill_query":
        if not parsed_data.get("skills"):
            missing.append("skills")
        elif required_skills:
            existing = {s.lower() for s in parsed_data.get("skills", [])}
            absent = [s for s in required_skills if s.lower() not in existing]
            if absent:
                missing.append("required_skills_not_found")
    return missing


def _extract_name(lines: List[str]) -> str:
    if not lines:
        return ""
    first = lines[0]
    if len(first.split()) <= 5 and not any(ch.isdigit() for ch in first) and "@" not in first:
        return first
    return ""


def _extract_email(text: str) -> str:
    match = re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text)
    return match.group(0) if match else ""


def _extract_phone(text: str) -> str:
    match = re.search(r"(\+?\d[\d\-\s()]{7,}\d)", text)
    return match.group(0) if match else ""


def _extract_skills(lower_text: str) -> List[str]:
    found = []
    for skill in SKILL_KEYWORDS:
        if re.search(rf"\b{re.escape(skill)}\b", lower_text):
            found.append(skill)
    return sorted(found)


def _extract_section(lines: List[str], section_titles: List[str]) -> List[str]:
    section: List[str] = []
    capture = False
    for line in lines:
        lower = line.lower()
        if any(title in lower for title in section_titles):
            capture = True
            continue
        if capture and re.match(r"^[A-Z][A-Za-z ]{2,20}:?$", line):
            break
        if capture:
            section.append(line)
    return section

