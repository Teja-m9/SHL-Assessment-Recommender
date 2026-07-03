import logging
import os
from collections import defaultdict
from typing import Iterable, Optional

from dotenv import load_dotenv

from app.constants import (
    REFINEMENT_PREFIXES,
    REFUSAL_TERMS,
    ROLE_KEYWORDS,
    SENIORITY_KEYWORDS,
    SKILL_KEYWORDS,
    TEST_TYPE_KEYWORDS,
)
from app.prompts import GROQ_SYSTEM_PROMPT, build_groq_rewrite_prompt
from app.schemas import ChatRequest, ChatResponse, Message, Recommendation
from app.services.catalog_service import Catalog

load_dotenv()
logger = logging.getLogger(__name__)


class AgentService:
    def __init__(self, catalog: Optional[Catalog] = None) -> None:
        self.catalog = catalog or Catalog()
        self.groq_model = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
        self.groq_temperature = float(os.getenv("GROQ_TEMPERATURE", "0.2"))
        self.groq_max_tokens = int(os.getenv("GROQ_MAX_TOKENS", "220"))
        self.groq_client = self._init_groq_client()

    def _init_groq_client(self):
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            return None
        try:
            from groq import Groq

            return Groq(api_key=api_key)
        except Exception:
            return None

    def handle_chat(self, request: ChatRequest) -> ChatResponse:
        messages = list(request.messages)
        latest_user = self._latest_user_message(messages)

        if not latest_user:
            return self._finalize_response(
                user_text="",
                base_reply="Tell me about the role, seniority, and assessment need, and I will recommend SHL assessments from the catalog.",
                recommendations=[],
                intent="clarification",
                end_of_conversation=False,
                state="clarifying",
            )

        if self._is_refusal_trigger(latest_user):
            return self._finalize_response(
                user_text=latest_user,
                base_reply="I can only help with SHL assessment selection. I cannot provide general hiring, legal, or prompt-injection guidance.",
                recommendations=[],
                intent="refusal",
                end_of_conversation=False,
                state="refuse",
            )

        if self._is_comparison_request(latest_user):
            compared = self.catalog.find_assessments_in_text(latest_user)
            if len(compared) >= 2:
                reply = self._build_comparison_reply(compared[:2])
                return self._finalize_response(
                    user_text=latest_user,
                    base_reply=reply,
                    recommendations=compared[:2],
                    intent="comparison",
                    end_of_conversation=True,
                    state="comparing",
                    comparison_summary=reply,
                )
            return self._finalize_response(
                user_text=latest_user,
                base_reply="Please name the SHL assessments you want compared, and I will compare them using the catalog data only.",
                recommendations=[],
                intent="clarification",
                end_of_conversation=False,
                state="clarifying",
            )

        profile = self._extract_profile(messages)
        if self._needs_clarification(profile):
            return self._finalize_response(
                user_text=latest_user,
                base_reply=self._build_clarification_reply(profile),
                recommendations=[],
                intent="clarification",
                end_of_conversation=False,
                state="clarifying",
            )

        recommendations = self.catalog.search(profile, limit=10)
        if not recommendations:
            return self._finalize_response(
                user_text=latest_user,
                base_reply="I could not find a strong SHL catalog match yet. Try sharing the role, seniority, core skills, or preferred assessment type.",
                recommendations=[],
                intent="clarification",
                end_of_conversation=False,
                state="clarifying",
            )

        shortlist = recommendations[: min(5, len(recommendations))]
        intent = "refinement" if self._is_refinement_turn(messages) else "recommendation"
        reply = self._build_recommendation_reply(profile, shortlist, intent)
        return self._finalize_response(
            user_text=latest_user,
            base_reply=reply,
            recommendations=shortlist,
            intent=intent,
            end_of_conversation=True,
            state="refining" if intent == "refinement" else "recommending",
        )

    def _finalize_response(
        self,
        user_text: str,
        base_reply: str,
        recommendations: list[Recommendation],
        intent: str,
        end_of_conversation: bool,
        state: str,
        comparison_summary: str | None = None,
    ) -> ChatResponse:
        reply, reply_source, llm_model = self._maybe_enhance_reply(user_text, base_reply, recommendations, intent)
        return ChatResponse(
            reply=reply,
            recommendations=recommendations,
            end_of_conversation=end_of_conversation,
            state=state,
            comparison_summary=comparison_summary,
            reply_source=reply_source,
            llm_model=llm_model,
        )

    def _latest_user_message(self, messages: Iterable[Message]) -> str:
        for message in reversed(list(messages)):
            if message.role == "user":
                return message.content.strip()
        return ""

    def _is_refusal_trigger(self, text: str) -> bool:
        lower = text.lower()
        return any(term in lower for term in REFUSAL_TERMS)

    def _is_comparison_request(self, text: str) -> bool:
        lower = text.lower()
        return "compare" in lower or "difference between" in lower

    def _extract_profile(self, messages: list[Message]) -> dict:
        user_text = " ".join(message.content for message in messages if message.role == "user")
        latest_text = self._latest_user_message(messages).lower()
        normalized = user_text.lower()

        profile = {
            "role": self._match_first(ROLE_KEYWORDS, normalized),
            "seniority": self._match_first(SENIORITY_KEYWORDS, normalized),
            "test_types": self._collect_matches(TEST_TYPE_KEYWORDS, normalized, latest_text),
            "skills": self._extract_skills(normalized),
        }
        return profile

    def _match_first(self, keyword_map: dict[str, list[str]], text: str) -> Optional[str]:
        for canonical, variants in keyword_map.items():
            if any(variant in text for variant in variants):
                return canonical
        return None

    def _collect_matches(
        self,
        keyword_map: dict[str, list[str]],
        text: str,
        latest_text: str,
    ) -> list[str]:
        weighted_matches: dict[str, int] = defaultdict(int)
        for canonical, variants in keyword_map.items():
            if any(variant in text for variant in variants):
                weighted_matches[canonical] += 1
            if any(variant in latest_text for variant in variants):
                weighted_matches[canonical] += 2
        ordered = sorted(weighted_matches.items(), key=lambda item: (-item[1], item[0]))
        return [name for name, _ in ordered]

    def _extract_skills(self, text: str) -> list[str]:
        return [skill for skill in SKILL_KEYWORDS if skill in text]

    def _needs_clarification(self, profile: dict) -> bool:
        has_role = bool(profile["role"])
        has_target = bool(profile["test_types"] or profile["skills"])
        return not (has_role and has_target)

    def _build_clarification_reply(self, profile: dict) -> str:
        missing = []
        if not profile["role"]:
            missing.append("the role")
        if not profile["test_types"]:
            missing.append("the assessment type")
        if not profile["skills"]:
            missing.append("the key skill area")

        missing_text = ", ".join(missing[:-1])
        if missing_text and len(missing) > 1:
            missing_text = f"{missing_text}, and {missing[-1]}"
        elif missing:
            missing_text = missing[0]
        else:
            missing_text = "a bit more detail"

        return (
            f"I need {missing_text} before I recommend SHL assessments. "
            "Tell me the role, seniority, and whether you need cognitive, personality, or technical testing."
        )

    def _is_refinement_turn(self, messages: list[Message]) -> bool:
        user_messages = [message.content.strip().lower() for message in messages if message.role == "user"]
        if len(user_messages) < 2:
            return False
        latest = user_messages[-1]
        return latest.startswith(REFINEMENT_PREFIXES)

    def _build_recommendation_reply(
        self,
        profile: dict,
        recommendations: list[Recommendation],
        intent: str,
    ) -> str:
        intro = "I updated the shortlist" if intent == "refinement" else "Here is a grounded SHL shortlist"
        role_text = profile["role"] or "the role"
        seniority_text = f" for a {profile['seniority']} {role_text}" if profile["seniority"] else f" for {role_text}"
        type_text = ""
        if profile["test_types"]:
            type_text = f" focused on {', '.join(profile['test_types'])} assessment needs"

        bullets = "; ".join(f"{item.name} ({item.url})" for item in recommendations)
        return f"{intro}{seniority_text}{type_text}: {bullets}."

    def _build_comparison_reply(self, recommendations: list[Recommendation]) -> str:
        first, second = recommendations[:2]
        return (
            f"{first.name} is a {first.test_type} assessment, while {second.name} is a {second.test_type} assessment. "
            f"You can review them here: {first.url} and {second.url}."
        )

    def _maybe_enhance_reply(
        self,
        user_text: str,
        base_reply: str,
        recommendations: list[Recommendation],
        intent: str,
    ) -> tuple[str, str, str | None]:
        if self.groq_client is None:
            logger.info("Groq rewrite skipped: missing client")
            return base_reply, "catalog", None

        try:
            prompt = build_groq_rewrite_prompt(
                intent=intent,
                user_text=user_text,
                base_reply=base_reply,
                grounded_matches=self._format_recommendations(recommendations),
            )
            response = self.groq_client.chat.completions.create(
                model=self.groq_model,
                messages=[
                    {
                        "role": "system",
                        "content": GROQ_SYSTEM_PROMPT,
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=self.groq_temperature,
                max_tokens=self.groq_max_tokens,
            )
            content = response.choices[0].message.content.strip()
            if content:
                logger.info("Groq rewrite succeeded with model=%s", self.groq_model)
                return content, "groq", self.groq_model

            logger.info("Groq rewrite returned empty content; using catalog reply")
            return base_reply, "catalog", None
        except Exception as exc:
            logger.warning("Groq rewrite failed; using catalog reply", exc_info=exc)
            return base_reply, "catalog", None

    def _format_recommendations(self, recommendations: list[Recommendation]) -> str:
        if not recommendations:
            return "No recommendations."
        return " | ".join(f"{item.name} ({item.test_type}) -> {item.url}" for item in recommendations)