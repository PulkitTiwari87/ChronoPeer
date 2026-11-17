"""FastAPI dependencies: database session, settings and the current operating role.

There is no authentication (spec 4.3 / 13.8). The role comes from the X-Role header and is enforced
per endpoint, which separates the two modes but does not prove who the caller is.
"""
from fastapi import Depends, Header, HTTPException, Request

from .services.audit import Actor


def get_db(request: Request):
    db = request.app.state.session_factory()
    try:
        yield db
    finally:
        db.close()


def get_settings(request: Request):
    return request.app.state.settings


def get_actor(x_role: str = Header("investigator"), x_actor: str = Header("")) -> Actor:
    role = x_role.strip().lower()
    if role not in ("investigator", "reviewer"):
        raise HTTPException(400, "X-Role must be 'investigator' or 'reviewer'")
    return Actor(role, x_actor.strip()[:80] or role.capitalize())


def _require(role: str):
    def dependency(actor: Actor = Depends(get_actor)) -> Actor:
        if actor.role != role:
            raise HTTPException(403, f"This action needs {role} mode (current mode: {actor.role})")
        return actor

    return dependency


investigator_only = _require("investigator")
reviewer_only = _require("reviewer")
