# Imports
from fastapi import APIRouter, status, Depends
from dotenv import load_dotenv
import os

# In-App Dependencies
from dependencies import jwt_dependency

# Load Environment Variables
load_dotenv('.env')

###############################################################################
# Initialize Router
###############################################################################
router = APIRouter()

###############################################################################
# Endpoints
###############################################################################
