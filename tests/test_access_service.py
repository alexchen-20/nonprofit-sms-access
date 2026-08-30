from __future__ import annotations

import pytest

from nonprofit_login.access_service import CodeVerification, MemberDirectory, MemberRecord, NonprofitLogin


class AcceptedSms:
    def __init__(self) -> None:
        self.verified: tuple[str, str, str] | None = None

    async def request_code(self, to: str, request_id: str) -> dict:
        return {"message_id": "msg-test"}

    async def verify_code(self, to: str, code: str, request_id: str) -> dict:
        self.verified = (to, code, request_id)
        return {"verified": True}


@pytest.mark.asyncio
async def test_verified_donor_lands_on_receipts_with_visible_count() -> None:
    sms = AcceptedSms()
    login = NonprofitLogin(
        sms,
        MemberDirectory(
            [MemberRecord(member_id="donor-104", phone="+15551234567", audience="donor", receipt_count=3)]
        ),
    )

    result = await login.verify(
        CodeVerification(phone="+15551234567", code="123456", request_id="login-test-001")
    )

    assert result.destination == "receipts"
    assert result.item_count == 3
    assert sms.verified == ("+15551234567", "123456", "login-test-001")


@pytest.mark.asyncio
async def test_unknown_phone_never_reaches_sms_boundary() -> None:
    sms = AcceptedSms()
    login = NonprofitLogin(sms, MemberDirectory([]))

    with pytest.raises(LookupError, match="not registered"):
        await login.verify(CodeVerification(phone="+15551234567", code="123456", request_id="login-test-002"))

    assert sms.verified is None

