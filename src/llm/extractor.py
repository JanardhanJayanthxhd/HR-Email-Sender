from langchain_core.language_models import BaseChatModel
from tenacity import retry, stop_after_attempt, wait_fixed

from src.extraction.email_finder import find_emails
from src.llm.prompts import EXTRACTION_PROMPT
from src.logger import log
from src.models import JobPost, JobPostExtraction


@retry(stop=stop_after_attempt(3), wait=wait_fixed(1), reraise=True)
async def _invoke_extractor(text: str, llm: BaseChatModel) -> JobPostExtraction:
    structured_llm = llm.with_structured_output(JobPostExtraction, method="json_schema")
    return await structured_llm.ainvoke(
        EXTRACTION_PROMPT.format(job_text=text)
    )


async def extract_job_post(text: str, llm: BaseChatModel) -> JobPost | None:
    """Extract structured job post data from text.

    Args:
        text: Job post text (e.g., from LinkedIn).
        llm: LangChain chat model.

    Returns:
        JobPost with extracted company, role, and all email addresses found,
        or None if no email is found.
    """
    candidate_emails = find_emails(text)

    if not candidate_emails:
        log.info("No email addresses found in job post")
        return None

    result = await _invoke_extractor(text, llm)
    log.info(f"Result from _invoke_extractor(): {result}")

    return JobPost(
        company=result.company,
        role=result.role,
        hr_emails=candidate_emails,
    )
