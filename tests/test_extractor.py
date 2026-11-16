from unittest.mock import AsyncMock, MagicMock

import pytest

from src.llm.extractor import extract_job_post
from src.models import JobPostExtraction


@pytest.mark.asyncio
async def test_extract_job_post_success():
    job_text = "Acme Corp hiring Python Developer. Email: hr@acme.com. Need FastAPI, Docker."

    mock_llm = MagicMock()
    mock_structured = AsyncMock()
    mock_structured.ainvoke.return_value = JobPostExtraction(
        company="Acme Corp",
        role="Python Developer",
    )
    mock_llm.with_structured_output.return_value = mock_structured

    result = await extract_job_post(job_text, mock_llm)

    assert result.company == "Acme Corp"
    assert result.role == "Python Developer"
    assert result.hr_emails == ["hr@acme.com"]
    mock_llm.with_structured_output.assert_called_once_with(
        JobPostExtraction, method="json_schema"
    )
    prompt = mock_structured.ainvoke.await_args.args[0]
    assert "key_requirements" not in prompt
    assert "applicant profile" not in prompt.lower()
    assert "Candidate emails:" not in prompt


@pytest.mark.asyncio
async def test_extract_returns_all_emails_without_llm_selection():
    job_text = "Acme Corp hiring. Email: hr@acme.com or careers@acme.com"

    mock_llm = MagicMock()
    mock_structured = AsyncMock()
    mock_structured.ainvoke.return_value = JobPostExtraction(
        company="Acme Corp",
        role="Developer",
    )
    mock_llm.with_structured_output.return_value = mock_structured

    result = await extract_job_post(job_text, mock_llm)

    assert result.hr_emails == ["hr@acme.com", "careers@acme.com"]
    mock_structured.ainvoke.assert_awaited_once()


@pytest.mark.asyncio
async def test_extract_no_email_found():
    job_text = "Acme Corp hiring Python Developer. No email provided."

    result = await extract_job_post(job_text, MagicMock())

    assert result is None
