from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime, timezone
from html import escape

import uvicorn
from fastapi import Depends, FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, PlainTextResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.models import Payment, PaymentStatus, User
from app.db.session import get_session
from app.services.payments import PaymentService
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
    ) or "<li>Нет данных</li>"
    payments_html = "".join(
        (
            "<li>"
            f"payment={escape(payment.external_payment_id)} | user_id={payment.user_id} | "
            f"{payment.amount} {escape(payment.currency)} | {escape(payment.status.value)} | "
            f"{_dt(payment.created_at)}"
            "</li>"
        )
        for payment in recent_payments
    ) or "<li>Нет данных</li>"

    token_hint = ""
    if not settings.admin_web_token:
        token_hint = '<p class="hint">ADMIN_WEB_TOKEN не задан: доступ открыт без токена.</p>'

    html = f"""
<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Админ-панель</title>
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
  </style>
</head>
<body>
  <div class="wrap">
    <h1>Админ-панель</h1>
    {token_hint}
    <div class="grid">
      <div class="card"><div class="title">Всего пользователей</div><div class="value">{total_users}</div></div>
      <div class="card"><div class="title">Активных подписок</div><div class="value">{active_subscriptions}</div></div>
      <div class="card"><div class="title">Всего платежей</div><div class="value">{total_payments}</div></div>
      <div class="card"><div class="title">Оплаченных платежей</div><div class="value">{paid_payments}</div></div>
    </div>
    <div class="card">
      <h2>Последние пользователи</h2>
      <ul>{users_html}</ul>
    </div>
    <div class="card" style="margin-top:12px;">
      <h2>Последние платежи</h2>
      <ul>{payments_html}</ul>
    </div>
  </div>
</body>
</html>
"""
    return HTMLResponse(content=html)


@app.get("/pay/{payment_uuid}", response_class=HTMLResponse)
async def payment_page(payment_uuid: str, session: AsyncSession = Depends(get_session)) -> HTMLResponse:
    payment_service = PaymentService(session, settings)
    payment = await payment_service.get_payment(payment_uuid)
    if payment is None:
        raise HTTPException(status_code=404, detail="Payment not found")

    html = f"""
<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Переход к оплате</title>
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
    <h1>Переход к оплате</h1>
    <p>Через несколько секунд тут будет страница оплаты...</p>
    <a href="{escape(payment.payment_url)}">Перейти</a>
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
    ok = await payment_service.mark_paid_and_extend(label)

    status_text = "Оплата подтверждена. Подписка продлена." if ok else "Оплата не найдена."
    return HTMLResponse(
        f"<h2>{escape(status_text)}</h2><p>Можно вернуться в Telegram.</p>",
    )


@app.get("/payments/yoomoney/fail", response_class=HTMLResponse)
async def yoomoney_fail(label: str | None = None, session: AsyncSession = Depends(get_session)) -> HTMLResponse:
    if label:
        payment_service = PaymentService(session, settings)
        await payment_service.mark_failed(label)

    return HTMLResponse("<h2>Оплата не завершена.</h2><p>Можно попробовать снова в боте.</p>")


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
