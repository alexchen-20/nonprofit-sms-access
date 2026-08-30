from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

from .access_service import CodeRequest, CodeVerification, MemberDirectory, MemberRecord, NonprofitLogin
from .infrai_sms import InfraiError, InfraiSms


app = FastAPI(title="Nonprofit phone login")

members = MemberDirectory(
    [
        MemberRecord(member_id="donor-104", phone="+15551234567", audience="donor", receipt_count=3),
        MemberRecord(member_id="vol-208", phone="+15551234568", audience="volunteer", reminder_count=2),
        MemberRecord(member_id="staff-312", phone="+15551234569", audience="campaign_staff", campaign_count=4),
    ]
)


def login_service() -> NonprofitLogin:
    return NonprofitLogin(InfraiSms(), members)


@app.exception_handler(InfraiError)
async def infrai_error_handler(_request: object, exc: InfraiError) -> JSONResponse:
    caller_status = exc.status_code if 400 <= exc.status_code < 500 else 502
    return JSONResponse(status_code=caller_status, content={"detail": str(exc)})


@app.post("/login/code", status_code=202)
async def request_login_code(command: CodeRequest) -> dict[str, str]:
    try:
        state = await login_service().send_code(command)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"state": state}


@app.post("/login/verify")
async def verify_login_code(command: CodeVerification) -> dict:
    try:
        result = await login_service().verify(command)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"state": "verified", "workspace": result.model_dump()}

