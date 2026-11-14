import pytest

from src.mailer.email_templates import EMAIL_TEMPLATES, render_email_template


def test_templates_render_role_and_company_with_separate_paragraphs():
    detailed = render_email_template(
        1,
        company="Acme Ltd",
        role="Python Developer",
    )
    straightforward = render_email_template(
        2,
        company="Acme Ltd",
        role="Backend Developer",
    )

    assert len(EMAIL_TEMPLATES) == 2
    assert "Python Developer position at Acme Ltd" in detailed.body
    assert detailed.body.endswith("[redacted]\n[redacted]")
    assert "Backend Developer at Acme Ltd" in straightforward.body
    assert straightforward.body.endswith("[redacted]\n[redacted]")
    assert "\n\n" in detailed.body
    assert "\n\n" in straightforward.body


def test_template_bodies_match_requested_wording():
    detailed = render_email_template(1, company="Acme Ltd", role="Python Developer")
    straightforward = render_email_template(2, company="Acme Ltd", role="Backend Developer")

    assert detailed.body == """Dear Hiring Team,

I came across your post for the Python Developer position at Acme Ltd and would like to apply. I am a Python developer with 1 year of experience in the IT sector, based in Chennai, with a strong interest in Python and Generative AI.

In my previous role as a Junior Software Developer, I worked on REST APIs and AI-powered applications. I have also built personal projects involving RAG, LLMs, and vector search using PostgreSQL and pgvector.

I am eager to apply my skills, take on new challenges, and contribute to your team. Please find my resume attached for your consideration.

Thank you for your time. I look forward to hearing from you.
Best regards,
[redacted]
[redacted]"""
    assert straightforward.body == """Dear Hiring Manager,

I am writing to apply for the Backend Developer at Acme Ltd.

I am a Software Developer with experience in Python and FastAPI, and I have worked on building backend systems and AI-based applications. I have also developed a RAG-based project for document querying using LLMs.

I have attached my resume for your consideration. I would appreciate the opportunity to discuss how my skills can contribute to your team.

Thank you for your time and consideration.

Sincerely,
[redacted]
[redacted]"""


def test_template_number_out_of_range_is_rejected():
    with pytest.raises(ValueError, match="between 1 and 2"):
        render_email_template(3, company="Acme Ltd", role="Developer")
