import uuid
from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class SessionMemory:
    session_id: str
    resume_text: str = ""
    extracted_data: Dict = field(default_factory=dict)
    conversation_history: List[Dict] = field(default_factory=list)
    intent_history: List[str] = field(default_factory=list)


class MemoryStore:
    def __init__(self) -> None:
        self._sessions: Dict[str, SessionMemory] = {}

    def create_session(self) -> SessionMemory:
        session_id = str(uuid.uuid4())
        session = SessionMemory(session_id=session_id)
        self._sessions[session_id] = session
        return session

    def get_session(self, session_id: str) -> SessionMemory:
        return self._sessions.get(session_id)

    def save_session(self, session: SessionMemory) -> None:
        self._sessions[session.session_id] = session

