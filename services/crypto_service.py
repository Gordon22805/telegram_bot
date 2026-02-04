from aiocryptopay import AioCryptoPay, Networks

from config import CRYPTOBOT_TOKEN

# Use MAIN_NET for real payments
_crypto = AioCryptoPay(
    token=CRYPTOBOT_TOKEN,
    network=Networks.MAIN_NET
)

async def create_invoice(amount: float, description: str = ""):
    """
    Create invoice in CryptoPay mainnet.
    Returns invoice object from aiocryptopay.
    """
    if not CRYPTOBOT_TOKEN:
        raise RuntimeError("CRYPTOBOT_TOKEN is not set")

    amount = round(float(amount), 2)
    try:
        invoice = await _crypto.create_invoice(asset="USDT", amount=amount, description=description)
        return invoice
    except Exception as exc:
        raise RuntimeError(f"CryptoPay error: {exc}") from exc

async def get_invoice_status(invoice_id: int):
    """
    Return invoice object or None.
    """
    invoices = await _crypto.get_invoices(invoice_ids=[invoice_id])
    if not invoices:
        return None
    return invoices[0]

async def close_crypto():
    try:
        await _crypto.close()
    except Exception:
        pass
