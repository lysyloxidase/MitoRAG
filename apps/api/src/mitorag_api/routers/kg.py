"""Knowledge graph exploration endpoint boundary."""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter()


@router.get("/status")
def kg_status() -> dict[str, str]:
    return {"status": "phase_3_not_wired"}

