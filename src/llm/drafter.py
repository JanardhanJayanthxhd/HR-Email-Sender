import re

from langchain_core.language_models import BaseChatModel
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from src.llm.prompts import DRAFTING_PROMPT
from src.models import EmailDraft, JobPost

_EMAIL_PATTERN = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
_SIGN_OFF_PATTERN = re.compile(
    r"\s+(?:best regards|kind regards|warm regards|regards|sincerely|yours sincerely)"
    r"\s*,?\s*.*$",
    re.IGNORECASE | re.DOTALL,
)
_SENTENCE_BOUNDARY = re.compile(r"(?<=[.!?])\s+(?=[A-Z])")


def format_email_body(body: str, sender_name: str, reply_to_email: str) -> str:
    """Normalize generated text and append the configured contact signature."""
    body = body.replace("\r\n", "\n").replace("\r", "\n").strip()
    body = _SIGN_OFF_PATTERN.sub("", body).strip()
    body = _EMAIL_PATTERN.sub("", body).strip()

    if sender_name:
        body = re.sub(rf"\s*{re.escape(sender_name)}\s*$", "", body, flags=re.IGNORECASE).strip()

    body = re.sub(r"(?i)^(Dear [^,\n]+[,!])\s+", r"\1\n\n", body)

    paragraphs = []
    for paragraph in re.split(r"\n\s*\n", body):
        paragraph = re.sub(r"\s*\n\s*", " ", paragraph).strip()
        if not paragraph:
            continue

        sentences = _SENTENCE_BOUNDARY.split(paragraph)
        if len(sentences) > 2:
            paragraphs.extend(
                " ".join(sentences[index : index + 2]).strip()
                for index in range(0, len(sentences), 2)
            )
        else:
            paragraphs.append(paragraph)

    formatted_body = "\n\n".join(paragraphs)
    signature = f"Best regards,\n{sender_name}\n{reply_to_email}"
    return f"{formatted_body}\n\n{signature}" if formatted_body else signature


@retry(
    retry=retry_if_exception_type((ValueError,)),
    stop=stop_after_attempt(2),
    wait=wait_exponential(multiplier=0.2, min=0.2, max=1),
    reraise=True,
)
async def draft_email(
    job_post: JobPost,
    profile: str,
    sender_name: str,
    reply_to_email: str,
    llm: BaseChatModel,
) -> EmailDraft:
    """Draft a concise tailored application email using only profile facts."""
    structured = llm.with_structured_output(EmailDraft)
    result = await (DRAFTING_PROMPT | structured).ainvoke(
        {
            "sender_name": sender_name,
            "profile": profile,
            "job_details": job_post.model_dump_json(),
        }
    )
    draft = result if isinstance(result, EmailDraft) else EmailDraft.model_validate(result)
    draft.body = format_email_body(draft.body, sender_name, reply_to_email)
    if len(draft.body.split()) > 150:
        raise ValueError("Generated email body exceeds 150 words")
    return draft
