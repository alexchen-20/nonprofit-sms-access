from __future__ import annotations

import asyncio
import os

from nonprofit_login.access_service import CodeRequest, CodeVerification, MemberDirectory, MemberRecord, NonprofitLogin
from nonprofit_login.infrai_sms import InfraiSms


async def main() -> None:
    phone = os.environ.get("DEMO_PHONE", "")
    if not phone:
        raise RuntimeError("DEMO_PHONE is required")

    login = NonprofitLogin(
        InfraiSms(),
        MemberDirectory([MemberRecord(member_id="demo-donor", phone=phone, audience="donor", receipt_count=3)]),
    )
    request_id = "demo-receipts-001"
    print(await login.send_code(CodeRequest(phone=phone, request_id=request_id)))
    code = input("SMS code: ").strip()
    result = await login.verify(CodeVerification(phone=phone, request_id=request_id, code=code))
    print(result.model_dump_json(indent=2))


if __name__ == "__main__":
    asyncio.run(main())

