# Imports
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

# In-App Dependencies
from routers.stream import router as stream_router
from routers.auth import router as auth_router
from routers.chat_history import router as chat_history_router


###############################################################################
# Initialize FastAPI
###############################################################################
app = FastAPI()


###############################################################################
# Routes
###############################################################################
app.include_router(stream_router)
app.include_router(auth_router)
app.include_router(chat_history_router)


###############################################################################
# CORS Middleware
###############################################################################
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


###############################################################################
# Root Endpoint
###############################################################################
# Default to docs
@app.get("/", tags=["General"])
def root_route():
    return RedirectResponse(url="/docs")