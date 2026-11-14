from dataclasses import dataclass

from src.config import settings
from src.models import EmailDraft


@dataclass(frozen=True)
class EmailTemplate:
    name: str
    subject: str
    body: str


EMAIL_TEMPLATES = (
    EmailTemplate(
        name="Slightly detailed",
        subject="Application for {role} at {company}",
        body="""Dear Hiring Team,

I came across your post for the {role} position at {company} and would like to apply. I am a Python developer with 1 year of experience in the IT sector, based in Chennai, with a strong interest in Python and Generative AI.

In my previous role as a Junior Software Developer, I worked on REST APIs and AI-powered applications. I have also built personal projects involving RAG, LLMs, and vector search using PostgreSQL and pgvector.

I am eager to apply my skills, take on new challenges, and contribute to your team. Please find my resume attached for your consideration.

Thank you for your time. I look forward to hearing from you.
Best regards,
{sender_name}
{phone_line}""",
    ),
    EmailTemplate(
        name="Straightforward",
        subject="Application for {role} at {company}",
        body="""Dear Hiring Manager,

I am writing to apply for the {role} at {company}.

I am a Software Developer with experience in Python and FastAPI, and I have worked on building backend systems and AI-based applications. I have also developed a RAG-based project for document querying using LLMs.

I have attached my resume for your consideration. I would appreciate the opportunity to discuss how my skills can contribute to your team.

Thank you for your time and consideration.

Sincerely,
{sender_name}
{phone_line}""",
    ),
)


def render_email_template(template_number: int, *, company: str, role: str) -> EmailDraft:
    """Render a numbered fixed email template with the extracted job details."""
    if not 1 <= template_number <= len(EMAIL_TEMPLATES):
        raise ValueError(f"Template number must be between 1 and {len(EMAIL_TEMPLATES)}")

    template = EMAIL_TEMPLATES[template_number - 1]
    phone_line = (settings.sender_phone or "").strip()
    body = template.body.format(
        role=role,
        company=company,
        sender_name=settings.sender_name,
        phone_line=phone_line,
    )
    return EmailDraft(
        subject=template.subject.format(role=role, company=company),
        body=body.rstrip(),
    )
