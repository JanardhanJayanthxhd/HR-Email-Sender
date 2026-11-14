from unittest.mock import AsyncMock, MagicMock

import pytest

from src.llm.extractor import extract_job_post
from src.models import JobPost


@pytest.mark.asyncio
async def test_extract_job_post_success():
    job_text = "Acme Corp hiring Python Developer. Email: hr@acme.com. Need FastAPI, Docker."

    mock_llm = MagicMock()
    mock_structured = AsyncMock()
    mock_structured.ainvoke.return_value = JobPost(
        company="Acme Corp",
        role="Python Developer",
        hr_email="hr@acme.com",
    )
    mock_llm.with_structured_output.return_value = mock_structured

    result = await extract_job_post(job_text, mock_llm)

    assert result.company == "Acme Corp"
    assert result.role == "Python Developer"
    assert result.hr_email == "hr@acme.com"
    mock_llm.with_structured_output.assert_called_once()
    prompt = mock_structured.ainvoke.await_args.args[0]
    assert "key_requirements" not in prompt
    assert "applicant profile" not in prompt.lower()


@pytest.mark.asyncio
async def test_extract_rejects_email_not_in_candidates():
    job_text = "Acme Corp hiring. Email: hr@acme.com"

    mock_llm = MagicMock()
    mock_structured = AsyncMock()
    # The LLM should return an email that's NOT in the candidate list extracted from text
    mock_structured.ainvoke.return_value = JobPost(
        company="Acme Corp",
        role="Developer",
        hr_email="fake@notintext.com",  # This email should NOT be in candidate list
    )
    mock_llm.with_structured_output.return_value = mock_structured

    with pytest.raises(ValueError, match="not found in original"):
        await extract_job_post(job_text, mock_llm)
    mock_structured.ainvoke.assert_awaited_once()


@pytest.mark.asyncio
async def test_extract_no_email_found():
    job_text = "Acme Corp hiring Python Developer. No email provided."

    result = await extract_job_post(job_text, MagicMock())

    assert result is None
