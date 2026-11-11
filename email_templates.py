"""Email template variants for job applications.

Contains three professional variants with slightly different tones.
"""


def get_template_1(sender_name: str, position: str, company: str) -> str:
    """Generate template 1 for job application.

    Args:
        sender_name: Applicant's full name.
        position: Job position being applied for.
        company: Company name.

    Returns:
        Formatted email body string.
    """
    return f"""Dear Hiring Manager,

I am writing to express my strong interest in the {position} position at {company}.

[Add your skills, experience, and qualifications here for Template 1]

I have attached my resume for your review, which provides additional details about my qualifications and achievements. I would welcome the opportunity to discuss how my experience and skills can benefit {company}.

Thank you for considering my application. I look forward to the possibility of contributing to your organization.

Sincerely,
{sender_name}"""


def get_template_2(sender_name: str, position: str, company: str) -> str:
    """Generate template 2 for job application.

    Args:
        sender_name: Applicant's full name.
        position: Job position being applied for.
        company: Company name.

    Returns:
        Formatted email body string.
    """
    return f"""Hello,

I'm excited to apply for the {position} role at {company}.

[Add your skills, experience, and qualifications here for Template 2]

I've attached my resume with more details about my background. I'd love to discuss how I can contribute to your team and learn more about the role.

Thanks for your time and consideration. I'm looking forward to hearing from you!

Best regards,
{sender_name}"""


def get_template_3(sender_name: str, position: str, company: str) -> str:
    """Generate template 3 for job application.

    Args:
        sender_name: Applicant's full name.
        position: Job position being applied for.
        company: Company name.

    Returns:
        Formatted email body string.
    """
    return f"""Hello,

I'm applying for the {position} position at {company}.

[Add your skills, experience, and qualifications here for Template 3]

My resume is attached for your review. I'd appreciate the opportunity to discuss this role further.

Thank you for your consideration.

Best,
{sender_name}"""


TEMPLATE_OPTIONS = {
    "template1": get_template_1,
    "template2": get_template_2,
    "template3": get_template_3,
}


def get_template(
    template_type: str, sender_name: str, position: str, company: str
) -> str:
    """Get email template by type.

    Args:
        template_type: Type of template ('template1', 'template2', or 'template3').
        sender_name: Applicant's full name.
        position: Job position being applied for.
        company: Company name.

    Returns:
        Formatted email body string.

    Raises:
        ValueError: If template_type is not recognized.
    """
    if template_type not in TEMPLATE_OPTIONS:
        raise ValueError(
            f"Invalid template type: {template_type}. "
            f"Choose from: {', '.join(TEMPLATE_OPTIONS.keys())}"
        )

    template_func = TEMPLATE_OPTIONS[template_type]
    return template_func(sender_name, position, company)
