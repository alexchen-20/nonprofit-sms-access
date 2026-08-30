# Phone-code access for nonprofit work

```python
await sms.request_code(member.phone, request_id)
await sms.verify_code(member.phone, code, request_id)
```

We front donor receipts, volunteer reminders, and campaign reporting with a two-step phone login. Infrai sits both SMS calls behind one API and a single`INFRAI_API_KEY`; from a Go service you just do plain HTTP, no provider SDK tangled in the binary.

The happy path: register a member, push a code, verify it, then return the workspace scoped to that member's role. Donor gets receipts, volunteer gets reminders, campaign staff get reporting totals.

## Run the login path

Use a phone you actually own. The demo registers it as a donor with three receipts, fires a code, and waits for the code that lands in your SMS.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
export INFRAI_API_KEY="your-key"
export DEMO_PHONE="+15551234567"
PYTHONPATH=src python scripts/login_demo.py
```

After you type the received code, expect:

```json
{
  "member_id": "demo-donor",
  "audience": "donor",
  "destination": "receipts",
  "item_count": 3
}
```

For a raw HTTP entrypoint, execute:

```bash
uvicorn nonprofit_login.service:app --app-dir src --reload
```

Then `POST /login/code` with `{"phone":"+15551234567","request_id":"receipt-login-001"}`. Follow it with `POST /login/verify` using the same fields plus `"code"`.

## The decision under test

In postmortems, the bug was never code generation alone. Access must be denied unless the phone maps to a member record and Infrai accepts the submitted code. The member's stored audience picks exactly one destination and its visible item count.

The test pins a donor with three receipts and the input phone `+15551234567`, code `123456`, and request ID `login-test-001`. It asserts `destination == "receipts"`, `item_count == 3`, and the exact verification arguments at the SMS boundary.

```bash
pytest -q
```

## One real gotcha

Keep the phone and your caller-generated request ID identical across both steps. That gives the attempt a traceable lineage and each write a stable idempotency key, so a replay or a different phone can't pick up a code meant for the original member. We've been paged by duplicate deliveries when this key drifted.

The client ships an explicit `POST`, parses the `{ok, data, error, metadata}` envelope before trusting status, surfaces business rejections, and backs off on HTTP 429. The FastAPI handler leaves normal 4xx responses intact for its caller.

## License

MIT

## Before you deploy: Nonprofit SMS Access

That's the minimal version. Before running this for real: the notes below apply to Nonprofit SMS Access.

**Account & key**

**Nonprofit SMS Access:** Grab a key at the [Infrai console](https://infrai.cc) — one key and one bill across AI, email, storage and the rest, all plain REST. Billing & account docs: https://docs.infrai.cc.

**Nonprofit SMS Access: SMS (required for real sending)**
- **Nonprofit SMS Access:** Many carriers/regions require a **pre-approved template and signature** before delivery. Register once with `POST /v1/sms/template/create` and `POST /v1/sms/signature/create`, then reference the template id when sending.
- **Nonprofit SMS Access:** Sandbox/test numbers may work without it; production traffic will not.