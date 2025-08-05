from fastapi import FastAPI
from app.routes import auth, user

app = FastAPI(title="Privacy Fintech API")

app.include_router(auth.router)
app.include_router(user.router)

@app.get("/")
async def root():
    return {"message": "Privacy Fintech Backend Running"}