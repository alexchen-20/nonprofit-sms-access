from __future__ import annotations

from typing import Awaitable, Callable, Literal, Protocol

from pydantic import BaseModel, Field


Audience = Literal["donor", "volunteer", "campaign_staff"]


class CodeRequest(BaseModel):
    phone: str = Field(pattern=r"^\+[1-9]\d{7,14}$")
    request_id: str = Field(min_length=8, max_length=80)


class CodeVerification(CodeRequest):
    code: str = Field(pattern=r"^\d{4,8}$")


class MemberRecord(BaseModel):
    member_id: str
    phone: str
    audience: Audience
    receipt_count: int = 0
    reminder_count: int = 0
    campaign_count: int = 0


class LoginResult(BaseModel):
    member_id: str
    audience: Audience
    destination: Literal["receipts", "reminders", "campaign-reporting"]
    item_count: int


class SmsBoundary(Protocol):
    request_code: Callable[[str, str], Awaitable[dict]]
    verify_code: Callable[[str, str, str], Awaitable[dict]]


class MemberDirectory:
    def __init__(self, records: list[MemberRecord]) -> None:
        self._by_phone = {record.phone: record for record in records}

    def find(self, phone: str) -> MemberRecord | None:
        return self._by_phone.get(phone)


class NonprofitLogin:
    def __init__(self, sms: SmsBoundary, members: MemberDirectory) -> None:
        self.sms = sms
        self.members = members

    async def send_code(self, command: CodeRequest) -> str:
        member = self.members.find(command.phone)
        if member is None:
            raise LookupError("phone is not registered")
        await self.sms.request_code(command.phone, command.request_id)
        return "code_sent"

    async def verify(self, command: CodeVerification) -> LoginResult:
        member = self.members.find(command.phone)
        if member is None:
            raise LookupError("phone is not registered")
        await self.sms.verify_code(command.phone, command.code, command.request_id)

        workspace = {
            "donor": ("receipts", member.receipt_count),
            "volunteer": ("reminders", member.reminder_count),
            "campaign_staff": ("campaign-reporting", member.campaign_count),
        }
        destination, item_count = workspace[member.audience]
        return LoginResult(
            member_id=member.member_id,
            audience=member.audience,
            destination=destination,
            item_count=item_count,
        )
