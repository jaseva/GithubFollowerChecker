from __future__ import annotations

import logging
import os
from dataclasses import dataclass

from app.models import ProfileSummarySubject

logger = logging.getLogger(__name__)

DEFAULT_OPENAI_PROFILE_MODEL = "gpt-4o-mini"


@dataclass(frozen=True)
class OpenAIProfileSummary:
    text: str
    model: str


def profile_summary_provider() -> str:
    return os.getenv("PROFILE_SUMMARY_PROVIDER", "auto").strip().lower()


def profile_summary_model() -> str:
    return os.getenv("OPENAI_PROFILE_SUMMARY_MODEL", DEFAULT_OPENAI_PROFILE_MODEL).strip() or DEFAULT_OPENAI_PROFILE_MODEL


def profile_summary_timeout() -> float:
    raw = os.getenv("OPENAI_PROFILE_SUMMARY_TIMEOUT_SECONDS", "8")
    try:
        return max(2.0, float(raw))
    except ValueError:
        return 8.0


def build_desktop_profile_prompt(profile: ProfileSummarySubject) -> str:
    profile_description = profile.bio or "No bio available"
    if profile.repository_names:
        repository_context = ", ".join(profile.repository_names[:30])
    else:
        repository_context = f"{profile.public_repos:,} public repositories; repository names are not cached in the dashboard payload"

    context_lines = [
        f"Followers: {profile.followers:,}",
        f"Following: {profile.following:,}",
        f"Public repositories: {profile.public_repos:,}",
    ]
    if profile.company:
        context_lines.append(f"Company: {profile.company}")
    if profile.location:
        context_lines.append(f"Location: {profile.location}")
    if profile.signal_score is not None:
        context_lines.append(f"Local signal score: {profile.signal_score:.0f} ({profile.signal_label or 'Signal'})")

    # This intentionally mirrors the desktop app's Generate Summary prompt,
    # with explicit guardrails for the web investigation workflow.
    return (
        f"User {profile.username} has the following bio: {profile_description}. "
        f"They have contributed to the following repositories: {repository_context}. "
        "Summarize the user's profile and contributions. Identify the sentiment & tone of the individual.\n\n"
        "Use only the supplied GitHub fields below. Do not invent repositories, employers, achievements, protected traits, "
        "employment recommendations, compensation recommendations, or promotion/ranking conclusions.\n"
        + "\n".join(context_lines)
    )


def generate_desktop_style_openai_summary(
    profile: ProfileSummarySubject,
    *,
    prefer_ai: bool = True,
) -> OpenAIProfileSummary | None:
    provider = profile_summary_provider()
    if not prefer_ai or provider == "local":
        return None

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None

    try:
        from openai import OpenAI
    except ImportError:
        logger.info("OpenAI SDK is not installed; using local profile summary fallback.")
        return None

    model = profile_summary_model()
    prompt = build_desktop_profile_prompt(profile)

    try:
        client = OpenAI(api_key=api_key, timeout=profile_summary_timeout())
        completion = client.chat.completions.create(
            model=model,
            temperature=0.2,
            max_tokens=260,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": "Write a concise summary from this user's GitHub profile."},
            ],
        )
        content = completion.choices[0].message.content
        if not content:
            return None
        return OpenAIProfileSummary(text=content.strip(), model=model)
    except Exception:
        if provider == "openai":
            logger.exception("OpenAI profile summary failed.")
        else:
            logger.info("OpenAI profile summary unavailable; using local fallback.", exc_info=True)
        return None
