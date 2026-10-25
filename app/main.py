from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers.auth import router as auth_router
from app.routers.resources import router as resources_router
from app.routers.notifications import router as notifications_router
from app.routers.requests import router as requests_router
from app.routers.reading_lists import router as reading_lists_router
from app.routers.admin import router as admin_router
from app.routers.reports import router as reports_router
from app.routers.personalization import router as personalization_router
from app.routers.reading_progress import router as reading_progress_router

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
app.include_router(requests_router)
app.include_router(reading_lists_router)
app.include_router(admin_router)
app.include_router(reports_router)
app.include_router(personalization_router)
app.include_router(reading_progress_router)

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