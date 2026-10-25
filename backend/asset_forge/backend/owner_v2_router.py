"""Opt-in V2 routes. Never accepted by or forwarded to legacy execution APIs."""

from fastapi import APIRouter, Header, HTTPException, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from pydantic import BaseModel, ConfigDict, Field

from .owner_v2 import OwnerV2, Unauthorized, Unavailable, require_enabled

class OwnerV2Route(APIRoute):
    """Sanitize validation failures before they reach the app's default handler."""

    def get_route_handler(self):
        handler = super().get_route_handler()

        async def sanitized_handler(request: Request):
            try:
                return await handler(request)
            except RequestValidationError:
                return JSONResponse(
                    status_code=422,
                    content={"detail": "Invalid input"},
                    headers={"Cache-Control": "no-store"},
                )

        return sanitized_handler


router = APIRouter(prefix="/auth/owner-v2", tags=["Owner Identity V2"], route_class=OwnerV2Route)
service = OwnerV2()


class EmailRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: str = Field(min_length=3, max_length=254)


class ProofRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    challenge_id: str = Field(min_length=36, max_length=36)
    browser_proof: str = Field(min_length=43, max_length=43)
    code: str = Field(min_length=43, max_length=43)


def invoke(response: Response, operation, *args):
    response.headers["Cache-Control"] = "no-store"
    try:
        require_enabled()  # Still enforced when service is injected by tests.
        return operation(*args)
    except Unavailable:
        raise HTTPException(503, "Owner V2 is unavailable", headers={"Cache-Control": "no-store"}) from None
    except Unauthorized:
        raise HTTPException(401, "Invalid or expired proof", headers={"Cache-Control": "no-store"}) from None
    except ValueError:
        raise HTTPException(422, "Invalid input", headers={"Cache-Control": "no-store"}) from None


@router.post("/request", status_code=202)
def request_code(body: EmailRequest, response: Response):
    return invoke(response, service.request, body.email)


@router.post("/verify")
def verify_code(body: ProofRequest, response: Response):
    return invoke(response, service.verify, body.challenge_id, body.browser_proof, body.code)


@router.get("/session")
def session_status(response: Response, authorization: str | None = Header(default=None)):
    return invoke(response, service.authenticate, authorization)


@router.post("/logout", status_code=204)
def logout(response: Response, authorization: str | None = Header(default=None)):
    invoke(response, service.logout, authorization)
