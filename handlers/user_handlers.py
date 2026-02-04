from aiogram import Router, types, F
from aiogram.types import FSInputFile
from pathlib import Path
from aiogram.filters import Command
from config import PRICES, MAX_QUANTITY, ADMIN_ID
from keyboards import main_menu_kb, main_menu_reply_kb, region_kb, payment_choice_kb, crypto_invoice_kb, trc_paid_kb, profile_kb, topup_paid_kb
from utils.spamguard import can_proceed
from services.crypto_service import create_invoice, get_invoice_status
from generator import generate_accounts
from handlers.admin_handlers import notify_admin_issue, notify_admin_payment_error  # to notify admin for TRC 'Soon'
from utils.db import create_order, get_user_orders

router = Router()

ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"

AMAZON_PRICES = {
    "USA": round(PRICES.get("USA", 0) + 5.0, 2),
    "TURKEY": round(PRICES.get("TURKEY", 0) + 7.0, 2),
}

PRODUCTS = {
    "Shopify": {
        "regions": ["USA", "TURKEY", "NETHERLANDS"],
        "prices": PRICES,
        "image": ASSETS_DIR / "shopi.png",
    },
    "Amazon": {
        "regions": ["USA", "TURKEY"],
        "prices": AMAZON_PRICES,
        "image": ASSETS_DIR / "amazon.png",
    },
}

# Region -> image path (Shopify only)
REGION_IMAGES = {
    "USA": ASSETS_DIR / "usa.png",
    "TURKEY": ASSETS_DIR / "turkey.png",
    "NETHERLANDS": ASSETS_DIR / "neth.png",
}

# In-memory state dictionaries:
# USER_STATE[user_id] = {"stage": "choose_region"|"enter_qty"|"waiting_payment", "region":..., "qty":..., "invoices": [ids]}
USER_STATE = {}
# Track delivered invoices to avoid double issuing
DELIVERED_INVOICES = set()


@router.message(Command("start"))
async def cmd_start(message: types.Message):
    caption = (
        "🤩⚡ Energy Shop — a trusted bot for securely buying existing Shopify accounts.\n\n"
        "Buy ready Shopify accounts directly, without middlemen.\n"
        "Verified accounts, full guarantees, and support for any escrow/guarantor to keep you safe.\n\n"
        "Use the menu below."
    )
    photo = FSInputFile(str(ASSETS_DIR / "lightning.png"))
    await message.answer_photo(
        photo=photo,
        caption=caption,
        reply_markup=main_menu_reply_kb()
    )

@router.message(Command("profile"))
async def cmd_profile(message: types.Message):
    user_id = message.from_user.id
    text = (
        "👤 PROFILE\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"🆔 ID: <code>{user_id}</code>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "Use the button below."
    )
    photo = FSInputFile(str(ASSETS_DIR / "users.png"))
    await message.answer_photo(
        photo=photo,
        caption=text,
        parse_mode="HTML",
        reply_markup=profile_kb()
    )

# Buy flow entry
@router.callback_query(F.data == "cmd_buy")
async def cb_buy(callback: types.CallbackQuery):
    product = "Shopify"
    USER_STATE[callback.from_user.id] = {"stage": "choose_region", "product": product}
    photo = FSInputFile(str(PRODUCTS[product]["image"]))
    await callback.message.answer_photo(
        photo=photo,
        caption="Choose region:",
        reply_markup=region_kb(product, PRODUCTS[product]["regions"])
    )
    await callback.answer()

@router.message(F.text == "⚙️ Buy Shopify")
async def msg_buy(message: types.Message):
    product = "Shopify"
    USER_STATE[message.from_user.id] = {"stage": "choose_region", "product": product}
    photo = FSInputFile(str(PRODUCTS[product]["image"]))
    await message.answer_photo(
        photo=photo,
        caption="Choose region:",
        reply_markup=region_kb(product, PRODUCTS[product]["regions"])
    )

@router.message(F.text == "🛒 Buy Amazon")
async def msg_buy_amazon(message: types.Message):
    product = "Amazon"
    USER_STATE[message.from_user.id] = {"stage": "choose_region", "product": product}
    photo = FSInputFile(str(PRODUCTS[product]["image"]))
    await message.answer_photo(
        photo=photo,
        caption="Choose region:",
        reply_markup=region_kb(product, PRODUCTS[product]["regions"])
    )

@router.message(F.text == "🆘 Support")
async def msg_support(message: types.Message):
    user_id = message.from_user.id
    USER_STATE[user_id] = {"stage": "support_wait"}
    photo = FSInputFile(str(ASSETS_DIR / "botik.png"))
    await message.answer_photo(
        photo=photo,
        caption="Please type your message for support. It will be forwarded to admin."
    )

@router.message(F.text == "👤 Profile")
async def msg_profile(message: types.Message):
    await cmd_profile(message)

@router.callback_query(F.data.startswith("region_"))
async def cb_region(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    parts = callback.data.split("_", 2)
    if len(parts) != 3:
        await callback.answer("Invalid region.", show_alert=True)
        return
    product = parts[1]
    region = parts[2]

    # Store state
    USER_STATE[user_id] = {
        "stage": "enter_qty",
        "product": product,
        "region": region,
        "qty": None,
        "invoices": [],
    }
    price = PRODUCTS.get(product, {}).get("prices", {}).get(region, 0)
    caption = (
        f"Product: <b>{product}</b>\n"
        f"Selected region: <b>{region}</b>\n"
        f"Price per account: <b>{price} USDT</b>\n\n"
        f"Enter quantity (max {MAX_QUANTITY}):"
    )
    image_path = REGION_IMAGES.get(region) or PRODUCTS.get(product, {}).get("image")
    if image_path:
        await callback.message.answer_photo(
            photo=FSInputFile(str(image_path)),
            caption=caption,
            parse_mode="HTML"
        )
    else:
        await callback.message.answer(caption, parse_mode="HTML")
    await callback.answer()

@router.message(F.text.regexp(r"^\d+(\.\d+)?$"))
async def quantity_message(message: types.Message):
    user_id = message.from_user.id
    state = USER_STATE.get(user_id)
    if not state:
        return

    if state.get("stage") == "topup_amount":
        amount = round(float(message.text), 2)
        if amount <= 0:
            await message.answer("Amount must be greater than 0.")
            return

        topup_id = create_topup(user_id, amount, method="TRC-20", status="pending")
        USER_STATE[user_id] = {"stage": "topup_wait"}

        await message.answer(
            "TRC-20 top-up address:\n"
            "<code>TBFwX63PXBiBiMP5JarQWuNMPRawS8gyHj</code>\n\n"
            "After payment, press the button below.",
            parse_mode="HTML",
            reply_markup=topup_paid_kb(topup_id)
        )
        return

    if state.get("stage") != "enter_qty":
        # ignore numeric messages when not expecting quantity
        return

    if not can_proceed(user_id):
        await message.answer("Please wait a few seconds before retrying.")
        return

    if "." in message.text:
        await message.answer("Quantity must be a whole number.")
        return
    qty = int(message.text)
    if qty <= 0 or qty > MAX_QUANTITY:
        await message.answer(f"Quantity must be between 1 and {MAX_QUANTITY}.")
        return

    USER_STATE[user_id]["qty"] = qty
    region = USER_STATE[user_id]["region"]
    product = USER_STATE[user_id].get("product", "Shopify")
    price = PRODUCTS.get(product, {}).get("prices", {}).get(region, 0)
    total = price * qty

    # Move to waiting_payment stage
    USER_STATE[user_id]["stage"] = "waiting_payment"

    summary = (
        f"Summary:\nProduct: <b>{product}</b>\nRegion: <b>{region}</b>\nQuantity: <b>{qty}</b>\n"
        f"Total: <b>{total:.2f} USDT</b>\n\n"
        "Choose payment method:"
    )
    image_path = REGION_IMAGES.get(region) or PRODUCTS.get(product, {}).get("image")
    if image_path:
        await message.answer_photo(
            photo=FSInputFile(str(image_path)),
            caption=summary,
            parse_mode="HTML",
            reply_markup=payment_choice_kb()
        )
    else:
        await message.answer(summary, parse_mode="HTML", reply_markup=payment_choice_kb())

@router.callback_query(F.data == "pay_crypto")
async def cb_pay_crypto(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    state = USER_STATE.get(user_id)
    if not state or state.get("stage") != "waiting_payment":
        await callback.answer("No active order. Start with /start or Buy.", show_alert=True)
        return

    region = state["region"]
    qty = state["qty"]
    product = state.get("product", "Shopify")
    price = PRODUCTS.get(product, {}).get("prices", {}).get(region, 0)
    total = price * qty

    # Create invoice via CryptoPay (Mainnet)
    try:
        invoice = await create_invoice(amount=total, description=f"{product} {region} x{qty}")
    except Exception as e:
        await notify_admin_payment_error(user_id, f"{product}-{region}", qty, total, str(e))
        await callback.answer("Payment service error. Admin was notified.", show_alert=True)
        return

    invoice_id = invoice.invoice_id
    invoice_url = invoice.bot_invoice_url

    # Store invoice id for this user
    state.setdefault("invoices", []).append(invoice_id)

    # Send payment link + check button
    await callback.message.answer(
        f"Please pay using the link below:\n{invoice_url}\n\n"
        "After payment press the 'Check payment' button.",
        reply_markup=crypto_invoice_kb(invoice_url, invoice_id)
    )
    await callback.answer()

@router.callback_query(F.data.startswith("check_"))
async def cb_check_payment(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    invoice_id_str = callback.data.split("_", 1)[1]
    try:
        invoice_id = int(invoice_id_str)
    except ValueError:
        await callback.answer("Invalid invoice id", show_alert=True)
        return

    # If already delivered for this invoice, prevent re-issuing
    if invoice_id in DELIVERED_INVOICES:
        await callback.answer("Accounts already issued for this invoice.", show_alert=True)
        return

    # Check invoice status
    try:
        inv = await get_invoice_status(invoice_id)
    except Exception:
        await callback.answer("Payment service error.", show_alert=True)
        return

    if not inv:
        await callback.answer("Invoice not found.", show_alert=True)
        return

    # The library may return status in inv.status (string)
    status = getattr(inv, "status", None)
    if status == "paid":
        # find user state tied to this invoice
        # we try to find user_id by scanning USER_STATE, but easiest is the current user
        state = USER_STATE.get(user_id)
        if not state:
            await callback.answer("Order not found.", show_alert=True)
            return

        region = state.get("region")
        qty = state.get("qty", 1)
        product = state.get("product", "Shopify")
        price = PRODUCTS.get(product, {}).get("prices", {}).get(region, 0)
        total = price * qty

        accounts = generate_accounts(region, qty)
        DELIVERED_INVOICES.add(invoice_id)
        create_order(user_id, f"{product}-{region}", qty, total, method="CryptoBot", status="confirmed")

        await callback.message.answer(
            "Payment received!\n\nHere are your accounts:\n\n"
            f"<code>{accounts}</code>",
            parse_mode="HTML"
        )
        await callback.answer()
    else:
        await callback.answer("Payment not found yet. Please try again later.", show_alert=True)


@router.callback_query(F.data == "pay_trc")
async def cb_pay_trc(callback: types.CallbackQuery):
    """
    TRC-20 flow is a placeholder: send 'Soon' to user and notify admin so admin can manually issue.
    """
    user_id = callback.from_user.id
    state = USER_STATE.get(user_id)
    if not state or state.get("stage") != "waiting_payment":
        await callback.answer("No active order.", show_alert=True)
        return

    region = state["region"]
    qty = state["qty"]
    product = state.get("product", "Shopify")

    # Inform user (placeholder)
    await callback.message.answer(
        "TRC-20 payment address:\n"
        "<code>TBFwX63PXBiBiMP5JarQWuNMPRawS8gyHj</code>\n\n"
        "After payment, press the button below.",
        parse_mode="HTML",
        reply_markup=trc_paid_kb()
    )

    await callback.answer()

@router.callback_query(F.data == "trc_paid")
async def cb_trc_paid(callback: types.CallbackQuery):
    """
    User confirms TRC payment. Notify admin for manual confirmation.
    """
    user_id = callback.from_user.id
    state = USER_STATE.get(user_id)
    if not state or state.get("stage") != "waiting_payment":
        await callback.answer("No active order.", show_alert=True)
        return

    region = state["region"]
    qty = state["qty"]
    product = state.get("product", "Shopify")

    # Notify admin so they can manually issue accounts
    price = PRODUCTS.get(product, {}).get("prices", {}).get(region, 0)
    total = price * qty
    create_order(user_id, f"{product}-{region}", qty, total, method="TRC-20", status="pending")
    await notify_admin_issue(user_id, f"{product}-{region}", qty)

    await callback.message.answer("Waiting for payment confirmation.")
    await callback.answer()

@router.callback_query(F.data == "profile_orders")
async def cb_profile_orders(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    orders = get_user_orders(user_id, limit=10)
    if not orders:
        await callback.message.answer("Orders history is empty.")
        await callback.answer()
        return

    lines = ["Orders history (last 10):\n"]
    for order_id, region, qty, total, method, status, created_at in orders:
        lines.append(
            f"#{order_id} - {region} x{qty} - {total:.2f} USDT - {method} - {status} - {created_at}"
        )
    await callback.message.answer("\n".join(lines))
    await callback.answer()


# Support: user presses Support
@router.callback_query(F.data == "cmd_support")
async def cb_support(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    # mark that we expect the next message as support text
    USER_STATE[user_id] = {"stage": "support_wait"}
    photo = FSInputFile(str(ASSETS_DIR / "botik.png"))
    await callback.message.answer_photo(
        photo=photo,
        caption="Please type your message for support. It will be forwarded to admin."
    )
    await callback.answer()

@router.message()
async def catch_all(message: types.Message):
    """
    Handles:
    - support messages when user in support_wait stage
    - other texts: ignore or instruct
    """
    user_id = message.from_user.id
    state = USER_STATE.get(user_id)

    # Support flow
    if state and state.get("stage") == "support_wait":
        # forward to admin with inline buttons (issue/reply)
        from handlers.admin_handlers import forward_support_to_admin
        # forward message content to admin
        await forward_support_to_admin(user_id, message.text, message.from_user)
        # reset user state to avoid repeated forwards
        USER_STATE[user_id] = {}
        await message.answer("Your message was forwarded to support. We will reply here.")
        return

    # If user sends other messages while in waiting_payment stage, ignore politely
    if state and state.get("stage") == "waiting_payment":
        await message.answer("You have an active order. Use the payment buttons or press /start to begin new.")
        return

    # Generic help
    await message.answer("Use /start to begin.")
