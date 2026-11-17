import pytest
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
    text = "Contact hr @ company . com"
    result = find_emails(text)
    assert result == ["hr@company.com"]


def test_plain_language_at_does_not_corrupt_email():
    text = "We're Hiring Freshers at Plutas.ai! Share your profile at bipasha.chhabra@plutas.ai"
    result = find_emails(text)
    assert result == ["bipasha.chhabra@plutas.ai"]


def test_find_email_with_dot_brackets():
    text = "Email: hr@company[dot]com"
    result = find_emails(text)
    assert result == ["hr@company.com"]


def test_find_email_with_dot_parens():
    text = "Email: hr@company(dot)com"
    result = find_emails(text)
    assert result == ["hr@company.com"]


def test_find_email_case_insensitive():
    text = "Email: HR[AT]COMPANY[DOT]COM"
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


def test_deduplicates_emails():
    text = "Contact hr@company.com or hr@company.com again"
    result = find_emails(text)
    assert result == ["hr@company.com"]