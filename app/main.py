from fastapi import FastAPI
from app.routers import auth_router, patient_router

app = FastAPI(title="Hospital Patient API")

# Include the routes we are about to create
app.include_router(auth_router.router, prefix="/auth", tags=["Authentication"])
app.include_router(patient_router.router, prefix="/patients", tags=["Patient Data"])

@app.get("/")
def read_root():
    return {"message": "Hospital API is running"}