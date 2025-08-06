from pydantic import BaseModel, EmailStr

class EmailCodeCreate(BaseModel):
    email: EmailStr

class EmailCodeVerify(BaseModel):
    """Payload for verifying an emailed code.

    The email address must match the authenticated user's email.
    """

    email: EmailStr
    code: str
