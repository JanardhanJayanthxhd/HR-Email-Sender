import pytest

from src.storage.db import get_applications_by_hr_email, init_db, insert_application


@pytest.mark.asyncio
async def test_get_applications_by_hr_email_matches_exact_address_in_recipient_list(tmp_path):
    db_path = tmp_path / "applications.db"
    await init_db(db_path)
    await insert_application(
        db_path, "Acme", "Backend Developer", "hr@acme.com, recruiter@acme.com",
        "Subject", "Body", "sent",
    )
    await insert_application(
        db_path, "Other", "Frontend Developer", "HR@ACME.COM",
        "Subject", "Body", "sent",
    )
    await insert_application(
        db_path, "Skipped Co", "Designer", "hr@acme.com",
        "Subject", "Body", "skipped",
    )
    await insert_application(
        db_path, "Acme Subsidiary", "Engineer", "not-hr@acme.com",
        "Subject", "Body", "sent",
    )

    applications = await get_applications_by_hr_email(db_path, "Hr@Acme.com")

    assert {company for company, _, _ in applications} == {"Acme", "Other"}
    assert all(role and timestamp for _, role, timestamp in applications)
