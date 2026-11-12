from langchain_core.language_models import BaseChatModel
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from src.llm.prompts import DRAFTING_PROMPT
from src.models import EmailDraft, JobPost


@retry(
    retry=retry_if_exception_type((ValueError,)),
    stop=stop_after_attempt(2),
    wait=wait_exponential(multiplier=0.2, min=0.2, max=1),
    reraise=True,
)
async def draft_email(
    job_post: JobPost, profile: str, sender_name: str, llm: BaseChatModel
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
    if len(draft.body.split()) > 150:
        raise ValueError("Generated email body exceeds 150 words")
    return draft
