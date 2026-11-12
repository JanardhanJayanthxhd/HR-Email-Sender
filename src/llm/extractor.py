from langchain_core.language_models import BaseChatModel
from tenacity import retry, stop_after_attempt, wait_fixed

from src.extraction.email_finder import find_emails
from src.llm.prompts import EXTRACTION_PROMPT
from src.models import JobPost


@retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
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
    # Step 1: Extract candidate emails via regex
    candidate_emails = find_emails(text)

    if not candidate_emails:
        return None

    # Step 2: LLM extracts structured data and selects HR email
    structured_llm = llm.with_structured_output(JobPost, method="json_schema")

    result: JobPost = await structured_llm.ainvoke(
        EXTRACTION_PROMPT.format(
            job_text=text,
            candidate_emails=candidate_emails
        )
    )

    # Step 3: Validate HR email is from candidates (Review Focus #1)
    if result.hr_email not in candidate_emails:
        raise ValueError(
            f"LLM returned email '{result.hr_email}' not found in original text. "
            f"Candidates were: {candidate_emails}"
        )

    return result