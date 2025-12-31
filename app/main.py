from fastapi import FastAPI

app = FastAPI(
    title="FastAPI Starter",
    description="A clean FastAPI project",
    version="0.1.0"
)

@app.get("/")
async def root():
    return {"message": "Hello FastAPI 🚀"}