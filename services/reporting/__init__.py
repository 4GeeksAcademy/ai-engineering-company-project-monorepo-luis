"""Reporting services module for Nexova business stakeholders.

Exposes thin API endpoints delegating to data/pipelines without coupling ETL logic.
"""

from services.reporting.router import router

__all__ = ["router"]
