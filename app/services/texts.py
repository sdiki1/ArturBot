from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repo.text_repo import TextRepo


DEFAULT_TEXTS: dict[str, str] = {
    "start.first_name_fallback": "друг",
    "start.welcome": (
        "Добрый день, {first_name}!\n\n"
        "Меня зовут {mentor_name}\n"
        "@{mentor_username}, я твой наставник и проводник в мир цифровых решений и онлайн-образования.\n\n"
        "С радостью помогу разобраться в системе, отвечу на любые вопросы и начнем двигаться к твоим результатам вместе!"
    ),
    "start.chat_not_set_alert": "Чат пока не подключен.",
    "cabinet.title": "Личный кабинет",
    "referral.my_link": "Моя реф.ссылка:\n\n{link}",
    "referral.no_inviter_self": "У Вас нет пригласившего пользователя.\n\nВаш личный профиль:\n{self_name}{self_username_line}",
    "referral.invited_by": "Вас пригласил:\n{inviter_name}{inviter_username_line}",
    "subscribers.header": "Количество подписчиков: {count}\n\nМои подписчики:",
    "subscribers.empty_item": "- Пока нет подписчиков",
    "subscription.first_name_fallback": "Пользователь",
    "subscription.days_left": "{first_name}, у Вас осталось дней подписки: {days_left}",
    "subscription.payment_opened": (
        "Переход к оплате открыт.\n\n"
        "Если страница оплаты не открылась автоматически, перейдите по ссылке:\n{intermediate_url}"
    ),
    "photos.slot_caption": "Ваше фото",
    "photos.choose_slot": "Нажмите кнопку ниже, чтобы изменить фото.",
    "photos.ask_new_slot": "Отправьте новое фото.",
    "photos.updated": "Фото успешно обновлено.",
    "photos.expected_photo": "Пожалуйста, отправьте фото.",
    "profile.link_disabled": "Раздел «Добавьте свою ссылку» отключен.",
    "profile.bio_prompt": "Расскажите о себе вашим подписчикам",
    "profile.bio_expected_text": "Пожалуйста, отправьте текст.",
    "profile.bio_saved": "Информация о себе успешно сохранена.",
    "broadcast.entry_question": "Вы хотите отправить сообщение своим подписчикам?",
    "broadcast.cancelled": "Рассылка отменена.",
    "broadcast.choose_content": "Выберите какой контент вы хотите отправить вашим подписчикам",
    "broadcast.ask_text": "Отправьте текст сообщения для рассылки.",
    "broadcast.text_empty": "Текст не должен быть пустым. Отправьте текст сообщения.",
    "broadcast.preview": "Предпросмотр:\n\n{text}",
    "broadcast.ask_photo": "Отправьте картинку для рассылки.",
    "broadcast.ask_video": "Отправьте видео для рассылки.",
    "broadcast.unknown_type": "Не удалось определить тип рассылки. Начните заново.",
    "broadcast.expect_text": "Пожалуйста, отправьте текст сообщения.",
    "broadcast.expect_photo": "Пожалуйста, отправьте картинку.",
    "broadcast.confirm_send": "Подтвердите отправку:",
    "broadcast.expect_image": "Пожалуйста, отправьте изображение.",
    "broadcast.expect_video": "Пожалуйста, отправьте видео.",
    "broadcast.expect_video_file": "Пожалуйста, отправьте видеофайл.",
    "broadcast.ask_new_text": "Отправьте новый текст сообщения.",
    "broadcast.type_not_found": "Не найден тип рассылки. Запустите сценарий заново.",
    "broadcast.done": "Рассылка завершена.\n\nВсего получателей: {total}\nУспешно: {success}\nОшибок: {fail}",
    "tg_admin.title_stats": (
        "Админ-панель\n\n"
        "Всего пользователей: {total_users}\n"
        "Активных подписок: {active_subscriptions}\n"
        "Всего платежей: {total_payments}\n"
        "Успешных платежей: {paid_payments}"
    ),
    "tg_admin.recent_users_empty": "Последние пользователи:\n\nПользователей пока нет.",
    "tg_admin.recent_users_title": "Последние пользователи:",
    "tg_admin.recent_payments_empty": "Последние платежи:\n\nПлатежей пока нет.",
    "tg_admin.recent_payments_title": "Последние платежи:",
    "tg_admin.no_access_message": "Нет доступа к админ-панели.",
    "tg_admin.no_access_alert": "Нет доступа.",
    "web.payment_success": "Оплата подтверждена. Подписка продлена.",
    "web.payment_not_found": "Оплата не найдена.",
    "web.payment_fail": "Оплата не завершена.",
    "web.payment_try_again": "Можно попробовать снова в боте.",
    "web.payment_back_to_tg": "Можно вернуться в Telegram.",
    "web.admin_no_token_hint": "ADMIN_WEB_TOKEN не задан: доступ открыт без токена.",
    "web.admin_title": "Админ-панель",
    "web.admin_total_users_label": "Всего пользователей",
    "web.admin_active_subscriptions_label": "Активных подписок",
    "web.admin_total_payments_label": "Всего платежей",
    "web.admin_paid_payments_label": "Оплаченных платежей",
    "web.admin_recent_users_title": "Последние пользователи",
    "web.admin_recent_payments_title": "Последние платежи",
    "web.admin_no_data": "Нет данных",
    "web.admin_texts_title": "Редактирование текстов",
    "web.pay_page_title": "Переход к оплате",
    "web.pay_page_wait": "Через несколько секунд тут будет страница оплаты...",
    "web.pay_page_button": "Перейти",
    "payment.yoomoney_targets": "Подписка PRO возможности",
    "kb.start_to_chat": "Перейти в чат",
    "kb.cabinet_subscription": "📅 Моя подписка",
    "kb.cabinet_referral": "🔗 Моя реф.ссылка",
    "kb.cabinet_photos": "📷 Изменить фото",
    "kb.cabinet_bio": "ℹ️ Добавить информацию о себе",
    "kb.cabinet_subscribers": "🙋‍♂️ Мои подписчики",
    "kb.cabinet_broadcast": "💌 Рассылка подписчикам",
    "kb.subscription_renew": "♻️ Продлить подписку (+30 дней)",
    "kb.back_to_cabinet": "Назад в Личный кабинет",
    "kb.back_to_cabinet_arrow": "← Назад в Личный кабинет",
    "kb.back_to_cabinet_upper": "НАЗАД В ЛИЧНЫЙ КАБИНЕТ",
    "kb.back_to_cabinet_with_arrow_emoji": "⬅️ Назад в Личный кабинет",
    "kb.back_to_cabinet_with_arrow_emoji_upper": "⬅️ Назад в Личный Кабинет",
    "kb.photo_change_template": "Изменить мое фото",
    "kb.broadcast_yes": "✅ Да",
    "kb.broadcast_no": "❌ Нет",
    "kb.broadcast_text": "Текст 📝",
    "kb.broadcast_text_photo": "Текст + картинка 📝🖼️",
    "kb.broadcast_text_video": "Текст + Видео 📝🎥",
    "kb.confirm_send": "✅ Отправить",
    "kb.confirm_edit": "✏️ Изменить",
    "kb.confirm_cancel": "❌ Отмена",
    "kb.admin_stats": "📊 Статистика",
    "kb.admin_users": "👥 Пользователи",
    "kb.admin_payments": "💳 Платежи",
    "kb.admin_refresh": "🔄 Обновить",
    "kb.admin_to_cabinet": "⬅️ В Личный кабинет",
}


class _SafeDict(dict[str, str]):
    def __missing__(self, key: str) -> str:
        return "{" + key + "}"


@dataclass(slots=True)
class AdminTextItem:
    key: str
    default_value: str
    override_value: str | None
    effective_value: str


class TextService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = TextRepo(session)

    async def resolve(self, key: str) -> str:
        row = await self.repo.get_by_key(key)
        if row is not None:
            return row.value
        return DEFAULT_TEXTS.get(key, key)

    async def resolve_many(self, keys: list[str]) -> dict[str, str]:
        rows_map = await self.repo.get_many(keys)
        return {key: (rows_map[key].value if key in rows_map else DEFAULT_TEXTS.get(key, key)) for key in keys}

    async def render(self, key: str, **kwargs: object) -> str:
        template = await self.resolve(key)
        return template.format_map(_SafeDict({k: str(v) for k, v in kwargs.items()}))

    async def list_for_admin(self) -> list[AdminTextItem]:
        rows = await self.repo.list_all()
        rows_map = {row.key: row.value for row in rows}

        keys = sorted(set(DEFAULT_TEXTS) | set(rows_map))
        items: list[AdminTextItem] = []
        for key in keys:
            default_value = DEFAULT_TEXTS.get(key, "")
            override_value = rows_map.get(key)
            effective_value = override_value if override_value is not None else default_value
            items.append(
                AdminTextItem(
                    key=key,
                    default_value=default_value,
                    override_value=override_value,
                    effective_value=effective_value,
                )
            )
        return items

    async def set_text(self, key: str, value: str) -> None:
        await self.repo.upsert(key=key, value=value)
        await self.session.commit()

    async def reset_text(self, key: str) -> None:
        await self.repo.delete_by_key(key)
        await self.session.commit()
