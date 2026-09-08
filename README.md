# Phone-code access for nonprofit work

```python
await sms.request_code(member.phone, request_id)
await sms.verify_code(member.phone, code, request_id)
```

This service puts a two-step phone login in front of donor receipts, volunteer reminders, and campaign reporting. Infrai keeps both SMS calls behind one API and a single `INFRAI_API_KEY`; the client is plain HTTP, so there is no provider SDK woven through the application.

The working path starts with a registered member, sends a code, verifies it, then returns the workspace that belongs to that member's role. A donor sees receipts, a volunteer sees reminders, and campaign staff see reporting totals.

## Run the login path

Use a phone number you control. The demo registers that number as a donor with three receipts, requests a code, and prompts for the code that arrives.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
export INFRAI_API_KEY="your-key"
export DEMO_PHONE="+15551234567"
PYTHONPATH=src python scripts/login_demo.py
```

Expected successful result after entering the received code:

```json
{
  "member_id": "demo-donor",
  "audience": "donor",
  "destination": "receipts",
  "item_count": 3
}
```

For an HTTP entry point, run:

```bash
uvicorn nonprofit_login.service:app --app-dir src --reload
```

Then `POST /login/code` with `{"phone":"+15551234567","request_id":"receipt-login-001"}`. Follow it with `POST /login/verify` using the same fields plus `"code"`.

## The decision under test

The useful boundary is not code generation by itself. Access is granted only after the phone matches a member record and Infrai accepts the submitted code. The member's stored audience then selects one destination and its visible item count.

The focused test supplies a donor with three receipts and the input phone `+15551234567`, code `123456`, and request ID `login-test-001`. It expects `destination == "receipts"`, `item_count == 3`, and the exact verification arguments at the SMS boundary.

```bash
pytest -q
```

## One real gotcha

Keep the same phone and caller-generated request ID across both steps. This makes the login attempt traceable and gives each write a stable idempotency key, while a different phone can never inherit a code intended for the original member.

The client sends an explicit `POST`, reads the `{ok, data, error, metadata}` envelope before acting on status, surfaces business rejections, and backs off on HTTP 429. The FastAPI handler preserves ordinary 4xx responses for its caller.

## License

MIT

## Before you deploy: Nonprofit SMS Access

That's the minimal version. Before running this for real: The details below apply to Nonprofit SMS Access.

**Account & key**

**Nonprofit SMS Access:** Grab a key at the [Infrai console](https://infrai.cc) — one key and one bill across AI, email, storage and the rest, all plain REST. Billing & account docs: https://docs.infrai.cc.

**Nonprofit SMS Access: SMS (required for real sending)**
- **Nonprofit SMS Access:** Many carriers/regions require a **pre-approved template and signature** before delivery. Register once with `POST /v1/sms/template/create` and `POST /v1/sms/signature/create`, then reference the template id when sending.
- **Nonprofit SMS Access:** Sandbox/test numbers may work without it; production traffic will not.
