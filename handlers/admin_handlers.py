from aiogram import Router, types
from aiogram.filters import Command
from config import ADMIN_ID, PRICES
from keyboards import admin_issue_kb, admin_reply_confirm_kb
from generator import generate_accounts
from utils.db import get_latest_pending_order, update_order_status, add_balance, update_topup_status, get_topup

router = Router()

# pending manual issues: user_id -> (region, qty)
PENDING_MANUAL = {}
# admin reply mode: admin_user_id -> target_user_id
ADMIN_REPLY_MODE = {}


async def notify_admin_issue(user_id: int, region: str, qty: int):
    """
    Send message to admin about manual TRC 'Soon' order.
    This function is imported by user_handlers and called there.
    """
    PENDING_MANUAL[user_id] = (region, qty)
    price = PRICES.get(region, 0) * qty
    text = (
        f"💸 Manual payment request (TRC placeholder)\n\n"
        f"User ID: {user_id}\n"
        f"Region: {region}\n"
        f"Quantity: {qty}\n"
        f"Total (informational): {price:.2f} USDT\n\n"
        "Use the buttons below to Issue accounts or Reply to user."
    )
    # We import bot lazily to avoid circular imports
    from aiogram import Bot
    from config import BOT_TOKEN
    bot = Bot(token=BOT_TOKEN)
    try:
        await bot.send_message(
            ADMIN_ID,
            text,
            reply_markup=admin_issue_kb(user_id)
        )
    finally:
        await bot.session.close()


async def notify_admin_payment_error(user_id: int, region: str, qty: int, total: float, error_text: str):
    """
    Notify admin about payment service errors for troubleshooting.
    """
    text = (
        "🚨 CryptoPay error\n\n"
        f"User ID: {user_id}\n"
        f"Region: {region}\n"
        f"Quantity: {qty}\n"
        f"Total: {total:.2f} USDT\n\n"
        f"Error: {error_text}"
    )
    from aiogram import Bot
    from config import BOT_TOKEN
    bot = Bot(token=BOT_TOKEN)
    try:
        await bot.send_message(ADMIN_ID, text)
    finally:
        await bot.session.close()


async def notify_admin_topup(user_id: int, topup_id: int, amount: float):
    """
    Notify admin about a pending top-up request.
    """
    text = (
        "💰 Top-up request\n\n"
        f"User ID: {user_id}\n"
        f"Top-up ID: {topup_id}\n"
        f"Amount: {amount:.2f} USDT\n\n"
        "Confirm after you see the payment."
    )
    from aiogram import Bot
    from config import BOT_TOKEN
    from aiogram.utils.keyboard import InlineKeyboardBuilder

    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Confirm top-up", callback_data=f"topup_confirm_{topup_id}_{user_id}")
    kb.button(text="❌ Reject", callback_data=f"topup_reject_{topup_id}_{user_id}")
    kb.adjust(2)

    bot = Bot(token=BOT_TOKEN)
    try:
        await bot.send_message(
            ADMIN_ID,
            text,
            reply_markup=kb.as_markup()
        )
    finally:
        await bot.session.close()


async def forward_support_to_admin(user_id: int, text: str, user_obj: types.User):
    """
    Forward user's support message to admin with reply button.
    """
    message = (
        f"📩 Support request\n\nFrom: {user_obj.full_name} (id: {user_id})\n\n"
        f"Message:\n{text}"
    )
    from aiogram import Bot
    from config import BOT_TOKEN
    bot = Bot(token=BOT_TOKEN)
    try:
        await bot.send_message(
            ADMIN_ID,
            message,
            reply_markup=admin_issue_kb(user_id)
        )
    finally:
        await bot.session.close()


# Handler for admin inline buttons (issue_ / reply_)
@router.callback_query()
async def admin_buttons(callback: types.CallbackQuery):
    data = callback.data or ""
    admin_id = callback.from_user.id
    if admin_id != ADMIN_ID:
        await callback.answer("No permission", show_alert=True)
        return

    if data.startswith("issue_"):
        # manual issue accounts
        target_id = int(data.split("_", 1)[1])
        pending = get_latest_pending_order(target_id)
        if not pending:
            await callback.answer("Nothing to issue or already issued.", show_alert=True)
            return
        order_id, region, qty, total, method, status, created_at = pending
        accounts = generate_accounts(region, qty)
        update_order_status(order_id, "confirmed")
        # send accounts to user
        try:
            await callback.bot.send_message(
                target_id,
                "Here are your accounts:\n\n"
                f"<code>{accounts}</code>",
                parse_mode="HTML"
            )
            await callback.answer("Accounts issued to user.")
        except Exception:
            await callback.answer("Failed to send to user (maybe blocked).", show_alert=True)
        return

    if data.startswith("topup_confirm_"):
        parts = data.split("_", 3)
        if len(parts) != 4:
            await callback.answer("Invalid top-up data.", show_alert=True)
            return
        topup_id = int(parts[2])
        target_id = int(parts[3])
        topup = get_topup(topup_id)
        if not topup:
            await callback.answer("Top-up not found.", show_alert=True)
            return
        _, _, amount, _, status, _ = topup
        update_topup_status(topup_id, "confirmed")
        add_balance(target_id, float(amount))
        try:
            await callback.bot.send_message(
                target_id,
                "Top-up confirmed. Your balance has been updated."
            )
            await callback.answer("Top-up confirmed.")
        except Exception:
            await callback.answer("Failed to notify user.", show_alert=True)
        return

    if data.startswith("topup_reject_"):
        parts = data.split("_", 3)
        if len(parts) != 4:
            await callback.answer("Invalid top-up data.", show_alert=True)
            return
        topup_id = int(parts[2])
        target_id = int(parts[3])
        update_topup_status(topup_id, "rejected")
        try:
            await callback.bot.send_message(
                target_id,
                "Top-up rejected. If this is a mistake, contact support."
            )
            await callback.answer("Top-up rejected.")
        except Exception:
            await callback.answer("Failed to notify user.", show_alert=True)
        return

    if data.startswith("reply_"):
        # admin wants to reply: set mode and prompt admin to send message
        target_id = int(data.split("_", 1)[1])
        ADMIN_REPLY_MODE[admin_id] = target_id
        await callback.message.answer("Please type your reply message. Send /cancel to cancel.", reply_markup=admin_reply_confirm_kb())
        await callback.answer()
        return

    if data == "reply_cancel":
        ADMIN_REPLY_MODE.pop(admin_id, None)
        await callback.answer("Reply canceled.")
        await callback.message.edit_reply_markup()  # remove inline kb for clarity
        return


# Admin text handler: when admin sends a message and is in reply mode, forward it to user
@router.message()
async def admin_text(message: types.Message):
    admin_id = message.from_user.id
    if admin_id != ADMIN_ID:
        return  # ignore messages from others in this router

    target = ADMIN_REPLY_MODE.get(admin_id)
    if not target:
        return  # not in reply mode

    text = message.text or ""
    # send the message to user
    try:
        await message.bot.send_message(
            target,
            f"📩 Support reply from admin:\n\n{text}"
        )
        await message.reply("Message sent to the user.")
    except Exception:
        await message.reply("Failed to send message to user. Maybe user blocked the bot.")

    # clear reply mode
    ADMIN_REPLY_MODE.pop(admin_id, None)
