from fastapi import FastAPI
from main import app

from a2wsgi import ASGIMiddleware

application = ASGIMiddleware(app)