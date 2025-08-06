from pydantic import BaseModel, EmailStr

class EmailCodeCreate(BaseModel):
    email: EmailStr

class EmailCodeVerify(BaseModel):
    email: EmailStr
    code: str
