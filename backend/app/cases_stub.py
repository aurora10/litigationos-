"""Placeholder case stubs so D02's auth guard can be acceptance-tested.

The real case management ships in D03. THIS MODULE IS REPLACED BY D03.
"""
from fastapi import APIRouter

router = APIRouter(prefix="/cases", tags=["cases-stub"])


@router.get("")
def list_cases():
    return []
