from langchain_core.language_models import BaseChatModel
from tenacity import retry, stop_after_attempt, wait_fixed

from src.extraction.email_finder import find_emails
from src.llm.prompts import EXTRACTION_PROMPT
from src.logger import log
from src.models import JobPost


@retry(stop=stop_after_attempt(3), wait=wait_fixed(1), reraise=True)
async def _invoke_extractor(
    text: str, candidate_emails: list[str], llm: BaseChatModel
) -> JobPost:
    structured_llm = llm.with_structured_output(JobPost, method="json_schema")
    return await structured_llm.ainvoke(
        EXTRACTION_PROMPT.format(job_text=text, candidate_emails=candidate_emails)
    )


async def extract_job_post(text: str, llm: BaseChatModel) -> JobPost | None:
    """Extract structured job post data from text.

    Args:
        text: Job post text (e.g., from LinkedIn).
        llm: LangChain chat model.

    Returns:
        JobPost with extracted data, or None if no email found.

    Raises:
        ValueError: If LLM returns email not in candidate list.
    """
    candidate_emails = find_emails(text)

    if not candidate_emails:
        log.info("No email addresses found in job post")
        return None

    result = await _invoke_extractor(text, candidate_emails, llm)

    # Step 3: Validate HR email is from candidates (Review Focus #1)
    if result.hr_email not in candidate_emails:
        log.error("LLM selected an email address not present in the job post")
        raise ValueError("LLM returned an email address not found in original job post")

    return result
