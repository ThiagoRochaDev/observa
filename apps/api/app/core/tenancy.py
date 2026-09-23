from __future__ import annotations

from collections.abc import AsyncIterator

from fastapi import Depends, Header, HTTPException

from app.core import db
from app.core.security import require_api_key


async def require_tenancy(
    x_observa_tenancy_id: str | None = Header(default=None, alias="X-Observa-Tenancy-ID"),
    x_observa_company_id: str | None = Header(default=None, alias="X-Observa-Company-ID"),
    actor: dict = Depends(require_api_key),
) -> AsyncIterator[dict]:
    tenancy_id = x_observa_tenancy_id or db.DEFAULT_TENANCY_ID
    tenancy = db.get_tenancy(tenancy_id)
    if not tenancy or not tenancy["enabled"]:
        raise HTTPException(status_code=404, detail="Tenancy not found or disabled")
    company = db.get_company(tenancy["company_id"])
    if not company or not company["enabled"]:
        raise HTTPException(status_code=404, detail="Company not found or disabled")
    if x_observa_company_id and x_observa_company_id != company["id"]:
        raise HTTPException(status_code=409, detail="Tenancy does not belong to selected company")
    member = None
    if not actor["is_platform_admin"]:
        member = db.get_company_member(company["id"], actor["subject"])
        if not member:
            raise HTTPException(status_code=403, detail="Caller has no access to this company")

    token = db.set_current_tenancy(tenancy_id)
    try:
        yield {"company": company, "tenancy": tenancy, "actor": actor, "member": member}
    finally:
        db.reset_current_tenancy(token)


def require_tenancy_operator(context: dict = Depends(require_tenancy)) -> dict:
    if context["actor"]["is_platform_admin"]:
        return context
    if not context["member"] or context["member"]["role"] not in {"owner", "admin", "operator"}:
        raise HTTPException(status_code=403, detail="Operator role required")
    return context


def require_tenancy_admin(context: dict = Depends(require_tenancy)) -> dict:
    if context["actor"]["is_platform_admin"]:
        return context
    if not context["member"] or context["member"]["role"] not in {"owner", "admin"}:
        raise HTTPException(status_code=403, detail="Company owner or admin role required")
    return context


def require_platform_admin(actor: dict = Depends(require_api_key)) -> dict:
    if not actor["is_platform_admin"]:
        raise HTTPException(status_code=403, detail="Platform administrator required")
    return actor
