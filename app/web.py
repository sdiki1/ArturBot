from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime, timezone
from html import escape

import uvicorn
from fastapi import Depends, FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, PlainTextResponse, RedirectResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.models import Payment, PaymentStatus, User
from app.db.session import get_session
from app.services.payments import PaymentService
from app.services.texts import TextService
from app.utils.text import user_display_name

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    yield


app = FastAPI(title="PRO Возможности Payment Web", lifespan=lifespan)


@app.get("/health", response_class=PlainTextResponse)
async def health() -> str:
    return "ok"


def _dt(value: datetime | None) -> str:
    if value is None:
        return "—"
    return value.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


@app.get("/admin", response_class=HTMLResponse)
async def admin_panel(token: str | None = None, session: AsyncSession = Depends(get_session)) -> HTMLResponse:
    if settings.admin_web_token and token != settings.admin_web_token:
        raise HTTPException(status_code=403, detail="forbidden")

    text_service = TextService(session)
    now = datetime.now(timezone.utc)
    total_users = int((await session.execute(select(func.count(User.id)))).scalar_one())
    active_subscriptions = int(
        (
            await session.execute(
                select(func.count(User.id)).where(
                    User.subscription_expires_at.is_not(None),
                    User.subscription_expires_at > now,
                )
            )
        ).scalar_one()
    )
    total_payments = int((await session.execute(select(func.count(Payment.id)))).scalar_one())
    paid_payments = int(
        (
            await session.execute(
                select(func.count(Payment.id)).where(Payment.status == PaymentStatus.paid),
            )
        ).scalar_one()
    )

    recent_users = list((await session.execute(select(User).order_by(User.created_at.desc()).limit(20))).scalars().all())
    recent_payments = list((await session.execute(select(Payment).order_by(Payment.created_at.desc()).limit(20))).scalars().all())
    admin_items = await text_service.list_for_admin()

    no_data_text = await text_service.resolve("web.admin_no_data")
    users_html = "".join(
        (
            "<li>"
            f"{escape(user_display_name(user))}"
            f"{' @' + escape(user.username) if user.username else ''}"
            f" (id: {user.telegram_id})"
            f" — {_dt(user.created_at)}"
            "</li>"
        )
        for user in recent_users
    ) or f"<li>{escape(no_data_text)}</li>"
    payments_html = "".join(
        (
            "<li>"
            f"payment={escape(payment.external_payment_id)} | user_id={payment.user_id} | "
            f"{payment.amount} {escape(payment.currency)} | {escape(payment.status.value)} | "
            f"{_dt(payment.created_at)}"
            "</li>"
        )
        for payment in recent_payments
    ) or f"<li>{escape(no_data_text)}</li>"

    token_hint = ""
    if not settings.admin_web_token:
        token_hint = f'<p class="hint">{escape(await text_service.resolve("web.admin_no_token_hint"))}</p>'

    token_input = f'<input type="hidden" name="token" value="{escape(token)}" />' if token else ""
    text_forms_html = []
    for item in admin_items:
        value = item.override_value if item.override_value is not None else item.effective_value
        text_forms_html.append(
            (
                '<div class="text-row" id="text-{key}">'
                "<form method=\"post\" action=\"/admin/texts\">"
                f"{token_input}"
                f"<input type=\"hidden\" name=\"key\" value=\"{escape(item.key)}\" />"
                f"<label><b>{escape(item.key)}</b></label>"
                f"<div class=\"default\">По умолчанию: {escape(item.default_value) if item.default_value else '—'}</div>"
                f"<textarea name=\"value\" rows=\"4\">{escape(value)}</textarea>"
                "<div class=\"actions\">"
                "<button type=\"submit\" name=\"action\" value=\"save\">Сохранить</button>"
                "<button type=\"submit\" name=\"action\" value=\"reset\" class=\"secondary\">Сброс</button>"
                "</div>"
                "</form>"
                "</div>"
            ).format(key=escape(item.key))
        )
    text_forms = "".join(text_forms_html)

    html = f"""
<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{escape(await text_service.resolve("web.admin_title"))}</title>
  <style>
    body {{ margin: 0; background: #111318; color: #f4f5f7; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; }}
    .wrap {{ max-width: 980px; margin: 24px auto; padding: 0 16px 24px; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 12px; margin-bottom: 16px; }}
    .card {{ background: #1a1f29; border: 1px solid #2d3442; border-radius: 12px; padding: 14px; }}
    .title {{ opacity: .8; font-size: 13px; margin-bottom: 6px; }}
    .value {{ font-size: 26px; font-weight: 700; }}
    h1, h2 {{ margin: 0 0 12px; }}
    ul {{ margin: 0; padding-left: 18px; }}
    li {{ margin-bottom: 8px; word-break: break-word; }}
    .hint {{ color: #ffd27d; }}
    .text-row {{ background: #171b23; border: 1px solid #2d3442; border-radius: 10px; padding: 12px; margin-bottom: 10px; }}
    .text-row label {{ display: block; margin-bottom: 6px; }}
    .text-row .default {{ color: #a8afbe; font-size: 12px; margin-bottom: 8px; white-space: pre-wrap; }}
    .text-row textarea {{ width: 100%; box-sizing: border-box; border-radius: 8px; border: 1px solid #2d3442; background: #0f131a; color: #f4f5f7; padding: 8px; }}
    .text-row .actions {{ display: flex; gap: 8px; margin-top: 8px; }}
    .text-row button {{ border: 0; border-radius: 8px; padding: 8px 12px; font-weight: 600; cursor: pointer; }}
    .text-row button.secondary {{ background: #2d3442; color: #fff; }}
  </style>
</head>
<body>
  <div class="wrap">
    <h1>{escape(await text_service.resolve("web.admin_title"))}</h1>
    {token_hint}
    <div class="grid">
      <div class="card"><div class="title">{escape(await text_service.resolve("web.admin_total_users_label"))}</div><div class="value">{total_users}</div></div>
      <div class="card"><div class="title">{escape(await text_service.resolve("web.admin_active_subscriptions_label"))}</div><div class="value">{active_subscriptions}</div></div>
      <div class="card"><div class="title">{escape(await text_service.resolve("web.admin_total_payments_label"))}</div><div class="value">{total_payments}</div></div>
      <div class="card"><div class="title">{escape(await text_service.resolve("web.admin_paid_payments_label"))}</div><div class="value">{paid_payments}</div></div>
    </div>
    <div class="card">
      <h2>{escape(await text_service.resolve("web.admin_recent_users_title"))}</h2>
      <ul>{users_html}</ul>
    </div>
    <div class="card" style="margin-top:12px;">
      <h2>{escape(await text_service.resolve("web.admin_recent_payments_title"))}</h2>
      <ul>{payments_html}</ul>
    </div>
    <div class="card" style="margin-top:12px;">
      <h2>{escape(await text_service.resolve("web.admin_texts_title"))}</h2>
      {text_forms}
    </div>
  </div>
</body>
</html>
"""
    return HTMLResponse(content=html)


@app.post("/admin/texts")
async def admin_save_text(
    key: str = Form(...),
    value: str = Form(default=""),
    action: str = Form(default="save"),
    token: str | None = Form(default=None),
    session: AsyncSession = Depends(get_session),
) -> RedirectResponse:
    if settings.admin_web_token and token != settings.admin_web_token:
        raise HTTPException(status_code=403, detail="forbidden")

    text_service = TextService(session)
    if action == "reset":
        await text_service.reset_text(key)
    else:
        await text_service.set_text(key, value)

    suffix = f"?token={token}" if token else ""
    return RedirectResponse(url=f"/admin{suffix}#text-{key}", status_code=303)


@app.get("/pay/{payment_uuid}", response_class=HTMLResponse)
async def payment_page(payment_uuid: str, session: AsyncSession = Depends(get_session)) -> HTMLResponse:
    payment_service = PaymentService(session, settings)
    text_service = TextService(session)
    payment = await payment_service.get_payment(payment_uuid)
    if payment is None:
        raise HTTPException(status_code=404, detail="Payment not found")

    page_title = await text_service.resolve("web.pay_page_title")
    page_wait = await text_service.resolve("web.pay_page_wait")
    page_btn = await text_service.resolve("web.pay_page_button")

    html = f"""
<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{escape(page_title)}</title>
  <style>
    body {{
      margin: 0;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
      background: #101114;
      color: #ffffff;
      min-height: 100vh;
      display: flex;
      align-items: center;
      justify-content: center;
    }}
    .card {{
      width: min(520px, 92vw);
      background: #181a1f;
      border: 1px solid #2e3239;
      border-radius: 18px;
      padding: 28px;
      text-align: center;
    }}
    h1 {{ margin: 0 0 12px; font-size: 28px; }}
    p {{ margin: 0 0 24px; opacity: 0.92; }}
    a {{
      display: inline-block;
      background: #ffffff;
      color: #111;
      text-decoration: none;
      border-radius: 12px;
      padding: 12px 22px;
      font-weight: 600;
    }}
  </style>
</head>
<body>
  <div class="card">
    <h1>{escape(page_title)}</h1>
    <p>{escape(page_wait)}</p>
    <a href="{escape(payment.payment_url)}">{escape(page_btn)}</a>
  </div>
  <script>
    setTimeout(function () {{
      window.location.href = {payment.payment_url!r};
    }}, 2200);
  </script>
</body>
</html>
"""
    return HTMLResponse(content=html)


@app.get("/payments/yoomoney/success", response_class=HTMLResponse)
async def yoomoney_success(label: str, session: AsyncSession = Depends(get_session)) -> HTMLResponse:
    payment_service = PaymentService(session, settings)
    text_service = TextService(session)
    ok = await payment_service.mark_paid_and_extend(label)

    status_text = await text_service.resolve("web.payment_success") if ok else await text_service.resolve("web.payment_not_found")
    back_text = await text_service.resolve("web.payment_back_to_tg")
    return HTMLResponse(
        f"<h2>{escape(status_text)}</h2><p>{escape(back_text)}</p>",
    )


@app.get("/payments/yoomoney/fail", response_class=HTMLResponse)
async def yoomoney_fail(label: str | None = None, session: AsyncSession = Depends(get_session)) -> HTMLResponse:
    if label:
        payment_service = PaymentService(session, settings)
        await payment_service.mark_failed(label)

    text_service = TextService(session)
    fail_text = await text_service.resolve("web.payment_fail")
    retry_text = await text_service.resolve("web.payment_try_again")
    return HTMLResponse(f"<h2>{escape(fail_text)}</h2><p>{escape(retry_text)}</p>")


@app.post("/payments/yoomoney/callback", response_class=PlainTextResponse)
async def yoomoney_callback(
    request: Request,
    notification_type: str = Form(default=""),
    operation_id: str = Form(default=""),
    amount: str = Form(default=""),
    currency: str = Form(default=""),
    datetime_value: str = Form(default="", alias="datetime"),
    sender: str = Form(default=""),
    codepro: str = Form(default=""),
    sha1_hash: str = Form(default=""),
    label: str = Form(default=""),
    session: AsyncSession = Depends(get_session),
) -> PlainTextResponse:
    payload = {
        "notification_type": notification_type,
        "operation_id": operation_id,
        "amount": amount,
        "currency": currency,
        "datetime": datetime_value,
        "sender": sender,
        "codepro": codepro,
        "sha1_hash": sha1_hash,
        "label": label,
    }

    payment_service = PaymentService(session, settings)
    if not payment_service.verify_yoomoney_notification(payload):
        return PlainTextResponse("forbidden", status_code=403)

    if label:
        await payment_service.mark_paid_and_extend(label)

    _ = request
    return PlainTextResponse("ok")


if __name__ == "__main__":
    uvicorn.run("app.web:app", host="0.0.0.0", port=8000, reload=False)
