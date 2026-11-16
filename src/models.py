from pydantic import BaseModel, ConfigDict, Field


class JobPost(BaseModel):
    """Job details extracted from pasted job text."""

    model_config = ConfigDict(str_strip_whitespace=True)

    company: str = Field(min_length=1, description="Company name")
    role: str = Field(min_length=1, description="Job role/title")
    hr_emails: list[str] = Field(min_length=1)


class JobPostExtraction(BaseModel):
    """Company and role fields extracted by the LLM."""

    model_config = ConfigDict(str_strip_whitespace=True)

    company: str = Field(min_length=1, description="Company name")
    role: str = Field(min_length=1, description="Job role/title")


class EmailDraft(BaseModel):
    """Generated application email."""

    model_config = ConfigDict(str_strip_whitespace=True)

    subject: str = Field(min_length=1)
    body: str = Field(min_length=1)
