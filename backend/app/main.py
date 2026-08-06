from fastapi import FastAPI
app = FastAPI(
    title = "AI Interview Coach API",
    description = "This API provides endpoints for an AI Interview Coach application, allowing users to practice interview questions and receive feedback.",
    version = "1.0.0",
)

@app.get("/")
def read_root():
    return {"message": "Welcome to the AI Interview Coach API!"}
