# Telegram Job Application Bot - Design Specification

**Date:** 2026-11-12  
**Author:** Claude (Kiro)  
**Status:** Approved for Implementation

## Overview

A Telegram bot that automates job application emails via Gmail. User pastes LinkedIn job post text → bot extracts company/role/HR email using LLM → shows tailored draft → user approves → bot sends email with resume attached.

## Goals

- **Primary:** Reduce friction in applying to multiple jobs by automating email composition and sending
- **Safety:** Never send without explicit user approval via button tap
- **Flexibility:** Support multiple LLM providers (Ollama local, Google Gemini) via LangChain
- **Tracking:** Log all applications to SQLite for reference

## Non-Goals

- LinkedIn scraping or automation (input is pasted text only)
- Multi-user support (single authorized Telegram user ID only)
- Resume parsing or generation (uses existing PDF)
- Job search or recommendation features

## Constraints

### Hard Constraints

1. **Python 3.11+** minimum version
2. **Free tools only** - no paid APIs required (Ollama default)
3. **No LinkedIn scraping** - input is manual paste only
4. **Never send without approval** - explicit Send button tap required
5. **Single authorized user** - only `ALLOWED_USER_ID` can use bot
6. **All secrets in .env** (gitignored, with `.env.example` provided)
7. **Gmail SMTP only** - no other email providers
8. **Type hints everywhere** - fully typed codebase
9. **Async where library is async** - proper async/await usage

### Quality Constraints

1. **Simple, modular code** - single responsibility per file
2. **LangChain for ALL LLM access** - no direct provider SDK calls outside `src/llm/`
3. **Tests mock LLM and SMTP** - no network calls in unit tests
4. **Ruff clean** - lint and format passing
5. **DRY, YAGNI** - no speculative features

## Architecture

### System Components

```
┌─────────────┐
│  Telegram   │
│    User     │
└──────┬──────┘
       │ paste job text
       ▼
┌─────────────────────────────────────────┐
│         Telegram Bot (python-telegram-bot)│
│  ┌────────────────────────────────────┐ │
│  │  ConversationHandler               │ │
│  │  - /start, /help, /resume commands │ │
│  │  - Message handler                 │ │
│  │  - Button callbacks                │ │
│  └────────────────────────────────────┘ │
└──────┬───────────────────┬──────────────┘
       │                   │
       │ extract           │ send
       ▼                   ▼
┌─────────────┐     ┌─────────────┐
│ LLM Layer   │     │   Mailer    │
│ (LangChain) │     │ (aiosmtplib)│
│             │     │             │
│ - Extractor │     │ - Gmail     │
│ - Drafter   │     │   SMTP:465  │
└─────────────┘     └─────────────┘
       │                   │
       │                   │ attach
       ▼                   ▼
┌─────────────┐     ┌─────────────┐
│  Storage    │     │  resume.pdf │
│ (aiosqlite) │     │             │
└─────────────┘     └─────────────┘
```

### Data Flow

1. **User pastes job text** → Telegram message handler
2. **Extract emails** → `email_finder.py` (regex + de-obfuscation)
3. **LLM extraction** → `extractor.py` (company, role, requirements, HR email from candidates)
4. **Validate email** → `email-validator` library
5. **LLM drafting** → `drafter.py` (tailored email using profile)
6. **Show draft** → Inline keyboard with Send/Edit/Skip buttons
7. **User taps Send** → Check daily cap, check database, send via Gmail
8. **Log to DB** → Record application details

### LLM Provider Architecture

**Provider Selection via Environment Variable:**

```python
LLM_PROVIDER = "ollama"  # or "google"
```

**Factory Pattern:**

```python
# src/llm/factory.py
_PROVIDERS = {
    "ollama": build_ollama_llm,
    "google": build_google_llm,
}

def get_llm(settings: Settings) -> BaseChatModel:
    builder = _PROVIDERS.get(settings.llm_provider)
    if not builder:
        raise ValueError(f"Unknown provider: {settings.llm_provider}. Supported: {list(_PROVIDERS.keys())}")
    return builder(settings)
```

**Adding New Provider:**
1. Write builder function (e.g., `build_anthropic_llm`)
2. Register in `_PROVIDERS` dict
3. Add required env vars to `config.py`
4. Document in README

## Components

### 1. Configuration (`src/config.py`)

**Purpose:** Type-safe configuration from environment variables using `pydantic-settings`.

**Settings:**

```python
class Settings(BaseSettings):
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
    send_delay_min: int = 30  # seconds
    send_delay_max: int = 60  # seconds
    
    # Paths
    resume_dir: Path = Path("resume")
    profile_path: Path = Path("resume/profile.md")
    database_path: Path = Path("data/applications.db")
    
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")
```

### 2. Bot Layer (`src/bot/`)

#### `handlers.py`

**Purpose:** Telegram message handlers and conversation flow.

**Handlers:**

- `/start` - Welcome message, check authorization, ask for resume selection
- `/help` - Usage instructions
- `/resume` - Change resume selection
- **Text message** - Parse job post, extract details, show draft
- **Button callbacks:**
  - `send_{uuid}` - Send email
  - `edit_{uuid}` - Enter edit mode
  - `skip_{uuid}` - Discard draft
  - `email_{index}` - Select from multiple HR emails
  - `resume_{index}` - Select resume file

**Conversation States:**

- `WAITING_JOB_TEXT` - Default state
- `WAITING_EDIT` - After "Edit" button, waiting for replacement body text
- `WAITING_EMAIL_CHOICE` - Multiple HR emails found
- `WAITING_RESUME_CHOICE` - Multiple resumes found

#### `keyboards.py`

**Purpose:** Build inline keyboards for user interactions.

**Functions:**

```python
def approval_keyboard(draft_id: str) -> InlineKeyboardMarkup:
    """Send / Edit / Skip buttons."""

def email_choice_keyboard(emails: list[str]) -> InlineKeyboardMarkup:
    """Numbered email selection buttons."""

def resume_choice_keyboard(resume_files: list[Path]) -> InlineKeyboardMarkup:
    """Numbered resume selection buttons."""
```

#### `auth.py`

**Purpose:** Authorization decorator to restrict bot to single user.

```python
def authorized_only(handler):
    """Decorator that checks user_id against ALLOWED_USER_ID."""
    @wraps(handler)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id != settings.allowed_user_id:
            await update.message.reply_text("⛔ Unauthorized.")
            return
        return await handler(update, context)
    return wrapper
```

### 3. LLM Layer (`src/llm/`)

#### `factory.py`

**Purpose:** Provider-agnostic LLM instantiation via registry pattern.

**Functions:**

```python
def build_ollama_llm(settings: Settings) -> ChatOllama:
    """Build Ollama chat model."""

def build_google_llm(settings: Settings) -> ChatGoogleGenerativeAI:
    """Build Google Gemini chat model."""

def get_llm(settings: Settings) -> BaseChatModel:
    """Get LLM instance based on provider setting."""
```

#### `prompts.py`

**Purpose:** LangChain prompt templates for extraction and drafting.

**Prompts:**

1. **Extraction Prompt:**
   - Input: Job post text, candidate emails (from regex)
   - Output: `JobPost` (company, role, requirements, HR email)
   - Constraints: HR email MUST be from candidate list, reject if no email found

2. **Drafting Prompt:**
   - Input: `JobPost`, profile content
   - Output: `EmailDraft` (subject, body)
   - Constraints: Under 150 words, no invented facts, mention 2-3 matching requirements

#### `extractor.py`

**Purpose:** Extract structured job data from pasted text.

**Function:**

```python
async def extract_job_post(
    text: str,
    candidate_emails: list[str],
    llm: BaseChatModel
) -> JobPost:
    """
    Extract company, role, requirements, and HR email.
    
    Returns JobPost with structured output using with_structured_output().
    Retries up to 2 times on validation failure (tenacity).
    Raises ValueError if HR email not in candidate list.
    """
```

#### `drafter.py`

**Purpose:** Generate tailored application email.

**Function:**

```python
async def draft_email(
    job_post: JobPost,
    profile: str,
    sender_name: str,
    llm: BaseChatModel
) -> EmailDraft:
    """
    Draft email body tailored to job requirements.
    
    Uses profile.md content to match requirements.
    Returns EmailDraft with subject and body.
    Retries up to 2 times on validation failure.
    """
```

### 4. Extraction (`src/extraction/`)

#### `email_finder.py`

**Purpose:** Find and de-obfuscate email addresses in text.

**Function:**

```python
def find_emails(text: str) -> list[str]:
    """
    Extract emails using regex with de-obfuscation.
    
    Handles formats:
    - Standard: user@example.com
    - [at]: user[at]example.com
    - (at): user(at)example.com
    - " at ": user at example dot com
    - [dot]: user@example[dot]com
    - (dot): user@example(dot)com
    - Spaces: user @ example . com
    
    Returns list of normalized email addresses.
    """
```

### 5. Mailer (`src/mailer/`)

#### `gmail.py`

**Purpose:** Send emails via Gmail SMTP with async support.

**Function:**

```python
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
    """
    Send email via Gmail SMTP (smtp.gmail.com:465, SSL).
    
    Attaches PDF resume.
    Sets Reply-To header.
    Returns True on success, False on failure.
    """
```

### 6. Storage (`src/storage/`)

#### `db.py`

**Purpose:** SQLite database for application tracking.

**Schema:**

```sql
CREATE TABLE applications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company TEXT NOT NULL,
    role TEXT NOT NULL,
    hr_email TEXT NOT NULL,
    subject TEXT NOT NULL,
    body TEXT NOT NULL,
    status TEXT NOT NULL,  -- 'sent' or 'skipped'
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_timestamp ON applications(timestamp);
CREATE INDEX idx_status ON applications(status);
```

**Functions:**

```python
async def init_db(db_path: Path) -> None:
    """Initialize database schema."""

async def insert_application(
    db_path: Path,
    company: str,
    role: str,
    hr_email: str,
    subject: str,
    body: str,
    status: str
) -> None:
    """Insert application record."""

async def get_daily_send_count(db_path: Path) -> int:
    """Count emails sent today (status='sent')."""
```

### 7. Models (`src/models.py`)

**Purpose:** Pydantic models for structured data.

**Models:**

```python
class JobPost(BaseModel):
    """Extracted job details."""
    company: str
    role: str
    requirements_summary: str  # 2-3 sentence summary
    key_requirements: list[str]  # Bullet points for matching
    hr_email: str

class EmailDraft(BaseModel):
    """Generated email content."""
    subject: str
    body: str
```

## Email Template

**Single professional template (professional-leaning, mid-casual tone):**

```
Dear Hiring Team,

I came across your post for the {role} position at {company} and would like to apply. I am a Python developer with 1 year of experience in the IT sector, based in Chennai, with a strong interest in Python and Generative AI.

{tailored_paragraph_matching_requirements}

I am eager to apply my skills, take on new challenges, and contribute to your team. Please find my resume attached for your consideration.

Thank you for your time. I look forward to hearing from you.

Best regards,
{sender_name}
{phone_number}
```

**The `{tailored_paragraph_matching_requirements}` section is generated by the LLM based on:**
- Job requirements from `JobPost.key_requirements`
- User's background from `resume/profile.md`
- Constraint: Mention 2-3 requirements that match profile
- Constraint: No invented facts about user

## Email Extraction Rules

1. **Regex first:** `email_finder.py` runs regex + de-obfuscation on job text
2. **LLM selects:** LLM picks HR email FROM regex candidates only
3. **Validation:** Reject any LLM-returned email not in source text
4. **Multiple emails:** Show numbered buttons, user selects
5. **No email found:** Tell user and stop (no draft shown)
6. **Email validation:** Use `email-validator` before showing draft

## User Flows

### Happy Path: Single Job Application

1. User pastes LinkedIn job post text
2. Bot replies: "🔍 Extracting details..."
3. Bot finds 1 HR email via regex
4. LLM extracts company, role, requirements
5. LLM drafts tailored email
6. Bot shows:
   ```
   📋 Job Details:
   Company: Acme Corp
   Role: Python Developer
   HR: hr@acme.com
   
   📧 Draft Email:
   Subject: Application Janardhan Jayanth - Python Developer
   
   [Email body preview]
   
   [Send] [Edit] [Skip]
   ```
7. User taps **Send**
8. Bot checks daily cap (not exceeded)
9. Bot sends email via Gmail
10. Bot waits random delay (30-60s)
11. Bot logs to database (status='sent')
12. Bot replies: "✅ Email sent to hr@acme.com"

### Alternative Flow: Multiple HR Emails

1. User pastes job text
2. Regex finds 3 emails: hr@acme.com, recruiting@acme.com, john@acme.com
3. Bot shows:
   ```
   Found multiple email addresses. Which one is HR?
   
   1️⃣ hr@acme.com
   2️⃣ recruiting@acme.com
   3️⃣ john@acme.com
   ```
4. User taps **1**
5. Flow continues with selected email

### Alternative Flow: Edit Email Body

1. Bot shows draft with [Send] [Edit] [Skip]
2. User taps **Edit**
3. Bot replies: "Send me the new email body:"
4. User sends replacement text
5. Bot re-shows draft with updated body
6. User taps **Send** (or **Edit** again)

### Alternative Flow: Multiple Resumes

1. User starts bot with `/start`
2. Bot finds 2 PDFs in `resume/` directory
3. Bot shows:
   ```
   Found multiple resumes. Which one should I use?
   
   1️⃣ resume-python-dev.pdf
   2️⃣ resume-full-stack.pdf
   ```
4. User taps **2**
5. Bot remembers choice for this session

### Alternative Flow: Daily Cap Reached

1. User has sent 15 emails today (daily cap = 15)
2. User pastes new job and taps **Send**
3. Bot replies: "⚠️ Daily send limit reached (15/15). Try again tomorrow."
4. Application NOT sent, NOT logged

### Alternative Flow: No Email Found

1. User pastes job text without email address
2. Regex finds no emails
3. Bot replies: "❌ No email address found in the job post. Please check and try again."
4. No draft shown, no extraction attempted

### Error Flow: Multiple Job Posts

1. User pastes text containing 2+ distinct job descriptions
2. Bot detects multiple jobs
3. Bot replies: "⚠️ Found multiple job posts. Please send them one at a time."
4. No extraction attempted

### Error Flow: Unauthorized User

1. Different Telegram user (not `ALLOWED_USER_ID`) sends message
2. Bot replies: "⛔ Unauthorized."
3. No action taken

## Safety Features

### Daily Send Cap

- Configurable via `DAILY_SEND_CAP` env var (default 15)
- Counts only emails with status='sent' in last 24 hours
- Prevents sending if cap reached, shows friendly error
- Recommendation: Start with 15, increase to 20-25 if needed

### Random Delay Between Sends

- Random delay between `SEND_DELAY_MIN` and `SEND_DELAY_MAX` seconds
- Default: 30-60 seconds
- Prevents Gmail spam filters from flagging rapid-fire sends
- Delay happens AFTER send, before next job application

### Authorization Guard

- Only `ALLOWED_USER_ID` can use bot
- Decorator on all handlers: `@authorized_only`
- Unauthorized users get "⛔ Unauthorized." message

### Graceful Error Messages

- Network errors: "❌ Failed to send email. Check your internet connection."
- Gmail errors: "❌ Gmail authentication failed. Check your app password."
- LLM errors: "❌ Failed to extract job details. Please try rephrasing."
- Validation errors: "❌ Failed to generate valid email. Please try again."

### Structured Logging

- Use `structlog` for JSON logs
- Log levels: INFO (sends), WARNING (cap reached), ERROR (failures)
- Log fields: timestamp, user_id, action, status, company, role

### Graceful Shutdown

- Handle SIGINT/SIGTERM
- Close database connections
- Stop Telegram polling gracefully

## Dependencies

**Runtime (pyproject.toml):**

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
```

**Installation:**

```bash
# Base install (Ollama only)
pip install -e .

# With Google Gemini support
pip install -e .[google]

# Development dependencies
pip install -e .[dev]
```

## Testing Strategy

### Unit Tests (No Network)

- **Mock LLM:** Use fake LangChain chat model for extraction/drafting tests
- **Mock SMTP:** Use `pytest-mock` to mock `aiosmtplib.SMTP`
- **Mock Telegram:** Mock `python-telegram-bot` Update/Context objects

### Test Coverage

- `email_finder.py`: All obfuscation formats + edge cases
- `extractor.py`: Valid extraction, email validation, retry logic
- `drafter.py`: Template filling, word count, requirement matching
- `db.py`: Insert, count, schema creation
- `gmail.py`: Send success, send failure, attachment handling
- `handlers.py`: Authorization, conversation flow, button callbacks

### CLI Testing Script

```bash
# Test extraction without running bot
echo "Company XYZ is hiring Python Developer. Email: hr@xyz.com" | python -m src.llm.extractor
```

## File Structure

```
auto_email_sender/
├── src/
│   ├── main.py              # Entrypoint, builds Application, registers handlers
│   ├── config.py            # Pydantic Settings class
│   ├── models.py            # JobPost, EmailDraft
│   ├── bot/
│   │   ├── __init__.py
│   │   ├── handlers.py      # Message handler, button callbacks
│   │   ├── keyboards.py     # Inline keyboard builders
│   │   └── auth.py          # Authorization decorator
│   ├── llm/
│   │   ├── __init__.py
│   │   ├── factory.py       # get_llm() via provider registry
│   │   ├── prompts.py       # ChatPromptTemplate objects
│   │   ├── extractor.py     # text -> JobPost
│   │   └── drafter.py       # JobPost + profile -> EmailDraft
│   ├── extraction/
│   │   ├── __init__.py
│   │   └── email_finder.py  # Regex + de-obfuscation
│   ├── mailer/
│   │   ├── __init__.py
│   │   └── gmail.py         # send_email() via aiosmtplib
│   └── storage/
│       ├── __init__.py
│       └── db.py            # SQLite schema, insert, query
├── tests/
│   ├── __init__.py
│   ├── test_email_finder.py
│   ├── test_extractor.py
│   ├── test_drafter.py
│   ├── test_gmail.py
│   ├── test_db.py
│   └── test_handlers.py
├── resume/
│   ├── profile.md           # User background (for LLM)
│   └── *.pdf                # Resume files
├── data/
│   └── applications.db      # SQLite database (gitignored)
├── docs/
│   └── superpowers/
│       ├── specs/
│       │   └── 2026-11-12-telegram-job-bot-design.md
│       └── plans/
│           └── 2026-11-12-telegram-job-bot-plan.md
├── .env                     # Secrets (gitignored)
├── .env.example             # Template
├── .gitignore
├── pyproject.toml           # Dependencies, ruff config
├── README.md                # Setup instructions
└── ruff.toml                # Ruff configuration

# OLD FILES TO DELETE:
├── app.py                   # Tkinter app (DELETE)
├── email_config.py          # Old config (DELETE)
├── email_sender.py          # Old sender (DELETE)
├── email_templates.py       # Old templates (DELETE)
└── requirements.txt         # Old deps (DELETE)
```

## README Requirements

**Must document:**

1. **Ollama Installation:**
   - Install Ollama: https://ollama.ai/download
   - Pull model: `ollama pull qwen3:4b-instruct-2507-q4_K_M`
   - Fallback models: `phi4-mini`, `llama3.2:3b`

2. **Telegram Bot Setup:**
   - Create bot via BotFather: https://t.me/botfather
   - Get bot token
   - Find your Telegram user ID: Use @userinfobot

3. **Gmail App Password:**
   - Enable 2FA: https://myaccount.google.com/security
   - Generate App Password: https://myaccount.google.com/apppasswords
   - Use app password in `GMAIL_APP_PASSWORD` (not regular password)

4. **Environment Variables:**
   - Copy `.env.example` to `.env`
   - Fill in all required values

5. **Profile Setup:**
   - Edit `resume/profile.md` with your background
   - Add your resume PDF to `resume/` directory

6. **Running the Bot:**
   ```bash
   python -m src.main
   ```

7. **Switching LLM Provider:**
   - Change `LLM_PROVIDER=google` in `.env`
   - Set `GOOGLE_API_KEY`
   - Install extra: `pip install -e .[google]`

8. **Adding New LLM Provider:**
   - Write builder function in `src/llm/factory.py`
   - Register in `_PROVIDERS` dict
   - Add env vars to `src/config.py`
   - Add optional dependency to `pyproject.toml`

## Success Criteria

### Functional

- ✅ Bot responds only to authorized user
- ✅ Extracts company, role, HR email from pasted text
- ✅ Generates tailored email mentioning 2-3 matching requirements
- ✅ Shows draft with Send/Edit/Skip buttons
- ✅ Sends email only after Send button tap
- ✅ Attaches resume PDF
- ✅ Respects daily send cap
- ✅ Logs all applications to database
- ✅ Handles multiple HR emails (user selects)
- ✅ Handles multiple resumes (user selects)
- ✅ Edit flow works (replace body text)

### Non-Functional

- ✅ Type hints everywhere (mypy clean optional)
- ✅ Ruff lint and format passing
- ✅ All tests pass with mocked LLM/SMTP
- ✅ No network calls in unit tests
- ✅ Structured logging to stdout
- ✅ Graceful shutdown (Ctrl+C)
- ✅ README documents all setup steps

## Open Questions (Resolved)

1. ~~Reply-To email address~~ → Configurable via `REPLY_TO_EMAIL` env var
2. ~~Random delay necessary?~~ → Yes, 30-60 seconds to avoid spam flags
3. ~~Daily cap vs hourly limit~~ → Daily cap only (hourly not needed)
4. ~~Email template tone~~ → Professional-leaning, mid-casual (template provided)
5. ~~Resume selection timing~~ → Ask each time user applies
6. ~~Multiple jobs in one message~~ → Tell user to send one at a time
7. ~~Replace or keep old code~~ → Complete replacement (delete old Tkinter app)
8. ~~LLM providers~~ → Ollama (default) + Google Gemini only

## Milestones

### Milestone 1: Scaffold + Auth
- Project structure, pyproject.toml, .env.example
- Config with pydantic-settings
- Bot responds "got it" to text
- Rejects unauthorized users
- Ruff + pytest setup

### Milestone 2: Email Extraction
- `email_finder.py` with regex + de-obfuscation
- Thorough unit tests (all obfuscation formats)
- Handles edge cases (multiple emails, no emails)

### Milestone 3: LLM Integration
- `factory.py` with Ollama + Google providers
- `extractor.py` with structured output
- CLI test script: `python -m src.llm.extractor < sample.txt`
- Uses fake chat model in tests (no network)

### Milestone 4: Drafting + Approval Flow
- `drafter.py` generates email from template
- Bot shows extracted details + draft
- Send / Edit / Skip buttons work
- Edit flow: user sends replacement, bot re-shows draft

### Milestone 5: Email Sending
- `gmail.py` sends via aiosmtplib (SSL port 465)
- Resume attachment
- Reply-To header
- First test sends to user's own address
- Random delay between sends

### Milestone 6: Database Logging
- `db.py` with SQLite schema
- Insert application records
- Daily send count query
- No duplicate detection (just logging)

### Milestone 7: Safety + Polish
- Daily send cap enforcement
- Graceful error messages
- Structured logging
- Graceful shutdown
- README with all setup steps

## Risk Mitigation

### Gmail Spam Filters

**Risk:** Sending too many emails flags account.

**Mitigation:**
- Daily cap default 15 (conservative)
- Random 30-60s delays
- README warns about daily limits
- User can adjust cap based on experience

### LLM Hallucination

**Risk:** LLM invents email addresses or facts about user.

**Mitigation:**
- Regex runs FIRST, LLM selects from candidates only
- Validation rejects emails not in source text
- Profile.md constrains facts about user
- Drafting prompt: "Use ONLY information from profile.md"

### Extraction Failures

**Risk:** LLM returns invalid structured output.

**Mitigation:**
- Retry up to 2 times with tenacity
- Pydantic validation enforces schema
- After retries, show friendly error to user
- User can rephrase and try again

### Token Costs (Google Gemini)

**Risk:** User switches to Google and racks up API costs.

**Mitigation:**
- Ollama is default (free, local)
- README documents Ollama setup prominently
- Google requires explicit opt-in (install extra, set API key)
- Low temperature (0.0) reduces token usage

### Resume Privacy

**Risk:** Resume contains sensitive info.

**Mitigation:**
- Resume directory gitignored
- Profile.md separate from resume (for LLM context only)
- User controls what goes in profile.md
- Single authorized user (no multi-user exposure)

## Future Enhancements (Out of Scope)

- Multi-user support with per-user configs
- Web dashboard for application tracking
- Email thread tracking (did HR reply?)
- Job search integration (scrape LinkedIn)
- Resume parsing/generation
- A/B testing email variants
- Analytics (response rates, best templates)
- Slack/Discord bot versions

---

**End of Design Specification**
