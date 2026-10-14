from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


app = FastAPI(
    title="UNN E-Library API",
    description="Backend API for the University of Nigeria E-Library System",
    version="1.0.0"
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {
        "message": "UNN E-Library API is running"
    }


@app.get("/health")
def health_check():
    return {
        "status": "healthy"
    }