from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton


def main_menu_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="Buy", callback_data="cmd_buy")
    kb.button(text="Support", callback_data="cmd_support")
    kb.adjust(1)
    return kb.as_markup()


def main_menu_reply_kb():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="⚙️ Buy Shopify")],
            [KeyboardButton(text="🛒 Buy Amazon")],
            [KeyboardButton(text="🆘 Support")],
            [KeyboardButton(text="👤 Profile")],
        ],
        resize_keyboard=True
    )


def region_kb(product: str, regions: list[str]):
    kb = InlineKeyboardBuilder()
    for r in regions:
        if r == "USA":
            kb.button(text="🇺🇸 USA", callback_data=f"region_{product}_{r}")
        elif r == "TURKEY":
            kb.button(text="🇹🇷 Turkey", callback_data=f"region_{product}_{r}")
        elif r == "NETHERLANDS":
            kb.button(text="🇳🇱 Netherlands", callback_data=f"region_{product}_{r}")
        else:
            kb.button(text=r, callback_data=f"region_{product}_{r}")
    kb.adjust(1)
    return kb.as_markup()


def payment_choice_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="💳 Pay via CryptoBot", callback_data="pay_crypto")
    kb.button(text="💸 Pay via TRC-20 Wallet (Soon)", callback_data="pay_trc")
    kb.adjust(1)
    return kb.as_markup()


def trc_paid_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ I have paid", callback_data="trc_paid")
    kb.adjust(1)
    return kb.as_markup()


def crypto_invoice_kb(pay_url: str, invoice_id: int):
    kb = InlineKeyboardBuilder()
    kb.button(text="🔗 Open payment link", url=pay_url)
    kb.button(text="✅ Check payment", callback_data=f"check_{invoice_id}")
    kb.adjust(1)
    return kb.as_markup()


def admin_issue_kb(user_id: int):
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Issue Accounts", callback_data=f"issue_{user_id}")
    kb.button(text="✉️ Reply to user", callback_data=f"reply_{user_id}")
    kb.adjust(2)
    return kb.as_markup()


def admin_reply_confirm_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="Cancel", callback_data="reply_cancel")
    kb.adjust(1)
    return kb.as_markup()


def profile_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="📜 Orders history", callback_data="profile_orders")
    kb.adjust(1)
    return kb.as_markup()


def topup_paid_kb(topup_id: int):
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ I have paid", callback_data=f"topup_paid_{topup_id}")
    kb.adjust(1)
    return kb.as_markup()
