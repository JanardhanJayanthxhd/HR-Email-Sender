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