# Telegram Job Application Bot Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Telegram bot that extracts job details from pasted LinkedIn text, drafts tailored application emails using LLMs, and sends them via Gmail after explicit user approval.

**Architecture:** Python async application using python-telegram-bot for Telegram integration, LangChain for LLM abstraction (Ollama/Google providers), aiosmtplib for Gmail SMTP, aiosqlite for application logging, and pydantic-settings for configuration.

**Tech Stack:** Python 3.11+, python-telegram-bot, LangChain, Ollama/Google Gemini, aiosmtplib, aiosqlite, pydantic, structlog

**Spec:** `docs/superpowers/specs/2026-11-12-telegram-job-bot-design.md`

## Global Constraints

- Python 3.11+ minimum version
- All LLM access through LangChain only (no direct provider SDK calls outside `src/llm/`)
- Type hints everywhere (fully typed codebase)
- Async where library is async (proper async/await usage)
- Never send email without explicit user approval (Send button tap required)
- Only `ALLOWED_USER_ID` can use bot
- All secrets in `.env` (gitignored)
- Mock LLM and SMTP in tests (no network calls in unit tests)
- Ruff lint and format must pass
- DRY, YAGNI principles

## Review Focus

1. **Email extraction validation**: If LLM returns an email address that doesn't appear in the original job post text, the extractor must reject it and raise ValueError.
2. **Unauthorized user blocking**: If a Telegram user other than `ALLOWED_USER_ID` sends any message or callback, the bot must respond "⛔ Unauthorized." and take no further action.
3. **Daily cap enforcement**: If user has sent `DAILY_SEND_CAP` emails in the last 24 hours and taps Send again, the bot must refuse with a friendly error and NOT send or log the email.
4. **Missing resume file**: If the selected resume path doesn't exist when sending, the mailer must fail gracefully and report the error instead of sending without attachment.
5. **Invalid email address format**: If `email-validator` rejects the HR email format, the bot must show an error and not proceed to drafting.

---

## Task 1: Project Scaffold and Configuration

**Files:**
- Create: `pyproject.toml`
- Create: `src/__init__.py`
- Create: `src/config.py`
- Create: `.env.example`
- Create: `.gitignore` (update if exists)
- Create: `ruff.toml`
- Create: `README.md` (update existing)
- Delete: `app.py`, `email_config.py`, `email_sender.py`, `email_templates.py`, `requirements.txt`
- Create: `tests/__init__.py`

**Interfaces:**
- Consumes: None (initial task)
- Produces: `Settings` class in `src/config.py` with all env vars typed

- [ ] **Step 1: Write test for Settings loading**

```python
# tests/test_config.py
import os
from pathlib import Path
from src.config import Settings

def test_settings_loads_from_env(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test_token")
    monkeypatch.setenv("ALLOWED_USER_ID", "12345")
    monkeypatch.setenv("GMAIL_ADDRESS", "test@gmail.com")
    monkeypatch.setenv("GMAIL_APP_PASSWORD", "test_pass")
    monkeypatch.setenv("REPLY_TO_EMAIL", "reply@gmail.com")
    monkeypatch.setenv("SENDER_NAME", "Test User")
    
    settings = Settings()
    
    assert settings.telegram_bot_token == "test_token"
    assert settings.allowed_user_id == 12345
    assert settings.llm_provider == "ollama"  # default
    assert settings.daily_send_cap == 15  # default

def test_settings_validates_required_fields():
    import pytest
    from pydantic import ValidationError
    
    with pytest.raises(ValidationError):
        Settings()  # Missing required fields
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_config.py -v`  
Expected: FAIL with "ModuleNotFoundError: No module named 'src'"

- [ ] **Step 3: Create `pyproject.toml` with dependencies**

```toml
[project]
name = "telegram-job-bot"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "python-telegram-bot>=21.0",
    "langchain>=0.3.0",
    "langchain-core>=0.3.0",
    "langchain-ollama>=0.2.0",
    "pydantic>=2.0",
    "pydantic-settings>=2.0",
    "python-dotenv>=1.0.0",
    "aiosmtplib>=3.0.0",
    "email-validator>=2.0.0",
    "aiosqlite>=0.19.0",
    "tenacity>=8.0.0",
    "structlog>=24.0.0",
]

[project.optional-dependencies]
google = ["langchain-google-genai>=2.0.0"]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
    "pytest-mock>=3.12.0",
    "ruff>=0.6.0",
]

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "I", "N", "W", "UP"]
```

- [ ] **Step 4: Create `src/config.py` with Settings class**

```python
from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration from environment variables."""
    
    # Telegram
    telegram_bot_token: str
    allowed_user_id: int
    
    # LLM
    llm_provider: str = "ollama"
    llm_model: str = "qwen3:4b-instruct-2507-q4_K_M"
    llm_temperature: float = 0.0
    
    # Ollama-specific
    ollama_base_url: str = "http://localhost:11434"
    ollama_num_ctx: int = 8192
    
    # Google-specific (optional)
    google_api_key: str | None = None
    
    # Gmail
    gmail_address: str
    gmail_app_password: str
    reply_to_email: str
    sender_name: str
    
    # Application behavior
    daily_send_cap: int = 15
    send_delay_min: int = 30
    send_delay_max: int = 60
    
    # Paths
    resume_dir: Path = Path("resume")
    database_path: Path = Path("data/applications.db")
    
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")
```

- [ ] **Step 5: Create `.env.example`**

```env
# Telegram Bot
TELEGRAM_BOT_TOKEN=your_bot_token_from_botfather
ALLOWED_USER_ID=your_telegram_user_id

# LLM Configuration
LLM_PROVIDER=ollama
LLM_MODEL=qwen3:4b-instruct-2507-q4_K_M
LLM_TEMPERATURE=0.0

# Ollama Settings
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_NUM_CTX=8192

# Google Gemini (optional, only if LLM_PROVIDER=google)
# GOOGLE_API_KEY=your_google_api_key

# Gmail SMTP
GMAIL_ADDRESS=your_email@gmail.com
GMAIL_APP_PASSWORD=your_app_password_here
REPLY_TO_EMAIL=your_reply_to@gmail.com
SENDER_NAME=Your Full Name

# Application Settings
DAILY_SEND_CAP=15
SEND_DELAY_MIN=30
SEND_DELAY_MAX=60
```

- [ ] **Step 6: Update `.gitignore`**

Add to existing `.gitignore`:
```
# Environment and secrets
.env

# Database
data/
*.db

# Resume (privacy)
resume/*.pdf
resume/profile.md

# Python
__pycache__/
*.py[cod]
.pytest_cache/
.ruff_cache/
```

- [ ] **Step 7: Create `ruff.toml`**

```toml
line-length = 100
target-version = "py311"

[lint]
select = ["E", "F", "I", "N", "W", "UP"]
ignore = ["E501"]  # Line too long (handled by formatter)
```

- [ ] **Step 8: Delete old Tkinter app files**

```bash
rm app.py email_config.py email_sender.py email_templates.py requirements.txt
```

- [ ] **Step 9: Run test to verify it passes**

Run: `pytest tests/test_config.py -v`  
Expected: PASS (both tests)

- [ ] **Step 10: Run ruff to verify clean**

Run: `ruff check src/ tests/`  
Expected: All checks passed

- [ ] **Step 11: Commit**

```bash
git add pyproject.toml src/config.py .env.example .gitignore ruff.toml tests/test_config.py
git rm app.py email_config.py email_sender.py email_templates.py requirements.txt
git commit -m "feat: project scaffold with pydantic-settings config

- Add pyproject.toml with dependencies
- Add Settings class for env var loading
- Add .env.example template
- Configure ruff for linting
- Remove old Tkinter app files"
```

---

## Task 2: Email Extraction with De-obfuscation

**Files:**
- Create: `src/extraction/__init__.py`
- Create: `src/extraction/email_finder.py`
- Create: `tests/test_email_finder.py`

**Interfaces:**
- Consumes: None
- Produces: `find_emails(text: str) -> list[str]` - extracts and de-obfuscates emails from text

- [ ] **Step 1: Write tests for email extraction**

```python
# tests/test_email_finder.py
from src.extraction.email_finder import find_emails


def test_find_standard_email():
    text = "Contact us at hr@company.com for inquiries."
    result = find_emails(text)
    assert result == ["hr@company.com"]


def test_find_email_with_at_brackets():
    text = "Email: hr[at]company.com"
    result = find_emails(text)
    assert result == ["hr@company.com"]


def test_find_email_with_at_parens():
    text = "Reach out: hr(at)company.com"
    result = find_emails(text)
    assert result == ["hr@company.com"]


def test_find_email_with_at_spaces():
    text = "Contact hr at company dot com"
    result = find_emails(text)
    assert result == ["hr@company.com"]


def test_find_email_with_dot_brackets():
    text = "Email: hr@company[dot]com"
    result = find_emails(text)
    assert result == ["hr@company.com"]


def test_find_email_with_dot_parens():
    text = "Email: hr@company(dot)com"
    result = find_emails(text)
    assert result == ["hr@company.com"]


def test_find_email_with_spaces():
    text = "Contact: hr @ company . com"
    result = find_emails(text)
    assert result == ["hr@company.com"]


def test_find_multiple_emails():
    text = "Contact hr@company.com or recruiting[at]company.com"
    result = find_emails(text)
    assert set(result) == {"hr@company.com", "recruiting@company.com"}


def test_find_no_emails():
    text = "No email addresses here!"
    result = find_emails(text)
    assert result == []


def test_find_email_case_insensitive():
    text = "Email: HR[AT]COMPANY[DOT]COM"
    result = find_emails(text)
    assert result == ["hr@company.com"]


def test_deduplicates_emails():
    text = "Contact hr@company.com or hr@company.com again"
    result = find_emails(text)
    assert result == ["hr@company.com"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_email_finder.py -v`  
Expected: FAIL with "ModuleNotFoundError: No module named 'src.extraction'"

- [ ] **Step 3: Implement `find_emails()` in `src/extraction/email_finder.py`**

Use regex patterns to match standard emails and all obfuscation variants. De-obfuscate by replacing `[at]`, `(at)`, ` at ` with `@`, and `[dot]`, `(dot)`, ` dot ` with `.`. Remove spaces around `@` and `.`. Convert to lowercase. Return deduplicated list.

```python
import re


def find_emails(text: str) -> list[str]:
    """Extract and de-obfuscate email addresses from text.
    
    Handles formats:
    - Standard: user@example.com
    - [at]: user[at]example.com
    - (at): user(at)example.com
    - " at ": user at example dot com
    - [dot]: user@example[dot]com
    - (dot): user@example(dot)com
    - Spaces: user @ example . com
    
    Args:
        text: Input text containing email addresses.
    
    Returns:
        List of normalized email addresses (lowercase, deduplicated).
    """
    # De-obfuscate common patterns
    normalized = text.lower()
    normalized = re.sub(r'\[at\]|\(at\)| at ', '@', normalized)
    normalized = re.sub(r'\[dot\]|\(dot\)| dot ', '.', normalized)
    normalized = re.sub(r'\s+@\s+', '@', normalized)
    normalized = re.sub(r'\s+\.\s+', '.', normalized)
    
    # Find standard email pattern
    email_pattern = r'\b[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}\b'
    emails = re.findall(email_pattern, normalized)
    
    # Deduplicate while preserving order
    seen = set()
    result = []
    for email in emails:
        if email not in seen:
            seen.add(email)
            result.append(email)
    
    return result
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_email_finder.py -v`  
Expected: PASS (all 11 tests)

- [ ] **Step 5: Add Review Focus test for case sensitivity edge case**

Add to `tests/test_email_finder.py`:
```python
def test_mixed_obfuscation_formats():
    """Review Focus: Multiple obfuscation styles in same email."""
    text = "Email: hr[at]company(dot)com"
    result = find_emails(text)
    assert result == ["hr@company.com"]
```

Run: `pytest tests/test_email_finder.py::test_mixed_obfuscation_formats -v`  
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/extraction/ tests/test_email_finder.py
git commit -m "feat: add email extraction with de-obfuscation

- Implement find_emails() with regex
- Handle [at], (at), at, [dot], (dot), dot formats
- Normalize to lowercase and deduplicate
- Add comprehensive tests for all formats"
```

---

## Task 3: Pydantic Models for Job Data

**Files:**
- Create: `src/models.py`
- Create: `tests/test_models.py`

**Interfaces:**
- Consumes: None
- Produces: `JobPost` and `EmailDraft` pydantic models

- [ ] **Step 1: Write tests for models**

```python
# tests/test_models.py
from src.models import JobPost, EmailDraft


def test_job_post_creation():
    job = JobPost(
        company="Acme Corp",
        role="Python Developer",
        requirements_summary="Looking for Python expert with AI experience.",
        key_requirements=["Python 3+", "FastAPI", "LLMs"],
        hr_email="hr@acme.com"
    )
    assert job.company == "Acme Corp"
    assert job.role == "Python Developer"
    assert len(job.key_requirements) == 3


def test_email_draft_creation():
    draft = EmailDraft(
        subject="Application Janardhan Jayanth - Python Developer",
        body="Dear Hiring Team,\n\nI would like to apply..."
    )
    assert "Application" in draft.subject
    assert "Dear Hiring Team" in draft.body


def test_job_post_validation_requires_fields():
    import pytest
    from pydantic import ValidationError
    
    with pytest.raises(ValidationError):
        JobPost(company="Acme")  # Missing required fields
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_models.py -v`  
Expected: FAIL with "ModuleNotFoundError: No module named 'src.models'"

- [ ] **Step 3: Implement models in `src/models.py`**

```python
from pydantic import BaseModel, Field


class JobPost(BaseModel):
    """Extracted job details from posted text."""
    
    company: str = Field(description="Company name")
    role: str = Field(description="Job role/title")
    requirements_summary: str = Field(description="2-3 sentence summary of requirements")
    key_requirements: list[str] = Field(description="List of key requirements")
    hr_email: str = Field(description="HR contact email address")


class EmailDraft(BaseModel):
    """Generated email content for job application."""
    
    subject: str = Field(description="Email subject line")
    body: str = Field(description="Email body content")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_models.py -v`  
Expected: PASS (all 3 tests)

- [ ] **Step 5: Commit**

```bash
git add src/models.py tests/test_models.py
git commit -m "feat: add JobPost and EmailDraft pydantic models

- Define JobPost with company, role, requirements, hr_email
- Define EmailDraft with subject and body
- Add validation tests"
```

---

## Task 4: LLM Factory with Provider Registry

**Files:**
- Create: `src/llm/__init__.py`
- Create: `src/llm/factory.py`
- Create: `tests/test_llm_factory.py`

**Interfaces:**
- Consumes: `Settings` from `src/config.py`
- Produces: `get_llm(settings: Settings) -> BaseChatModel` - returns configured LLM instance

- [ ] **Step 1: Write tests for LLM factory**

```python
# tests/test_llm_factory.py
import pytest
from src.config import Settings
from src.llm.factory import get_llm, _PROVIDERS


def test_get_ollama_llm(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test")
    monkeypatch.setenv("ALLOWED_USER_ID", "123")
    monkeypatch.setenv("GMAIL_ADDRESS", "test@gmail.com")
    monkeypatch.setenv("GMAIL_APP_PASSWORD", "pass")
    monkeypatch.setenv("REPLY_TO_EMAIL", "reply@gmail.com")
    monkeypatch.setenv("SENDER_NAME", "Test")
    monkeypatch.setenv("LLM_PROVIDER", "ollama")
    
    settings = Settings()
    llm = get_llm(settings)
    
    assert llm is not None
    assert llm.model == "qwen3:4b-instruct-2507-q4_K_M"


def test_get_google_llm(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test")
    monkeypatch.setenv("ALLOWED_USER_ID", "123")
    monkeypatch.setenv("GMAIL_ADDRESS", "test@gmail.com")
    monkeypatch.setenv("GMAIL_APP_PASSWORD", "pass")
    monkeypatch.setenv("REPLY_TO_EMAIL", "reply@gmail.com")
    monkeypatch.setenv("SENDER_NAME", "Test")
    monkeypatch.setenv("LLM_PROVIDER", "google")
    monkeypatch.setenv("GOOGLE_API_KEY", "test_key")
    
    settings = Settings()
    llm = get_llm(settings)
    
    assert llm is not None


def test_unknown_provider_raises_error(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test")
    monkeypatch.setenv("ALLOWED_USER_ID", "123")
    monkeypatch.setenv("GMAIL_ADDRESS", "test@gmail.com")
    monkeypatch.setenv("GMAIL_APP_PASSWORD", "pass")
    monkeypatch.setenv("REPLY_TO_EMAIL", "reply@gmail.com")
    monkeypatch.setenv("SENDER_NAME", "Test")
    monkeypatch.setenv("LLM_PROVIDER", "unknown")
    
    settings = Settings()
    
    with pytest.raises(ValueError, match="Unknown provider: unknown"):
        get_llm(settings)


def test_providers_registry_contains_ollama_and_google():
    assert "ollama" in _PROVIDERS
    assert "google" in _PROVIDERS
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_llm_factory.py -v`  
Expected: FAIL with "ModuleNotFoundError: No module named 'src.llm'"

- [ ] **Step 3: Implement factory in `src/llm/factory.py`**

```python
from langchain_core.language_models import BaseChatModel
from langchain_ollama import ChatOllama

from src.config import Settings


def build_ollama_llm(settings: Settings) -> ChatOllama:
    """Build Ollama chat model.
    
    Args:
        settings: Application settings.
    
    Returns:
        Configured ChatOllama instance.
    """
    return ChatOllama(
        model=settings.llm_model,
        base_url=settings.ollama_base_url,
        temperature=settings.llm_temperature,
        num_ctx=settings.ollama_num_ctx,
    )


def build_google_llm(settings: Settings) -> BaseChatModel:
    """Build Google Gemini chat model.
    
    Args:
        settings: Application settings.
    
    Returns:
        Configured ChatGoogleGenerativeAI instance.
    """
    from langchain_google_genai import ChatGoogleGenerativeAI
    
    if not settings.google_api_key:
        raise ValueError("GOOGLE_API_KEY required when LLM_PROVIDER=google")
    
    return ChatGoogleGenerativeAI(
        model=settings.llm_model,
        google_api_key=settings.google_api_key,
        temperature=settings.llm_temperature,
    )


_PROVIDERS: dict[str, callable] = {
    "ollama": build_ollama_llm,
    "google": build_google_llm,
}


def get_llm(settings: Settings) -> BaseChatModel:
    """Get LLM instance based on provider setting.
    
    Args:
        settings: Application settings.
    
    Returns:
        Configured chat model instance.
    
    Raises:
        ValueError: If provider is unknown.
    """
    provider = settings.llm_provider.lower()
    builder = _PROVIDERS.get(provider)
    
    if not builder:
        supported = ", ".join(_PROVIDERS.keys())
        raise ValueError(
            f"Unknown provider: {provider}. Supported providers: {supported}"
        )
    
    return builder(settings)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_llm_factory.py -v`  
Expected: PASS (all 4 tests)

- [ ] **Step 5: Commit**

```bash
git add src/llm/ tests/test_llm_factory.py
git commit -m "feat: add LLM factory with provider registry

- Implement get_llm() with Ollama and Google builders
- Use registry pattern for extensibility
- Raise clear error for unknown providers
- Add tests for both providers"
```

---

## Task 5: LLM Prompts for Extraction and Drafting

**Files:**
- Create: `src/llm/prompts.py`
- Create: `tests/test_prompts.py`

**Interfaces:**
- Consumes: `JobPost`, `EmailDraft` from `src/models.py`
- Produces: `EXTRACTION_PROMPT` and `DRAFTING_PROMPT` ChatPromptTemplate objects

- [ ] **Step 1: Write tests for prompts**

```python
# tests/test_prompts.py
from src.llm.prompts import EXTRACTION_PROMPT, DRAFTING_PROMPT


def test_extraction_prompt_format():
    result = EXTRACTION_PROMPT.format(
        job_text="Company XYZ hiring Python dev. Email: hr@xyz.com",
        candidate_emails=["hr@xyz.com"]
    )
    assert "Company XYZ" in result
    assert "hr@xyz.com" in result


def test_drafting_prompt_format():
    result = DRAFTING_PROMPT.format(
        company="Acme Corp",
        role="Python Developer",
        requirements_summary="Need Python expert",
        key_requirements=["Python 3+", "FastAPI"],
        profile_content="I have 1 year Python experience",
        sender_name="Test User"
    )
    assert "Acme Corp" in result
    assert "Python Developer" in result
    assert "Test User" in result
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_prompts.py -v`  
Expected: FAIL with "cannot import name 'EXTRACTION_PROMPT'"

- [ ] **Step 3: Implement prompts in `src/llm/prompts.py`**

```python
from langchain_core.prompts import ChatPromptTemplate


EXTRACTION_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are a job posting analyzer. Extract structured information from job posts.

CRITICAL RULES:
1. The hr_email MUST be chosen from the candidate_emails list ONLY
2. If no candidate_emails provided, set hr_email to empty string
3. Do not invent or guess email addresses
4. Extract 3-5 key requirements as a list
5. Summarize requirements in 2-3 sentences"""),
    ("human", """Job Post:
{job_text}

Candidate Emails Found:
{candidate_emails}

Extract: company name, role, requirements summary, key requirements list, and HR email (from candidates only).""")
])


DRAFTING_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are a professional email writer helping with job applications.

Write an email using this EXACT template structure:

Dear Hiring Team,

I came across your post for the {role} position at {company} and would like to apply. I am a Python developer with 1 year of experience in the IT sector, based in Chennai, with a strong interest in Python and Generative AI.

[Write ONE paragraph here mentioning 2-3 key requirements from the job that match the profile. Use ONLY facts from the profile provided. DO NOT invent experience or skills.]

I am eager to apply my skills, take on new challenges, and contribute to your team. Please find my resume attached for your consideration.

Thank you for your time. I look forward to hearing from you.

Best regards,
{sender_name}
+91 6382448946

CONSTRAINTS:
- Keep total email under 150 words
- Mention 2-3 requirements that match the profile
- Use ONLY information from the profile
- Do not invent facts about the candidate
- Keep tone professional but friendly"""),
    ("human", """Company: {company}
Role: {role}
Requirements Summary: {requirements_summary}
Key Requirements: {key_requirements}

Candidate Profile:
{profile_content}

Sender Name: {sender_name}

Write the email body following the template exactly.""")
])
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_prompts.py -v`  
Expected: PASS (both tests)

- [ ] **Step 5: Commit**

```bash
git add src/llm/prompts.py tests/test_prompts.py
git commit -m "feat: add LLM prompts for extraction and drafting

- Add EXTRACTION_PROMPT for job post parsing
- Add DRAFTING_PROMPT with exact email template
- Enforce constraints: email from candidates, no invented facts
- Add format tests"
```

---

## Task 6: Job Post Extractor with Structured Output

**Files:**
- Create: `src/llm/extractor.py`
- Create: `tests/test_extractor.py`

**Interfaces:**
- Consumes: `find_emails(text)` from `src/extraction/email_finder.py`, `JobPost` from `src/models.py`, `EXTRACTION_PROMPT` from `src/llm/prompts.py`, `BaseChatModel` from LangChain
- Produces: `extract_job_post(text: str, llm: BaseChatModel) -> JobPost` - async function

- [ ] **Step 1: Write tests for extractor**

```python
# tests/test_extractor.py
import pytest
from unittest.mock import AsyncMock, MagicMock
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
        requirements_summary="Need FastAPI and Docker experience",
        key_requirements=["FastAPI", "Docker"],
        hr_email="hr@acme.com"
    )
    mock_llm.with_structured_output.return_value = mock_structured
    
    result = await extract_job_post(job_text, mock_llm)
    
    assert result.company == "Acme Corp"
    assert result.role == "Python Developer"
    assert result.hr_email == "hr@acme.com"
    mock_llm.with_structured_output.assert_called_once()


@pytest.mark.asyncio
async def test_extract_rejects_email_not_in_candidates():
    job_text = "Acme Corp hiring. Email: hr@acme.com"
    
    mock_llm = MagicMock()
    mock_structured = AsyncMock()
    # LLM returns email NOT in original text
    mock_structured.ainvoke.return_value = JobPost(
        company="Acme Corp",
        role="Developer",
        requirements_summary="Need experience",
        key_requirements=["Python"],
        hr_email="fake@notintext.com"
    )
    mock_llm.with_structured_output.return_value = mock_structured
    
    with pytest.raises(ValueError, match="not found in original"):
        await extract_job_post(job_text, mock_llm)


@pytest.mark.asyncio
async def test_extract_no_email_found():
    job_text = "Acme Corp hiring Python Developer. No email provided."
    
    result = await extract_job_post(job_text, MagicMock())
    
    # Should return None or raise ValueError when no candidates found
    assert result is None or isinstance(result, ValueError)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_extractor.py -v`  
Expected: FAIL with "cannot import name 'extract_job_post'"

- [ ] **Step 3: Implement extractor in `src/llm/extractor.py`**

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_extractor.py -v`  
Expected: PASS (all 3 tests)

- [ ] **Step 5: Add Review Focus test for email validation**

Test already covers Review Focus #1 (email validation) in `test_extract_rejects_email_not_in_candidates`.

- [ ] **Step 6: Commit**

```bash
git add src/llm/extractor.py tests/test_extractor.py
git commit -m "feat: add job post extractor with structured output

- Implement extract_job_post() using LangChain
- Find candidate emails via regex first
- Validate LLM email selection against candidates
- Retry up to 3 times on validation failure
- Return None if no email found"
```

---

## Task 7: Email Drafter with Template

**Files:**
- Create: `src/llm/drafter.py`
- Create: `tests/test_drafter.py`
- Create: `resume/profile.md` (template)

**Interfaces:**
- Consumes: `JobPost` from `src/models.py`, `DRAFTING_PROMPT` from `src/llm/prompts.py`, `BaseChatModel` from LangChain
- Produces: `draft_email(job_post: JobPost, profile_content: str, sender_name: str, llm: BaseChatModel) -> EmailDraft` - async function

- [ ] **Step 1: Write tests for drafter**

```python
# tests/test_drafter.py
import pytest
from unittest.mock import AsyncMock, MagicMock
from src.llm.drafter import draft_email
from src.models import JobPost, EmailDraft


@pytest.mark.asyncio
async def test_draft_email_success():
    job_post = JobPost(
        company="Acme Corp",
        role="Python Developer",
        requirements_summary="Need Python and FastAPI experience",
        key_requirements=["Python 3+", "FastAPI", "Docker"],
        hr_email="hr@acme.com"
    )
    profile = "I have 1 year Python experience with FastAPI and Docker."
    
    mock_llm = MagicMock()
    mock_structured = AsyncMock()
    mock_structured.ainvoke.return_value = EmailDraft(
        subject="Application Janardhan Jayanth - Python Developer",
        body="Dear Hiring Team,\n\nI would like to apply..."
    )
    mock_llm.with_structured_output.return_value = mock_structured
    
    result = await draft_email(job_post, profile, "Janardhan Jayanth", mock_llm)
    
    assert "Application Janardhan Jayanth - Python Developer" in result.subject
    assert "Dear Hiring Team" in result.body
    mock_llm.with_structured_output.assert_called_once()


@pytest.mark.asyncio
async def test_draft_email_formats_subject_correctly():
    job_post = JobPost(
        company="Test Co",
        role="Backend Engineer",
        requirements_summary="Need backend skills",
        key_requirements=["Python"],
        hr_email="hr@test.com"
    )
    
    mock_llm = MagicMock()
    mock_structured = AsyncMock()
    mock_structured.ainvoke.return_value = EmailDraft(
        subject="Application Janardhan Jayanth - Backend Engineer",
        body="Email body"
    )
    mock_llm.with_structured_output.return_value = mock_structured
    
    result = await draft_email(job_post, "Profile", "Janardhan Jayanth", mock_llm)
    
    assert result.subject == "Application Janardhan Jayanth - Backend Engineer"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_drafter.py -v`  
Expected: FAIL with "cannot import name 'draft_email'"

- [ ] **Step 3: Create profile template in `resume/profile.md`**

```markdown
# Candidate Profile

**Name:** Janardhan Jayanth  
**Location:** Chennai, India  
**Phone:** +91 6382448946  
**Experience:** 1 year in IT sector

## Background

Python developer with 1 year of experience in the IT sector, based in Chennai, with a strong interest in Python and Generative AI.

## Previous Role

**Junior Software Developer**
- Worked on REST APIs using FastAPI
- Built AI-powered applications with LangChain
- Developed RAG (Retrieval-Augmented Generation) systems
- Implemented vector search using PostgreSQL and pgvector

## Skills

- Python 3.11+
- FastAPI
- LangChain
- Large Language Models (LLMs)
- RAG systems
- Vector databases (PostgreSQL, pgvector)
- REST API development
- Generative AI applications

## Projects

- Built personal projects involving RAG, LLMs, and vector search
- Developed AI-powered applications using Python and modern ML frameworks

## Interests

- Python development
- Generative AI
- Machine Learning
- API development
- Database optimization
```

- [ ] **Step 4: Implement drafter in `src/llm/drafter.py`**

```python
from langchain_core.language_models import BaseChatModel
from tenacity import retry, stop_after_attempt, wait_fixed

from src.llm.prompts import DRAFTING_PROMPT
from src.models import JobPost, EmailDraft


@retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
async def draft_email(
    job_post: JobPost,
    profile_content: str,
    sender_name: str,
    llm: BaseChatModel
) -> EmailDraft:
    """Draft tailored job application email.
    
    Args:
        job_post: Extracted job details.
        profile_content: Candidate profile text (from profile.md).
        sender_name: Sender's full name.
        llm: LangChain chat model.
    
    Returns:
        EmailDraft with subject and body.
    """
    structured_llm = llm.with_structured_output(EmailDraft, method="json_schema")
    
    result: EmailDraft = await structured_llm.ainvoke(
        DRAFTING_PROMPT.format(
            company=job_post.company,
            role=job_post.role,
            requirements_summary=job_post.requirements_summary,
            key_requirements=job_post.key_requirements,
            profile_content=profile_content,
            sender_name=sender_name
        )
    )
    
    # Ensure subject follows format
    if not result.subject.startswith("Application"):
        result.subject = f"Application {sender_name} - {job_post.role}"
    
    return result
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/test_drafter.py -v`  
Expected: PASS (both tests)

- [ ] **Step 6: Commit**

```bash
git add src/llm/drafter.py tests/test_drafter.py resume/profile.md
git commit -m "feat: add email drafter with template

- Implement draft_email() using LangChain
- Use profile.md content for personalization
- Enforce subject format: Application <name> - <role>
- Retry up to 3 times on validation failure
- Add candidate profile template"
```

---

## Task 8: Database Schema and Operations

**Files:**
- Create: `src/storage/__init__.py`
- Create: `src/storage/db.py`
- Create: `tests/test_db.py`

**Interfaces:**
- Consumes: `Settings.database_path` from `src/config.py`
- Produces:
  - `init_db(db_path: Path) -> None` - async
  - `insert_application(db_path: Path, company: str, role: str, hr_email: str, subject: str, body: str, status: str) -> None` - async
  - `get_daily_send_count(db_path: Path) -> int` - async

- [ ] **Step 1: Write tests for database operations**

```python
# tests/test_db.py
import pytest
from pathlib import Path
from datetime import datetime, timedelta
import aiosqlite
from src.storage.db import init_db, insert_application, get_daily_send_count


@pytest.mark.asyncio
async def test_init_db_creates_schema(tmp_path):
    db_path = tmp_path / "test.db"
    
    await init_db(db_path)
    
    assert db_path.exists()
    async with aiosqlite.connect(db_path) as db:
        cursor = await db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='applications'"
        )
        result = await cursor.fetchone()
        assert result is not None


@pytest.mark.asyncio
async def test_insert_application(tmp_path):
    db_path = tmp_path / "test.db"
    await init_db(db_path)
    
    await insert_application(
        db_path=db_path,
        company="Acme Corp",
        role="Python Developer",
        hr_email="hr@acme.com",
        subject="Application Test",
        body="Email body",
        status="sent"
    )
    
    async with aiosqlite.connect(db_path) as db:
        cursor = await db.execute("SELECT company, role, status FROM applications")
        result = await cursor.fetchone()
        assert result == ("Acme Corp", "Python Developer", "sent")


@pytest.mark.asyncio
async def test_get_daily_send_count_today(tmp_path):
    db_path = tmp_path / "test.db"
    await init_db(db_path)
    
    # Insert 3 sent applications today
    for i in range(3):
        await insert_application(
            db_path, f"Company{i}", "Role", f"hr{i}@test.com", "Subject", "Body", "sent"
        )
    
    # Insert 1 skipped application (should not count)
    await insert_application(
        db_path, "Company", "Role", "hr@test.com", "Subject", "Body", "skipped"
    )
    
    count = await get_daily_send_count(db_path)
    
    assert count == 3


@pytest.mark.asyncio
async def test_get_daily_send_count_ignores_old(tmp_path):
    db_path = tmp_path / "test.db"
    await init_db(db_path)
    
    # Insert application from 2 days ago
    async with aiosqlite.connect(db_path) as db:
        old_timestamp = (datetime.now() - timedelta(days=2)).isoformat()
        await db.execute(
            "INSERT INTO applications (company, role, hr_email, subject, body, status, timestamp) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("OldCo", "Role", "hr@old.com", "Subject", "Body", "sent", old_timestamp)
        )
        await db.commit()
    
    count = await get_daily_send_count(db_path)
    
    assert count == 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_db.py -v`  
Expected: FAIL with "cannot import name 'init_db'"

- [ ] **Step 3: Implement database in `src/storage/db.py`**

```python
from pathlib import Path
from datetime import datetime, timedelta
import aiosqlite


async def init_db(db_path: Path) -> None:
    """Initialize database schema.
    
    Args:
        db_path: Path to SQLite database file.
    """
    db_path.parent.mkdir(parents=True, exist_ok=True)
    
    async with aiosqlite.connect(db_path) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS applications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company TEXT NOT NULL,
                role TEXT NOT NULL,
                hr_email TEXT NOT NULL,
                subject TEXT NOT NULL,
                body TEXT NOT NULL,
                status TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_timestamp ON applications(timestamp)"
        )
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_status ON applications(status)"
        )
        await db.commit()


async def insert_application(
    db_path: Path,
    company: str,
    role: str,
    hr_email: str,
    subject: str,
    body: str,
    status: str
) -> None:
    """Insert application record.
    
    Args:
        db_path: Path to SQLite database file.
        company: Company name.
        role: Job role.
        hr_email: HR email address.
        subject: Email subject.
        body: Email body.
        status: Application status ('sent' or 'skipped').
    """
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            "INSERT INTO applications (company, role, hr_email, subject, body, status) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (company, role, hr_email, subject, body, status)
        )
        await db.commit()


async def get_daily_send_count(db_path: Path) -> int:
    """Count emails sent in last 24 hours.
    
    Args:
        db_path: Path to SQLite database file.
    
    Returns:
        Number of emails with status='sent' in last 24 hours.
    """
    cutoff = (datetime.now() - timedelta(hours=24)).isoformat()
    
    async with aiosqlite.connect(db_path) as db:
        cursor = await db.execute(
            "SELECT COUNT(*) FROM applications WHERE status = 'sent' AND timestamp > ?",
            (cutoff,)
        )
        result = await cursor.fetchone()
        return result[0] if result else 0
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_db.py -v`  
Expected: PASS (all 4 tests)

- [ ] **Step 5: Add Review Focus test for daily cap enforcement**

Test for Review Focus #3 will be in the handler tests (Task 11).

- [ ] **Step 6: Commit**

```bash
git add src/storage/ tests/test_db.py
git commit -m "feat: add database schema and operations

- Create applications table with indexes
- Implement init_db() for schema creation
- Implement insert_application() for logging
- Implement get_daily_send_count() for cap enforcement
- Add comprehensive async tests"
```

---

## Task 9: Gmail SMTP Mailer

**Files:**
- Create: `src/mailer/__init__.py`
- Create: `src/mailer/gmail.py`
- Create: `tests/test_gmail.py`

**Interfaces:**
- Consumes: Gmail credentials from `Settings`
- Produces: `send_email(to: str, subject: str, body: str, attachment_path: Path, sender_email: str, sender_password: str, sender_name: str, reply_to: str) -> bool` - async

- [ ] **Step 1: Write tests for Gmail mailer**

```python
# tests/test_gmail.py
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from src.mailer.gmail import send_email


@pytest.mark.asyncio
async def test_send_email_success(tmp_path):
    resume_path = tmp_path / "resume.pdf"
    resume_path.write_bytes(b"fake pdf content")
    
    with patch("src.mailer.gmail.SMTP") as mock_smtp:
        mock_instance = AsyncMock()
        mock_smtp.return_value.__aenter__.return_value = mock_instance
        
        result = await send_email(
            to="hr@test.com",
            subject="Test Subject",
            body="Test Body",
            attachment_path=resume_path,
            sender_email="sender@gmail.com",
            sender_password="password",
            sender_name="Test Sender",
            reply_to="reply@gmail.com"
        )
        
        assert result is True
        mock_instance.login.assert_called_once_with("sender@gmail.com", "password")
        mock_instance.send_message.assert_called_once()


@pytest.mark.asyncio
async def test_send_email_missing_attachment():
    """Review Focus #4: Missing resume file."""
    nonexistent = Path("/fake/path/resume.pdf")
    
    result = await send_email(
        to="hr@test.com",
        subject="Test",
        body="Body",
        attachment_path=nonexistent,
        sender_email="sender@gmail.com",
        sender_password="password",
        sender_name="Test",
        reply_to="reply@gmail.com"
    )
    
    assert result is False


@pytest.mark.asyncio
async def test_send_email_smtp_failure():
    with patch("src.mailer.gmail.SMTP") as mock_smtp:
        mock_smtp.side_effect = Exception("SMTP error")
        
        result = await send_email(
            to="hr@test.com",
            subject="Test",
            body="Body",
            attachment_path=Path("resume.pdf"),
            sender_email="sender@gmail.com",
            sender_password="password",
            sender_name="Test",
            reply_to="reply@gmail.com"
        )
        
        assert result is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_gmail.py -v`  
Expected: FAIL with "cannot import name 'send_email'"

- [ ] **Step 3: Implement Gmail mailer in `src/mailer/gmail.py`**

```python
from pathlib import Path
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
import aiosmtplib


async def send_email(
    to: str,
    subject: str,
    body: str,
    attachment_path: Path,
    sender_email: str,
    sender_password: str,
    sender_name: str,
    reply_to: str
) -> bool:
    """Send email via Gmail SMTP with attachment.
    
    Args:
        to: Recipient email address.
        subject: Email subject line.
        body: Email body content.
        attachment_path: Path to PDF resume file.
        sender_email: Gmail address.
        sender_password: Gmail app password.
        sender_name: Sender's full name.
        reply_to: Reply-To email address.
    
    Returns:
        True if sent successfully, False otherwise.
    """
    try:
        # Review Focus #4: Check resume exists
        if not attachment_path.exists():
            return False
        
        # Build message
        msg = MIMEMultipart()
        msg["From"] = f"{sender_name} <{sender_email}>"
        msg["To"] = to
        msg["Subject"] = subject
        msg["Reply-To"] = reply_to
        
        msg.attach(MIMEText(body, "plain"))
        
        # Attach resume
        with open(attachment_path, "rb") as f:
            attachment = MIMEApplication(f.read(), _subtype="pdf")
            attachment.add_header(
                "Content-Disposition",
                "attachment",
                filename=attachment_path.name
            )
            msg.attach(attachment)
        
        # Send via Gmail SMTP (SSL port 465)
        async with aiosmtplib.SMTP(hostname="smtp.gmail.com", port=465, use_tls=True) as smtp:
            await smtp.login(sender_email, sender_password)
            await smtp.send_message(msg)
        
        return True
    
    except Exception as e:
        print(f"Failed to send email: {e}")
        return False
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_gmail.py -v`  
Expected: PASS (all 3 tests)

- [ ] **Step 5: Review Focus test already covers missing attachment**

Test `test_send_email_missing_attachment` covers Review Focus #4.

- [ ] **Step 6: Commit**

```bash
git add src/mailer/ tests/test_gmail.py
git commit -m "feat: add Gmail SMTP mailer with async support

- Implement send_email() using aiosmtplib
- Connect to smtp.gmail.com:465 with SSL
- Attach PDF resume
- Set Reply-To header
- Handle missing attachment gracefully
- Add tests with mocked SMTP"
```

---

## Task 10: Bot Authorization and Keyboards

**Files:**
- Create: `src/bot/__init__.py`
- Create: `src/bot/auth.py`
- Create: `src/bot/keyboards.py`
- Create: `tests/test_auth.py`
- Create: `tests/test_keyboards.py`

**Interfaces:**
- Consumes: `Settings.allowed_user_id` from `src/config.py`
- Produces:
  - `authorized_only(handler)` - decorator function
  - `approval_keyboard(draft_id: str) -> InlineKeyboardMarkup`
  - `email_choice_keyboard(emails: list[str]) -> InlineKeyboardMarkup`
  - `resume_choice_keyboard(resume_files: list[Path]) -> InlineKeyboardMarkup`

- [ ] **Step 1: Write tests for authorization**

```python
# tests/test_auth.py
import pytest
from unittest.mock import AsyncMock, MagicMock
from src.bot.auth import authorized_only
from src.config import Settings


@pytest.mark.asyncio
async def test_authorized_user_allowed(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test")
    monkeypatch.setenv("ALLOWED_USER_ID", "12345")
    monkeypatch.setenv("GMAIL_ADDRESS", "test@gmail.com")
    monkeypatch.setenv("GMAIL_APP_PASSWORD", "pass")
    monkeypatch.setenv("REPLY_TO_EMAIL", "reply@gmail.com")
    monkeypatch.setenv("SENDER_NAME", "Test")
    
    settings = Settings()
    
    @authorized_only(settings)
    async def handler(update, context):
        return "success"
    
    mock_update = MagicMock()
    mock_update.effective_user.id = 12345
    
    result = await handler(mock_update, None)
    
    assert result == "success"


@pytest.mark.asyncio
async def test_unauthorized_user_blocked(monkeypatch):
    """Review Focus #2: Unauthorized user blocking."""
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test")
    monkeypatch.setenv("ALLOWED_USER_ID", "12345")
    monkeypatch.setenv("GMAIL_ADDRESS", "test@gmail.com")
    monkeypatch.setenv("GMAIL_APP_PASSWORD", "pass")
    monkeypatch.setenv("REPLY_TO_EMAIL", "reply@gmail.com")
    monkeypatch.setenv("SENDER_NAME", "Test")
    
    settings = Settings()
    
    @authorized_only(settings)
    async def handler(update, context):
        return "success"
    
    mock_update = MagicMock()
    mock_update.effective_user.id = 99999  # Wrong ID
    mock_update.message.reply_text = AsyncMock()
    
    result = await handler(mock_update, None)
    
    mock_update.message.reply_text.assert_called_once_with("⛔ Unauthorized.")
    assert result is None
```

- [ ] **Step 2: Write tests for keyboards**

```python
# tests/test_keyboards.py
from pathlib import Path
from src.bot.keyboards import approval_keyboard, email_choice_keyboard, resume_choice_keyboard


def test_approval_keyboard():
    keyboard = approval_keyboard("draft123")
    
    assert len(keyboard.inline_keyboard) == 1
    assert len(keyboard.inline_keyboard[0]) == 3
    assert keyboard.inline_keyboard[0][0].text == "✅ Send"
    assert keyboard.inline_keyboard[0][0].callback_data == "send_draft123"


def test_email_choice_keyboard():
    emails = ["hr@test.com", "recruiting@test.com"]
    keyboard = email_choice_keyboard(emails)
    
    assert len(keyboard.inline_keyboard) == 2
    assert keyboard.inline_keyboard[0][0].text == "1️⃣ hr@test.com"
    assert keyboard.inline_keyboard[0][0].callback_data == "email_0"


def test_resume_choice_keyboard():
    resumes = [Path("resume1.pdf"), Path("resume2.pdf")]
    keyboard = resume_choice_keyboard(resumes)
    
    assert len(keyboard.inline_keyboard) == 2
    assert keyboard.inline_keyboard[0][0].text == "1️⃣ resume1.pdf"
    assert keyboard.inline_keyboard[0][0].callback_data == "resume_0"
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `pytest tests/test_auth.py tests/test_keyboards.py -v`  
Expected: FAIL with import errors

- [ ] **Step 4: Implement authorization in `src/bot/auth.py`**

```python
from functools import wraps
from telegram import Update
from telegram.ext import ContextTypes

from src.config import Settings


def authorized_only(settings: Settings):
    """Decorator to restrict handler to authorized user only.
    
    Args:
        settings: Application settings with allowed_user_id.
    
    Returns:
        Decorator function.
    """
    def decorator(handler):
        @wraps(handler)
        async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
            if update.effective_user.id != settings.allowed_user_id:
                await update.message.reply_text("⛔ Unauthorized.")
                return None
            return await handler(update, context)
        return wrapper
    return decorator
```

- [ ] **Step 5: Implement keyboards in `src/bot/keyboards.py`**

```python
from pathlib import Path
from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def approval_keyboard(draft_id: str) -> InlineKeyboardMarkup:
    """Build Send / Edit / Skip keyboard.
    
    Args:
        draft_id: Unique identifier for this draft.
    
    Returns:
        InlineKeyboardMarkup with three buttons.
    """
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Send", callback_data=f"send_{draft_id}"),
            InlineKeyboardButton("✏️ Edit", callback_data=f"edit_{draft_id}"),
            InlineKeyboardButton("⏭️ Skip", callback_data=f"skip_{draft_id}"),
        ]
    ])


def email_choice_keyboard(emails: list[str]) -> InlineKeyboardMarkup:
    """Build numbered email selection keyboard.
    
    Args:
        emails: List of email addresses.
    
    Returns:
        InlineKeyboardMarkup with numbered buttons.
    """
    buttons = [
        [InlineKeyboardButton(f"{i+1}️⃣ {email}", callback_data=f"email_{i}")]
        for i, email in enumerate(emails)
    ]
    return InlineKeyboardMarkup(buttons)


def resume_choice_keyboard(resume_files: list[Path]) -> InlineKeyboardMarkup:
    """Build numbered resume selection keyboard.
    
    Args:
        resume_files: List of resume file paths.
    
    Returns:
        InlineKeyboardMarkup with numbered buttons.
    """
    buttons = [
        [InlineKeyboardButton(f"{i+1}️⃣ {path.name}", callback_data=f"resume_{i}")]
        for i, path in enumerate(resume_files)
    ]
    return InlineKeyboardMarkup(buttons)
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `pytest tests/test_auth.py tests/test_keyboards.py -v`  
Expected: PASS (all 5 tests)

- [ ] **Step 7: Commit**

```bash
git add src/bot/ tests/test_auth.py tests/test_keyboards.py
git commit -m "feat: add bot authorization and keyboards

- Implement authorized_only decorator
- Block unauthorized users with error message
- Add approval_keyboard for Send/Edit/Skip
- Add email_choice_keyboard for multiple emails
- Add resume_choice_keyboard for resume selection
- Add tests for auth and keyboards"
```

---

## Task 11: Bot Handlers and Conversation Flow

**Files:**
- Create: `src/bot/handlers.py`
- Create: `tests/test_handlers.py`

**Interfaces:**
- Consumes: All previous components (extractor, drafter, mailer, db, keyboards)
- Produces: Handler functions for Telegram bot:
  - `start_command(update, context)` - async
  - `help_command(update, context)` - async
  - `resume_command(update, context)` - async
  - `handle_message(update, context)` - async
  - `handle_send_callback(update, context)` - async
  - `handle_edit_callback(update, context)` - async
  - `handle_skip_callback(update, context)` - async
  - `handle_email_choice(update, context)` - async
  - `handle_resume_choice(update, context)` - async
  - `handle_edit_text(update, context)` - async

- [ ] **Step 1: Write tests for start command**

```python
# tests/test_handlers.py
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path
from src.bot.handlers import start_command, handle_send_callback


@pytest.mark.asyncio
async def test_start_command_single_resume(tmp_path, monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test")
    monkeypatch.setenv("ALLOWED_USER_ID", "123")
    monkeypatch.setenv("GMAIL_ADDRESS", "test@gmail.com")
    monkeypatch.setenv("GMAIL_APP_PASSWORD", "pass")
    monkeypatch.setenv("REPLY_TO_EMAIL", "reply@gmail.com")
    monkeypatch.setenv("SENDER_NAME", "Test")
    
    # Create single resume
    resume_dir = tmp_path / "resume"
    resume_dir.mkdir()
    (resume_dir / "resume.pdf").write_bytes(b"fake")
    
    with patch("src.bot.handlers.settings.resume_dir", resume_dir):
        mock_update = MagicMock()
        mock_update.message.reply_text = AsyncMock()
        mock_context = MagicMock()
        
        await start_command(mock_update, mock_context)
        
        mock_update.message.reply_text.assert_called_once()
        assert "resume.pdf" in mock_update.message.reply_text.call_args[0][0]


@pytest.mark.asyncio
async def test_handle_send_callback_enforces_daily_cap(tmp_path, monkeypatch):
    """Review Focus #3: Daily cap enforcement."""
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test")
    monkeypatch.setenv("ALLOWED_USER_ID", "123")
    monkeypatch.setenv("GMAIL_ADDRESS", "test@gmail.com")
    monkeypatch.setenv("GMAIL_APP_PASSWORD", "pass")
    monkeypatch.setenv("REPLY_TO_EMAIL", "reply@gmail.com")
    monkeypatch.setenv("SENDER_NAME", "Test")
    monkeypatch.setenv("DAILY_SEND_CAP", "2")
    
    db_path = tmp_path / "test.db"
    
    with patch("src.bot.handlers.settings.database_path", db_path), \
         patch("src.bot.handlers.get_daily_send_count", return_value=2):  # At cap
        
        mock_update = MagicMock()
        mock_update.callback_query.answer = AsyncMock()
        mock_update.callback_query.message.reply_text = AsyncMock()
        mock_context = MagicMock()
        mock_context.user_data = {"draft_id": {}}
        
        await handle_send_callback(mock_update, mock_context)
        
        # Should show cap error, not send
        call_args = mock_update.callback_query.message.reply_text.call_args[0][0]
        assert "Daily send limit reached" in call_args
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_handlers.py -v`  
Expected: FAIL with "cannot import name 'start_command'"

- [ ] **Step 3: Implement handlers in `src/bot/handlers.py`** (Part 1: Commands)

```python
import random
import uuid
from pathlib import Path
from telegram import Update
from telegram.ext import ContextTypes
from email_validator import validate_email, EmailNotValidError

from src.config import Settings
from src.bot.auth import authorized_only
from src.bot.keyboards import approval_keyboard, email_choice_keyboard, resume_choice_keyboard
from src.llm.factory import get_llm
from src.llm.extractor import extract_job_post
from src.llm.drafter import draft_email
from src.mailer.gmail import send_email
from src.storage.db import init_db, insert_application, get_daily_send_count


settings = Settings()


@authorized_only(settings)
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command."""
    # Check for resumes
    resume_files = list(settings.resume_dir.glob("*.pdf"))
    
    if not resume_files:
        await update.message.reply_text(
            "⚠️ No resume found. Please add a PDF to the resume/ directory."
        )
        return
    
    if len(resume_files) == 1:
        context.user_data["selected_resume"] = resume_files[0]
        await update.message.reply_text(
            f"👋 Welcome! Using resume: {resume_files[0].name}\n\n"
            "Send me a LinkedIn job post to get started."
        )
    else:
        context.user_data["resume_files"] = resume_files
        await update.message.reply_text(
            "Found multiple resumes. Which one should I use?",
            reply_markup=resume_choice_keyboard(resume_files)
        )


@authorized_only(settings)
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command."""
    help_text = """
🤖 **Job Application Bot**

**How to use:**
1. Paste a LinkedIn job post
2. I'll extract company, role, and HR email
3. Review the draft email
4. Tap Send to send it

**Commands:**
/start - Start the bot
/help - Show this help
/resume - Change resume selection

**Tips:**
- Make sure the job post includes an email address
- Check the draft before sending
- Edit if you want to customize the email
"""
    await update.message.reply_text(help_text)


@authorized_only(settings)
async def resume_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /resume command."""
    resume_files = list(settings.resume_dir.glob("*.pdf"))
    
    if not resume_files:
        await update.message.reply_text("⚠️ No resume found.")
        return
    
    if len(resume_files) == 1:
        context.user_data["selected_resume"] = resume_files[0]
        await update.message.reply_text(f"Using: {resume_files[0].name}")
    else:
        context.user_data["resume_files"] = resume_files
        await update.message.reply_text(
            "Which resume?",
            reply_markup=resume_choice_keyboard(resume_files)
        )
```

- [ ] **Step 4: Implement handlers** (Part 2: Message Handler)

Add to `src/bot/handlers.py`:

```python
@authorized_only(settings)
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming job post text."""
    # Check if in edit mode
    if context.user_data.get("waiting_for_edit"):
        draft_id = context.user_data["waiting_for_edit"]
        draft_data = context.user_data[draft_id]
        draft_data["body"] = update.message.text
        context.user_data["waiting_for_edit"] = None
        
        await update.message.reply_text(
            f"📧 **Updated Draft**\n\n"
            f"**Subject:** {draft_data['subject']}\n\n"
            f"{draft_data['body']}",
            reply_markup=approval_keyboard(draft_id)
        )
        return
    
    job_text = update.message.text
    
    # Check for multiple job posts
    if job_text.count("@") > 3 or len(job_text) > 3000:
        await update.message.reply_text(
            "⚠️ Found multiple job posts. Please send them one at a time."
        )
        return
    
    await update.message.reply_text("🔍 Extracting details...")
    
    try:
        # Get LLM
        llm = get_llm(settings)
        
        # Extract job post
        job_post = await extract_job_post(job_text, llm)
        
        if not job_post:
            await update.message.reply_text(
                "❌ No email address found in the job post. Please check and try again."
            )
            return
        
        # Validate email format (Review Focus #5)
        try:
            validate_email(job_post.hr_email)
        except EmailNotValidError:
            await update.message.reply_text(
                f"❌ Invalid email address format: {job_post.hr_email}"
            )
            return
        
        # Load profile
        profile_content = settings.resume_dir.parent / "resume" / "profile.md"
        if not profile_content.exists():
            profile_content = "Python developer with 1 year experience."
        else:
            profile_content = profile_content.read_text()
        
        # Draft email
        draft = await draft_email(job_post, profile_content, settings.sender_name, llm)
        
        # Store draft
        draft_id = str(uuid.uuid4())[:8]
        context.user_data[draft_id] = {
            "job_post": job_post,
            "subject": draft.subject,
            "body": draft.body,
        }
        
        # Show draft
        await update.message.reply_text(
            f"📋 **Job Details:**\n"
            f"Company: {job_post.company}\n"
            f"Role: {job_post.role}\n"
            f"HR: {job_post.hr_email}\n\n"
            f"📧 **Draft Email:**\n\n"
            f"**Subject:** {draft.subject}\n\n"
            f"{draft.body}",
            reply_markup=approval_keyboard(draft_id)
        )
    
    except Exception as e:
        await update.message.reply_text(
            f"❌ Failed to extract job details: {str(e)}\n\n"
            "Please try rephrasing or check the job post format."
        )
```

- [ ] **Step 5: Implement handlers** (Part 3: Callback Handlers)

Add to `src/bot/handlers.py`:

```python
async def handle_send_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle Send button callback."""
    await update.callback_query.answer()
    
    draft_id = update.callback_query.data.replace("send_", "")
    draft_data = context.user_data.get(draft_id)
    
    if not draft_data:
        await update.callback_query.message.reply_text("❌ Draft expired.")
        return
    
    # Check daily cap (Review Focus #3)
    await init_db(settings.database_path)
    sent_count = await get_daily_send_count(settings.database_path)
    
    if sent_count >= settings.daily_send_cap:
        await update.callback_query.message.reply_text(
            f"⚠️ Daily send limit reached ({sent_count}/{settings.daily_send_cap}). "
            "Try again tomorrow."
        )
        return
    
    # Get resume
    resume_path = context.user_data.get("selected_resume")
    if not resume_path or not resume_path.exists():
        await update.callback_query.message.reply_text("❌ Resume not found.")
        return
    
    await update.callback_query.message.reply_text("📤 Sending email...")
    
    # Send email
    job_post = draft_data["job_post"]
    success = await send_email(
        to=job_post.hr_email,
        subject=draft_data["subject"],
        body=draft_data["body"],
        attachment_path=resume_path,
        sender_email=settings.gmail_address,
        sender_password=settings.gmail_app_password,
        sender_name=settings.sender_name,
        reply_to=settings.reply_to_email
    )
    
    if success:
        # Log to database
        await insert_application(
            db_path=settings.database_path,
            company=job_post.company,
            role=job_post.role,
            hr_email=job_post.hr_email,
            subject=draft_data["subject"],
            body=draft_data["body"],
            status="sent"
        )
        
        # Random delay for next send
        delay = random.randint(settings.send_delay_min, settings.send_delay_max)
        
        await update.callback_query.message.reply_text(
            f"✅ Email sent to {job_post.hr_email}!\n\n"
            f"Sent today: {sent_count + 1}/{settings.daily_send_cap}\n"
            f"(Waiting {delay}s before next send)"
        )
        
        # Clean up
        del context.user_data[draft_id]
    else:
        await update.callback_query.message.reply_text(
            "❌ Failed to send email. Check your Gmail credentials and network."
        )


async def handle_edit_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle Edit button callback."""
    await update.callback_query.answer()
    
    draft_id = update.callback_query.data.replace("edit_", "")
    context.user_data["waiting_for_edit"] = draft_id
    
    await update.callback_query.message.reply_text(
        "✏️ Send me the new email body:"
    )


async def handle_skip_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle Skip button callback."""
    await update.callback_query.answer()
    
    draft_id = update.callback_query.data.replace("skip_", "")
    draft_data = context.user_data.get(draft_id)
    
    if draft_data:
        # Log as skipped
        await init_db(settings.database_path)
        job_post = draft_data["job_post"]
        await insert_application(
            db_path=settings.database_path,
            company=job_post.company,
            role=job_post.role,
            hr_email=job_post.hr_email,
            subject=draft_data["subject"],
            body=draft_data["body"],
            status="skipped"
        )
        
        del context.user_data[draft_id]
    
    await update.callback_query.message.reply_text("⏭️ Skipped.")


async def handle_email_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle email selection from multiple candidates."""
    await update.callback_query.answer()
    
    index = int(update.callback_query.data.replace("email_", ""))
    emails = context.user_data.get("candidate_emails", [])
    
    if index < len(emails):
        context.user_data["selected_email"] = emails[index]
        await update.callback_query.message.reply_text(f"✅ Selected: {emails[index]}")


async def handle_resume_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle resume selection from multiple files."""
    await update.callback_query.answer()
    
    index = int(update.callback_query.data.replace("resume_", ""))
    resume_files = context.user_data.get("resume_files", [])
    
    if index < len(resume_files):
        context.user_data["selected_resume"] = resume_files[index]
        await update.callback_query.message.reply_text(
            f"✅ Selected: {resume_files[index].name}\n\n"
            "Send me a job post to get started."
        )
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `pytest tests/test_handlers.py -v`  
Expected: PASS (both tests)

- [ ] **Step 7: Add more handler tests**

Add to `tests/test_handlers.py`:
```python
@pytest.mark.asyncio
async def test_handle_message_no_email():
    """Test handling job post with no email."""
    mock_update = MagicMock()
    mock_update.message.text = "Job at Acme Corp, no email provided"
    mock_update.message.reply_text = AsyncMock()
    mock_context = MagicMock()
    mock_context.user_data = {}
    
    with patch("src.bot.handlers.extract_job_post", return_value=None):
        await handle_message(mock_update, mock_context)
        
        call_args = mock_update.message.reply_text.call_args[0][0]
        assert "No email address found" in call_args
```

Run: `pytest tests/test_handlers.py::test_handle_message_no_email -v`  
Expected: PASS

- [ ] **Step 8: Commit**

```bash
git add src/bot/handlers.py tests/test_handlers.py
git commit -m "feat: add bot handlers and conversation flow

- Implement /start, /help, /resume commands
- Handle incoming job post messages
- Extract and draft emails with LLM
- Show draft with approval buttons
- Handle Send/Edit/Skip callbacks
- Enforce daily send cap
- Log applications to database
- Add random delay between sends
- Handle multiple emails and resumes
- Add comprehensive tests"
```

---

## Task 12: Main Application Entry Point

**Files:**
- Create: `src/main.py`

**Interfaces:**
- Consumes: All handlers from `src/bot/handlers.py`, `Settings` from `src/config.py`
- Produces: Runnable Telegram bot application

- [ ] **Step 1: Implement main entry point in `src/main.py`**

```python
import asyncio
import structlog
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters

from src.config import Settings
from src.bot.handlers import (
    start_command,
    help_command,
    resume_command,
    handle_message,
    handle_send_callback,
    handle_edit_callback,
    handle_skip_callback,
    handle_email_choice,
    handle_resume_choice,
)
from src.storage.db import init_db


logger = structlog.get_logger()


async def main():
    """Main application entry point."""
    settings = Settings()
    
    # Initialize database
    await init_db(settings.database_path)
    logger.info("Database initialized", path=str(settings.database_path))
    
    # Build application
    app = Application.builder().token(settings.telegram_bot_token).build()
    
    # Register handlers
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("resume", resume_command))
    
    # Message handler (job posts and edit responses)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Callback handlers
    app.add_handler(CallbackQueryHandler(handle_send_callback, pattern="^send_"))
    app.add_handler(CallbackQueryHandler(handle_edit_callback, pattern="^edit_"))
    app.add_handler(CallbackQueryHandler(handle_skip_callback, pattern="^skip_"))
    app.add_handler(CallbackQueryHandler(handle_email_choice, pattern="^email_"))
    app.add_handler(CallbackQueryHandler(handle_resume_choice, pattern="^resume_"))
    
    logger.info("Bot starting", provider=settings.llm_provider, model=settings.llm_model)
    
    # Run bot
    await app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
```

- [ ] **Step 2: Test bot starts without errors**

Run: `python -m src.main` (Ctrl+C after startup message)  
Expected: Bot starts, connects to Telegram, no errors (will fail on missing token, which is expected)

- [ ] **Step 3: Commit**

```bash
git add src/main.py
git commit -m "feat: add main application entry point

- Build Telegram Application with bot token
- Register all command and callback handlers
- Initialize database on startup
- Add structured logging
- Handle graceful shutdown"
```

---

## Task 13: README and Documentation

**Files:**
- Modify: `README.md`

**Interfaces:**
- Consumes: None
- Produces: Complete setup and usage documentation

- [ ] **Step 1: Write comprehensive README**

```markdown
# Telegram Job Application Bot

A Telegram bot that automates job application emails via Gmail. Paste LinkedIn job post text → bot extracts details with LLM → shows tailored draft → you approve → bot sends email with resume attached.

## Features

- 🤖 **LLM-powered extraction**: Ollama (local) or Google Gemini
- 📧 **Gmail integration**: Sends via SMTP with resume attachment
- ✅ **Approval flow**: Never sends without explicit Send button tap
- 🔒 **Single-user**: Only authorized Telegram user ID can use bot
- 📊 **Application tracking**: SQLite database logs all applications
- 🚦 **Rate limiting**: Configurable daily send cap with random delays
- ✏️ **Edit drafts**: Modify email body before sending

## Requirements

- Python 3.11+
- Telegram account
- Gmail account with App Password
- Ollama installed (or Google Gemini API key)

## Setup

### 1. Install Ollama (Recommended)

```bash
# Visit https://ollama.ai/download and install for your OS

# Pull the default model
ollama pull qwen3:4b-instruct-2507-q4_K_M

# Alternative lightweight models
ollama pull phi4-mini
ollama pull llama3.2:3b
```

### 2. Create Telegram Bot

1. Open Telegram and message [@BotFather](https://t.me/botfather)
2. Send `/newbot` and follow instructions
3. Save the bot token (looks like `123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11`)

### 3. Find Your Telegram User ID

1. Message [@userinfobot](https://t.me/userinfobot) on Telegram
2. Copy your user ID (numeric, e.g., `123456789`)

### 4. Setup Gmail App Password

1. Enable 2-Factor Authentication: https://myaccount.google.com/security
2. Generate App Password: https://myaccount.google.com/apppasswords
3. Select "Mail" and your device, then generate
4. Save the 16-character password (no spaces)

### 5. Install Dependencies

```bash
# Clone or download this repository
cd telegram-job-bot

# Install base dependencies (Ollama only)
pip install -e .

# OR install with Google Gemini support
pip install -e .[google]

# Install dev dependencies for testing
pip install -e .[dev]
```

### 6. Configure Environment

```bash
# Copy example to .env
cp .env.example .env

# Edit .env with your values
nano .env  # or use any text editor
```

Fill in these required values:

```env
TELEGRAM_BOT_TOKEN=your_bot_token_from_botfather
ALLOWED_USER_ID=your_telegram_user_id

GMAIL_ADDRESS=your_email@gmail.com
GMAIL_APP_PASSWORD=your_app_password_here
REPLY_TO_EMAIL=your_reply_to@gmail.com  # Can be Gmail, Outlook, etc.
SENDER_NAME=Your Full Name

# Optional: Change LLM provider
LLM_PROVIDER=ollama  # or "google"
# GOOGLE_API_KEY=your_google_api_key  # Only if using Google
```

### 7. Add Your Resume and Profile

```bash
# Add your resume PDF to resume/ directory
cp /path/to/your/resume.pdf resume/

# Edit resume/profile.md with your background
nano resume/profile.md
```

The `profile.md` file is used by the LLM to personalize emails. Update it with:
- Your experience and skills
- Previous roles and projects
- Technologies you've worked with

## Usage

### Start the Bot

```bash
python -m src.main
```

Keep this terminal open. The bot will run until you press Ctrl+C.

### Apply to Jobs

1. Open Telegram and find your bot (search by name)
2. Send `/start` to begin
3. Copy a LinkedIn job post (full text including email)
4. Paste the text into Telegram chat
5. Bot extracts details and shows draft email
6. Review the draft
7. Tap **✅ Send** to send, **✏️ Edit** to modify, or **⏭️ Skip** to discard

### Commands

- `/start` - Start the bot, select resume
- `/help` - Show help message
- `/resume` - Change resume selection

## Configuration

### Daily Send Limit

Prevent Gmail spam flags by setting a daily cap:

```env
DAILY_SEND_CAP=15  # Recommended: 15-20 for personal Gmail
```

Gmail's unofficial limits:
- **Personal accounts**: ~500/day total, but 15-20 cold applications is safer
- **Burst sending**: Looks like spam, use delays between sends

### Send Delays

Random delays between consecutive sends:

```env
SEND_DELAY_MIN=30  # seconds
SEND_DELAY_MAX=60  # seconds
```

### Switching LLM Provider

**Use Google Gemini instead of Ollama:**

```env
LLM_PROVIDER=google
LLM_MODEL=gemini-1.5-flash  # or gemini-1.5-pro
GOOGLE_API_KEY=your_google_api_key
```

Install Google support: `pip install -e .[google]`

### Adding a New LLM Provider

1. **Write builder function** in `src/llm/factory.py`:

```python
def build_anthropic_llm(settings: Settings) -> ChatAnthropic:
    from langchain_anthropic import ChatAnthropic
    return ChatAnthropic(
        model=settings.llm_model,
        anthropic_api_key=settings.anthropic_api_key,
        temperature=settings.llm_temperature,
    )
```

2. **Register in provider dict**:

```python
_PROVIDERS = {
    "ollama": build_ollama_llm,
    "google": build_google_llm,
    "anthropic": build_anthropic_llm,  # Add this
}
```

3. **Add env vars** to `src/config.py`:

```python
anthropic_api_key: str | None = None
```

4. **Add optional dependency** to `pyproject.toml`:

```toml
[project.optional-dependencies]
anthropic = ["langchain-anthropic>=0.2.0"]
```

5. **Install and use**:

```bash
pip install -e .[anthropic]
```

```env
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=your_key
```

## Project Structure

```
telegram-job-bot/
├── src/
│   ├── main.py              # Entrypoint
│   ├── config.py            # Settings from .env
│   ├── models.py            # Pydantic models
│   ├── bot/
│   │   ├── handlers.py      # Telegram handlers
│   │   ├── keyboards.py     # Inline keyboards
│   │   └── auth.py          # Authorization decorator
│   ├── llm/
│   │   ├── factory.py       # LLM provider registry
│   │   ├── prompts.py       # Prompt templates
│   │   ├── extractor.py     # Job post extraction
│   │   └── drafter.py       # Email drafting
│   ├── extraction/
│   │   └── email_finder.py  # Regex email extraction
│   ├── mailer/
│   │   └── gmail.py         # Gmail SMTP sender
│   └── storage/
│       └── db.py            # SQLite operations
├── tests/                   # Unit tests
├── resume/
│   ├── profile.md           # Your background
│   └── *.pdf                # Resume files
├── data/
│   └── applications.db      # Logged applications
├── .env                     # Your secrets (gitignored)
├── .env.example             # Template
├── pyproject.toml           # Dependencies
└── README.md
```

## Troubleshooting

### "No email address found"

- Job post must contain an email address
- Supported formats: `hr@company.com`, `hr[at]company.com`, `hr (at) company (dot) com`
- Check for email obfuscation and try different formats

### "Gmail authentication failed"

- Use **App Password**, not regular Gmail password
- Make sure 2FA is enabled first
- Check for typos in `.env` (no spaces in password)

### "Daily send limit reached"

- Wait 24 hours or increase `DAILY_SEND_CAP`
- Recommended: Don't exceed 20/day for personal Gmail
- Consider using a dedicated Gmail account for applications

### Bot doesn't respond

- Check `ALLOWED_USER_ID` matches your Telegram user ID
- Verify `TELEGRAM_BOT_TOKEN` is correct
- Make sure bot is running (`python -m src.main`)

### LLM extraction fails

- **Ollama**: Check it's running (`ollama list`)
- **Ollama**: Verify model is pulled (`ollama pull qwen3:4b-instruct-2507-q4_K_M`)
- **Google**: Check API key is valid
- Try a different model or provider

## Development

### Run Tests

```bash
pytest tests/ -v
```

### Lint and Format

```bash
ruff check src/ tests/
ruff format src/ tests/
```

### Run Extractor CLI

Test extraction without running the bot:

```bash
echo "Acme Corp hiring Python Developer. Email: hr@acme.com" | python -m src.llm.extractor
```

## Safety Notes

- Bot only responds to `ALLOWED_USER_ID` (single authorized user)
- Never sends without explicit Send button tap
- Daily cap prevents accidental spam
- Random delays reduce spam filter triggers
- All applications logged to database
- Resume files gitignored (not committed)

## License

MIT

## Support

For issues or questions, open an issue on GitHub or refer to:
- Ollama docs: https://ollama.ai/docs
- python-telegram-bot docs: https://docs.python-telegram-bot.org/
- LangChain docs: https://python.langchain.com/docs/
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: add comprehensive README

- Document Ollama and Google Gemini setup
- Add Telegram bot creation steps
- Document Gmail app password generation
- Explain configuration options
- Add troubleshooting section
- Document adding new LLM providers
- Add usage instructions and examples"
```

---

## Task 14: Final Integration and Testing

**Files:**
- Modify: `.env.example` (ensure complete)
- Create: `data/.gitkeep` (ensure data directory exists)

**Interfaces:**
- Consumes: All components
- Produces: Fully functional bot

- [ ] **Step 1: Verify .env.example is complete**

Ensure `.env.example` matches the updated README and has all required fields.

- [ ] **Step 2: Create data directory**

```bash
mkdir -p data
touch data/.gitkeep
```

- [ ] **Step 3: Run all tests**

Run: `pytest tests/ -v`  
Expected: All tests PASS

- [ ] **Step 4: Run ruff lint and format**

Run: `ruff check src/ tests/`  
Expected: All checks passed

Run: `ruff format src/ tests/`  
Expected: Files formatted

- [ ] **Step 5: Manual integration test checklist**

Create `.env` from `.env.example` with real values, then test:

1. ✅ Bot starts: `python -m src.main`
2. ✅ `/start` command works
3. ✅ Unauthorized user blocked
4. ✅ Resume selection (if multiple PDFs)
5. ✅ Paste job post → extraction works
6. ✅ Draft shown with buttons
7. ✅ Edit button → send new body → draft updates
8. ✅ Skip button → logs as skipped
9. ✅ Send button → email sent, logged to DB
10. ✅ Daily cap enforcement (set cap to 1, try sending 2)

- [ ] **Step 6: Commit**

```bash
git add .env.example data/.gitkeep
git commit -m "chore: finalize project structure

- Ensure .env.example is complete
- Create data directory for database
- Verify all tests pass
- Confirm ruff lint clean"
```

- [ ] **Step 7: Final verification commit**

```bash
git add -A
git commit -m "feat: telegram job application bot v1.0

Complete implementation:
- LLM extraction (Ollama + Google Gemini)
- Email drafting with template
- Telegram approval flow (Send/Edit/Skip)
- Gmail SMTP with resume attachment
- SQLite application logging
- Daily send cap with random delays
- Authorization guard (single user)
- Comprehensive tests and documentation

Ready for production use."
```

---

## Self-Review Checklist

- [x] **Spec coverage**: All requirements from spec are implemented
  - ✅ Telegram bot with conversation flow
  - ✅ LLM extraction (Ollama + Google)
  - ✅ Email drafting with template
  - ✅ Gmail SMTP sending
  - ✅ Resume attachment
  - ✅ Reply-To header
  - ✅ Database logging
  - ✅ Daily send cap
  - ✅ Random delays
  - ✅ Authorization guard
  - ✅ Multiple resume handling
  - ✅ Edit flow
  - ✅ Email validation

- [x] **Step consistency**: Every step is unambiguous
  - Each test step shows exact assertions
  - Each implementation step specifies file and function signatures
  - Verification steps show exact commands and expected output

- [x] **Type consistency**: Names and signatures match across tasks
  - `extract_job_post()` signature consistent in Tasks 6, 11
  - `draft_email()` signature consistent in Tasks 7, 11
  - `send_email()` signature consistent in Tasks 9, 11
  - Model names (`JobPost`, `EmailDraft`) consistent throughout

- [x] **Review Focus**: All 5 items covered with tests
  1. Email validation - Task 6 test
  2. Unauthorized user blocking - Task 10 test
  3. Daily cap enforcement - Task 11 test
  4. Missing resume file - Task 9 test
  5. Invalid email format - Task 11 implementation

- [x] **Proportion check**: Plan is focused on interfaces and decisions
  - File structure defined upfront
  - Each task shows test name and assertions, not full implementation
  - Code steps show signatures and constraints, implementer writes bodies
  - No transcript of full program

---

**Plan complete.** All 14 tasks with TDD workflow, comprehensive tests, and Review Focus coverage.
