import os
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, jsonify, request, send_from_directory

from agent import ResumeAgent
from llm import GeminiClient
from memory import MemoryStore
from tools import extract_text_from_pdf, parse_resume_text


load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = BASE_DIR.parent / "frontend"

app = Flask(__name__, static_folder=str(FRONTEND_DIR), static_url_path="")
memory_store = MemoryStore()
llm_client = GeminiClient(api_key=os.getenv("GEMINI_API_KEY"))
agent = ResumeAgent(llm_client=llm_client)


@app.get("/")
def index():
    return send_from_directory(str(FRONTEND_DIR), "index.html")


@app.get("/health")
def health():
    return jsonify({"status": "ok"})


@app.post("/api/session")
def create_session():
    session = memory_store.create_session()
    return jsonify({"session_id": session.session_id})


@app.post("/api/upload-resume")
def upload_resume():
    session_id = request.form.get("session_id", "").strip()
    if not session_id:
        return jsonify({"error": "session_id is required"}), 400

    session = memory_store.get_session(session_id)
    if not session:
        return jsonify({"error": "invalid session_id"}), 404

    resume_text = request.form.get("resume_text", "").strip()
    uploaded_file = request.files.get("resume_file")

    if uploaded_file and uploaded_file.filename.lower().endswith(".pdf"):
        file_bytes = uploaded_file.read()
        resume_text = extract_text_from_pdf(file_bytes)
    elif uploaded_file:
        resume_text = uploaded_file.read().decode("utf-8", errors="ignore")

    if not resume_text:
        return jsonify({"error": "Provide resume_text or upload resume_file"}), 400

    parsed = parse_resume_text(resume_text)
    session.resume_text = resume_text
    session.extracted_data = parsed
    memory_store.save_session(session)

    return jsonify(
        {
            "message": "Resume processed successfully",
            "extracted_data": parsed,
        }
    )


@app.post("/api/chat")
def chat():
    data = request.get_json(silent=True) or {}
    session_id = str(data.get("session_id", "")).strip()
    message = str(data.get("message", "")).strip()

    if not session_id or not message:
        return jsonify({"error": "session_id and message are required"}), 400

    session = memory_store.get_session(session_id)
    if not session:
        return jsonify({"error": "invalid session_id"}), 404

    if not session.extracted_data:
        return jsonify(
            {
                "answer": "Please upload a resume first.",
                "confidence": 1.0,
                "source": "inference",
                "missing_data": ["resume"],
            }
        )

    result = agent.respond(
        extracted_data=session.extracted_data,
        conversation_history=session.conversation_history,
        user_message=message,
    )

    session.conversation_history.append({"role": "user", "content": message})
    session.conversation_history.append({"role": "assistant", "content": result["answer"]})
    memory_store.save_session(session)

    return jsonify(result)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=False)
