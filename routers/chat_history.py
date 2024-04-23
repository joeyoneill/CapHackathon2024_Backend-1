# Imports
from fastapi import APIRouter
import os
from dotenv import load_dotenv
import logging

# Load Environment Variables
load_dotenv('.env')

# Configure the root logger to log all messages
logging.basicConfig(level=logging.DEBUG)

###############################################################################
# Initialize Router
###############################################################################
router = APIRouter()


###############################################################################
# Endpoints
###############################################################################