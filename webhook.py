from flask import Flask, request
import hmac, hashlib
import telegram
import asyncio

# Token dan bot Telegram
BOT_TOKEN = "7450399171:AAGWwkKWPmgfkgfEtkfb73K5-UDeehvRbnM"
bot = telegram.Bot(token=BOT_TOKEN)

# Tripay
PRIVATE_KEY = "f6d74-UXI0X-dBqex-7zeXJ-fqcRo"

# Simulasi database user sementara (harusnya ini pakai DB)
user_orders = {}

app = Flask(__name__)

@app.route('/tripay-webhook', methods=['POST'])
def tripay_webhook():
    signature = request.headers.get('X-Callback-Signature')
    data = request.get_json()

    # Validasi signature
    computed_signature = hmac.new(
        PRIVATE_KEY.encode(),
        msg=request.data,
        digestmod=hashlib.sha256
    ).hexdigest()

    if computed_signature != signature:
        return 'Invalid signature', 400

    # Ambil data transaksi
    merchant_ref = data.get('merchant_ref')
    reference = data.get('reference')
    status = data.get('status')
    
    # Cek status pembayaran
    status = data.get('status')
    if status == 'PAID':
        reference = data.get('reference')
        method = data.get('payment_method')
        total = data.get('total_amount')

        message = (
            f"💸 *Pembayaran Diterima!*\n\n"
            f"🔖 Ref: `{reference}`\n"
            f"💳 Metode: {method}\n"
            f"💰 Total: Rp{total:,}"
        )

        # Ganti dengan chat ID kamu sendiri (admin atau grup)
        ADMIN_CHAT_ID = 5588770450
        asyncio.run(bot.send_message(chat_id=ADMIN_CHAT_ID, text=message, parse_mode='Markdown'))

    return 'OK', 200

if __name__ == '__main__':
    app.run(port=5000)