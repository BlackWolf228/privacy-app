WHITELISTED_EMAILS = {
    "test1@test.com",
    "andrei@payinprivacy.com",
    "admin@example.com",
    "dan@payinprivacy.com",
    
}

def is_email_whitelisted(email: str) -> bool:
    return email.lower() in WHITELISTED_EMAILS