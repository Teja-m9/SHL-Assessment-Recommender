import os
import re
import uuid
from typing import List, Optional

from dotenv import load_dotenv

from app.catalog import Catalog
from app.schemas import ChatRequest, ChatResponse, Message, Recommendation

load_dotenv()


class AgentService:
    def __init__(self, catalog: Optional[Catalog] = None) -> None:
        self.catalog = catalog or Catalog()
        self.session_store = {}
        self.mongo_collection = None
        self._init_persistence()

    def _init_persistence(self) -> None:
        uri = os.getenv("MONGODB_URI")
        if not uri:
            return
        try:
            from pymongo import MongoClient

            client = MongoClient(uri, serverSelectionTimeoutMS=3000)
            database_name = None
            if "/" in uri.split("mongodb+srv://", 1)[-1]:
                candidate = uri.split("mongodb+srv://", 1)[-1].split("/", 1)[1]
                if candidate and "?" not in candidate:
                    database_name = candidate.split("?", 1)[0]
            if not database_name:
                database_name = "shl_assessment"
            self.mongo_collection = client[database_name].get_collection("chat_sessions")
        except Exception:
            self.mongo_collection = None

    def _load_session(self, session_id: Optional[str]) -> List[Message]:
        if not session_id:
            return []
        if self.mongo_collection is not None:
            doc = self.mongo_collection.find_one({"_id": session_id})
            if doc:
                return [Message(**message) for message in doc.get("messages", [])]
        return self.session_store.get(session_id, [])

    def _save_session(self, session_id: Optional[str], messages: List[Message]) -> None:
        if not session_id:
            return
        self.session_store[session_id] = messages
        if self.mongo_collection is not None:
            self.mongo_collection.update_one(
                {"_id": session_id},
                {"$set": {"messages": [message.model_dump() for message in messages]}},
                upsert=True,
            )

    def clear_session(self, session_id: Optional[str]) -> None:
        if not session_id:
            return
        self.session_store.pop(session_id, None)
        if self.mongo_collection is not None:
            self.mongo_collection.delete_one({"_id": session_id})

    def handle_chat(self, request: ChatRequest, session_id: Optional[str] = None) -> ChatResponse:
        messages = list(request.messages)
        resolved_session_id = session_id or str(uuid.uuid4())

        if not messages:
            return ChatResponse(
                reply="I can help you find a suitable SHL assessment. Tell me about the role and the kind of test you need.",
                recommendations=[],
                end_of_conversation=False,
                session_id=resolved_session_id,
            )

        if resolved_session_id:
            existing = self._load_session(resolved_session_id)
            if existing and len(messages) < len(existing):
                messages = existing + [message for message in messages if message not in existing]
            self._save_session(resolved_session_id, messages)

        latest_user = self._latest_user_message(messages)
        if self._is_refusal_trigger(latest_user):
            return ChatResponse(reply="I can help with SHL assessment recommendations, but I can’t help with legal or off-topic advice.", recommendations=[], end_of_conversation=False, state="refuse", session_id=resolved_session_id)

        if self._is_comparison_request(latest_user):
            named_items = self._extract_named_items(latest_user)
            matches = [self.catalog.search(item)[0] for item in named_items if self.catalog.search(item)]
            if matches:
                summary = self._build_comparison_summary(matches)
                return ChatResponse(reply="Here is a direct comparison based on the catalog entries you named.", recommendations=matches, end_of_conversation=False, state="comparing", comparison_summary=summary, session_id=resolved_session_id)

        slots = self._extract_slots(messages, latest_user)
        if self._needs_clarification(slots) and not self._is_refinement_request(latest_user):
            return ChatResponse(reply="I need a little more context before I recommend anything. Tell me the role, seniority, and whether you want a cognitive, skills, or personality test.", recommendations=[], end_of_conversation=False, state="clarifying", session_id=resolved_session_id)

        if self._is_refinement_request(latest_user):
            matches = self.catalog.search(self._build_query(slots) or latest_user)
            if matches:
                return ChatResponse(reply="I’ve updated the shortlist to include your new constraint.", recommendations=matches[:3], end_of_conversation=False, state="refining", session_id=resolved_session_id)

        matches = self.catalog.search(self._build_query(slots))
        if not matches:
            return ChatResponse(reply="I couldn’t find a strong match from the catalog. I can try a different role, level, or test type.", recommendations=[], end_of_conversation=False, state="clarifying", session_id=resolved_session_id)

        selected = matches[:3]
        reply = self._build_reply(slots, selected)
        enhanced_reply = self._maybe_enhance_reply(latest_user, reply, selected)
        return ChatResponse(reply=enhanced_reply, recommendations=selected, end_of_conversation=False, state="recommending", session_id=resolved_session_id)

    def _latest_user_message(self, messages: List[Message]) -> str:
        for message in reversed(messages):
            if message.role == "user":
                return message.content
        return ""

    def _is_refusal_trigger(self, text: str) -> bool:
        lower = text.lower()
        refusal_terms = ["legal advice", "disability", "interview question", "ignore previous instructions", "prompt injection"]
        return any(term in lower for term in refusal_terms)

    def _is_comparison_request(self, text: str) -> bool:
        lower = text.lower()
        return lower.startswith("compare") or "compare" in lower

    def _is_refinement_request(self, text: str) -> bool:
        lower = text.lower()
        return any(term in lower for term in ["add", "also", "include", "instead", "only", "no", "with"])

    def _extract_named_items(self, text: str) -> List[str]:
        tokens = re.findall(r"shl [a-z0-9 ]+", text.lower())
        items = [token.replace("shl ", "").strip().title() for token in tokens]
        if len(items) >= 2:
            return items

        fallback = []
        for name in ["Cognitive Ability Test", "Java Programming Test", "Personality Questionnaire"]:
            if name.lower() in text.lower():
                fallback.append(name)
        return fallback

    def _extract_slots(self, messages: List[Message], latest_text: str = "") -> dict:
        text = " ".join(message.content for message in messages if message.role == "user")
        latest_text = latest_text or text
        slots = {"role": None, "seniority": None, "test_type": None, "skills": None}

        role_patterns = [r"software engineer", r"software developer", r"engineer", r"developer", r"analyst", r"manager", r"designer", r"java"]
        for pattern in role_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                slots["role"] = pattern
                break

        seniority_patterns = [r"entry[- ]level", r"mid[- ]level", r"senior", r"junior", r"senior level", r"mid level"]
        for pattern in seniority_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                slots["seniority"] = pattern
                break

        test_type_priority = ["personality", "cognitive", "skills"]
        test_type_keywords = {
            "cognitive": [r"cognitive", r"reasoning", r"aptitude"],
            "skills": [r"coding", r"programming", r"skills", r"technical", r"java skills", r"skill"],
            "personality": [r"personality", r"behavior"],
        }
        for test_type in test_type_priority:
            if any(re.search(pattern, latest_text, re.IGNORECASE) for pattern in test_type_keywords[test_type]):
                slots["test_type"] = test_type
                break
        if not slots["test_type"]:
            for test_type in test_type_priority:
                if any(re.search(pattern, text, re.IGNORECASE) for pattern in test_type_keywords[test_type]):
                    slots["test_type"] = test_type
                    break

        skill_patterns = [r"java", r"python", r"sql", r"data", r"finance", r"skills assessment", r"assessment"]
        for pattern in skill_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                slots["skills"] = pattern
                break

        return slots

    def _needs_clarification(self, slots: dict) -> bool:
        has_role = bool(slots.get("role"))
        has_context = bool(slots.get("seniority") or slots.get("test_type") or slots.get("skills"))
        return not (has_role and has_context)

    def _build_query(self, slots: dict) -> str:
        pieces = []
        if slots.get("skills"):
            pieces.append(slots["skills"])
        if slots.get("seniority"):
            pieces.append(slots["seniority"])
        if slots.get("test_type"):
            pieces.append(slots["test_type"])
        if slots.get("role"):
            pieces.append(slots["role"])
        return " ".join(pieces)

    def _build_reply(self, slots: dict, recommendations: List[Recommendation]) -> str:
        first = recommendations[0]
        return (
            f"I found a shortlist for {slots.get('role') or 'this role'}: {first.name}. "
            f"It is a {first.test_type} assessment and fits the context you described."
        )

    def _maybe_enhance_reply(self, user_text: str, base_reply: str, recommendations: List[Recommendation]) -> str:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            return base_reply

        try:
            from groq import Groq
        except Exception:
            return base_reply

        try:
            client = Groq(api_key=api_key)
            prompt = (
                "You are an SHL assessment assistant. Rewrite the following answer to be more concise and helpful, "
                "while keeping it grounded in the catalog recommendations.\n\n"
                f"User request: {user_text}\n"
                f"Base answer: {base_reply}\n"
                f"Recommendations: {', '.join(item.name for item in recommendations[:3])}"
            )
            response = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[{"role": "system", "content": "You help with SHL assessment recommendations."}, {"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=220,
            )
            return response.choices[0].message.content.strip() or base_reply
        except Exception:
            return base_reply

    def _build_comparison_summary(self, recommendations: List[Recommendation]) -> str:
        if len(recommendations) < 2:
            return "Only one matching assessment was found."
        first, second = recommendations[0], recommendations[1]
        return f"{first.name} is a {first.test_type} assessment, while {second.name} is a {second.test_type} assessment."
