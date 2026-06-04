from typing import Dict, List

try:
    from backend.llm import GeminiClient
    from backend.models import AgentResponse
    from backend.tools import (
        extract_required_skills_from_query,
        infer_intent,
        match_required_skills,
        missing_data_fields,
    )
except ImportError:
    from llm import GeminiClient
    from models import AgentResponse
    from tools import (
        extract_required_skills_from_query,
        infer_intent,
        match_required_skills,
        missing_data_fields,
    )


SYSTEM_ROLE = (
    "You are a strict hiring assistant. Use only supplied resume data and conversation context. "
    "Do not fabricate. If data is absent, state 'Not mentioned in resume'. "
    "Return valid JSON only with keys: answer, confidence, source, missing_data."
)


class ResumeAgent:
    def __init__(self, llm_client: GeminiClient) -> None:
        self.llm_client = llm_client

    def respond(self, extracted_data: Dict, conversation_history: List[Dict], user_message: str) -> Dict:
        intent = infer_intent(user_message)
        required_skills = extract_required_skills_from_query(user_message)
        tool_payload: Dict = {}

        if intent == "skill_query" and required_skills:
            tool_payload["skill_match"] = match_required_skills(extracted_data, required_skills)

        missing = missing_data_fields(extracted_data, intent, required_skills)
        fallback = self._deterministic_fallback(extracted_data, intent, user_message, tool_payload, missing)

        prompt = self._build_prompt(extracted_data, conversation_history, user_message, intent, tool_payload, missing)
        llm_result = self.llm_client.generate_json(prompt)

        if not llm_result:
            return fallback.to_dict()

        answer = str(llm_result.get("answer", "")).strip() or fallback.answer
        confidence = float(llm_result.get("confidence", fallback.confidence))
        source = llm_result.get("source", fallback.source)
        missing_data = llm_result.get("missing_data", missing)
        if not isinstance(missing_data, list):
            missing_data = missing

        if "Not mentioned in resume" not in answer and missing_data:
            answer = f"{answer}\n\nMissing details: {', '.join(missing_data)}. Not mentioned in resume."

        return AgentResponse(
            answer=answer,
            confidence=confidence,
            source=source,
            missing_data=missing_data,
        ).to_dict()

    def _build_prompt(
        self,
        extracted_data: Dict,
        conversation_history: List[Dict],
        user_message: str,
        intent: str,
        tool_payload: Dict,
        missing: List[str],
    ) -> str:
        compact_history = conversation_history[-6:]
        return f"""
{SYSTEM_ROLE}

intent: {intent}
user_message: {user_message}
resume_data: {extracted_data}
tool_output: {tool_payload}
conversation_history: {compact_history}
known_missing_fields: {missing}

Rules:
1) Never invent resume facts.
2) If data is absent, explicitly include "Not mentioned in resume".
3) Confidence must be 0-1.
4) source must be "resume" for direct facts and "inference" for evaluations.
5) missing_data must be an array of missing fields.
"""

    def _deterministic_fallback(
        self,
        extracted_data: Dict,
        intent: str,
        user_message: str,
        tool_payload: Dict,
        missing: List[str],
    ) -> AgentResponse:
        name = extracted_data.get("name", "Not mentioned in resume")
        skills = extracted_data.get("skills", [])
        education = extracted_data.get("education", [])
        experience = extracted_data.get("experience", [])

        if not extracted_data:
            return AgentResponse(
                answer="Please upload a resume first.",
                confidence=0.98,
                source="inference",
                missing_data=["resume"],
            )

        if intent == "summarize_resume":
            answer = (
                f"Candidate: {name}\n"
                f"Skills: {', '.join(skills) if skills else 'Not mentioned in resume'}\n"
                f"Experience highlights: {experience[0] if experience else 'Not mentioned in resume'}\n"
                f"Education highlights: {education[0] if education else 'Not mentioned in resume'}"
            )
            return AgentResponse(answer=answer, confidence=0.82, source="resume", missing_data=missing)

        if intent == "candidate_evaluation":
            strengths = ", ".join(skills[:5]) if skills else "Not mentioned in resume"
            answer = (
                f"Preliminary evaluation for {name}: candidate shows evidence of {strengths}. "
                f"Final decision should include interview and project-depth validation."
            )
            return AgentResponse(answer=answer, confidence=0.72, source="inference", missing_data=missing)

        if intent == "skill_query" and "skill_match" in tool_payload:
            m = tool_payload["skill_match"]
            answer = (
                f"Matched skills: {', '.join(m['matched_skills']) if m['matched_skills'] else 'None'}; "
                f"Missing: {', '.join(m['missing_skills']) if m['missing_skills'] else 'None'}. "
                f"Match score: {m['match_score']:.2f}."
            )
            return AgentResponse(answer=answer, confidence=0.88, source="resume", missing_data=missing)

        if intent == "experience_query":
            answer = (
                "\n".join(experience[:4]) if experience else "Experience: Not mentioned in resume."
            )
            return AgentResponse(answer=answer, confidence=0.8, source="resume", missing_data=missing)

        if intent == "education_query":
            answer = (
                "\n".join(education[:4]) if education else "Education: Not mentioned in resume."
            )
            return AgentResponse(answer=answer, confidence=0.8, source="resume", missing_data=missing)

        answer = (
            f"Based on the resume, I can help with summary, skill match, candidate evaluation, "
            f"experience, and education insights. Your question was: {user_message}"
        )
        return AgentResponse(answer=answer, confidence=0.65, source="inference", missing_data=missing)
