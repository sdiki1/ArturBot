from __future__ import annotations

from contextlib import asynccontextmanager
from html import escape

import uvicorn
from fastapi import Depends, FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.session import get_session
from app.services.payments import PaymentService

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    yield


app = FastAPI(title="PRO Возможности Payment Web", lifespan=lifespan)


@app.get("/health", response_class=PlainTextResponse)
async def health() -> str:
    return "ok"


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
