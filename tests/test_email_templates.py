import pytest

from src.mailer.email_templates import EMAIL_TEMPLATES, render_email_template, settings


def test_templates_render_role_and_configured_name_without_optional_phone(monkeypatch):
    monkeypatch.setattr(settings, "sender_name", "Configured Name")
    monkeypatch.setattr(settings, "sender_phone", "")

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
    assert detailed.subject == "Application for Python Developer"
    assert straightforward.subject == "Application for Backend Developer"
    assert "Acme Ltd" not in detailed.subject + straightforward.subject
    assert "Python Developer position at Acme Ltd" in detailed.body
    assert detailed.body.endswith("Best regards,\nConfigured Name")
    assert "Backend Developer at Acme Ltd" in straightforward.body
    assert straightforward.body.endswith("Sincerely,\nConfigured Name")
    assert "\n\n" in detailed.body
    assert "\n\n" in straightforward.body


def test_templates_include_optional_phone_from_settings(monkeypatch):
    monkeypatch.setattr(settings, "sender_name", "Configured Name")
    monkeypatch.setattr(settings, "sender_phone", "+1 555 010 1234")

    detailed = render_email_template(1, company="Acme Ltd", role="Python Developer")
    straightforward = render_email_template(2, company="Acme Ltd", role="Backend Developer")

    assert detailed.body.endswith("Configured Name\n+1 555 010 1234")
    assert straightforward.body.endswith("Configured Name\n+1 555 010 1234")


def test_template_number_out_of_range_is_rejected():
    with pytest.raises(ValueError, match="between 1 and 2"):
        render_email_template(3, company="Acme Ltd", role="Developer")
