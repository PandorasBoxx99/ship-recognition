#!/usr/bin/env python3
"""Convenience entry point for the Ship Recognition backend."""

import uvicorn
from backend.config import settings

if __name__ == "__main__":
    uvicorn.run(
        "backend.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )
