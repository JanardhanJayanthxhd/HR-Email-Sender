from src.llm.drafter import format_email_body


def test_format_email_body_paragraphs_and_configured_signature():
    body = (
        "Dear Hiring Team, I am applying for the Backend Developer position at TechNova Solutions. "
        "With one year of Python experience, I have worked with Django and FastAPI. "
        "I implemented backend services using PostgreSQL and Docker. "
        "I am confident I can contribute to your team. "
        "Thank you for your time. Best regards, [redacted] "
        "janardhan555jayanth@gmail.com"
    )

    formatted = format_email_body(
        body,
        sender_name="[redacted]",
        reply_to_email="janardhan555jayanth@outlook.com",
    )

    assert formatted.startswith("Dear Hiring Team,\n\n")
    assert len(formatted.split("\n\n")) == 5
    assert "janardhan555jayanth@gmail.com" not in formatted
    assert formatted.endswith(
        "Best regards,\n[redacted]\njanardhan555jayanth@outlook.com"
    )
