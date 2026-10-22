from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers.auth import router as auth_router
from app.routers.resources import router as resources_router
from app.routers.notifications import router as notifications_router

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

app.include_router(auth_router)
app.include_router(resources_router)
app.include_router(notifications_router)

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