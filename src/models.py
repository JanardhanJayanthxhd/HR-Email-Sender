from pydantic import BaseModel, ConfigDict, Field


class JobPost(BaseModel):
    """Job details extracted from pasted job text."""

    model_config = ConfigDict(str_strip_whitespace=True)

    company: str = Field(min_length=1, description="Company name")
    role: str = Field(min_length=1, description="Job role/title")
    requirements_summary: str = Field(min_length=1, description="Short requirements summary")
    key_requirements: list[str] = Field(default_factory=list)
    hr_email: str = Field(min_length=3)


class EmailDraft(BaseModel):
    """Generated application email."""

    model_config = ConfigDict(str_strip_whitespace=True)

    subject: str = Field(min_length=1)
    body: str = Field(min_length=1)
