import hmac, hashlib
import uuid
import requests
import qrcode
from io import BytesIO
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    ContextTypes, ConversationHandler, MessageHandler, filters
)

# Konstanta & API Key
TOKEN = "7450399171:AAGWwkKWPmgfkgfEtkfb73K5-UDeehvRbnM"
TRIPAY_API_KEY = "DEV-bXz6Jn2OaIyrLCHRTKdKNkheVoPlME9LINAjdiRN"
ADMIN_CHAT_ID = 5588770450
CALLBACK_URL = "https://c2cf-114-10-20-11.ngrok-free.app/tripay-webhook"

ASK_NAME, ASK_TICKET = range(2)

# Simpan sementara (harusnya pakai DB)
user_orders = {}

# Menu utama
def get_main_menu():
    keyboard = [
        [InlineKeyboardButton("Pesan Tiket", callback_data='order')],
    ]
    return InlineKeyboardMarkup(keyboard)

def get_back_menu():
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Kembali", callback_data='back')]])

# /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Selamat datang di Wisata Ngrembel Gunung Pati!\nPilih menu:",
        reply_markup=get_main_menu()
    )

# Handler tombol inline
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == 'order':
        await query.edit_message_text("📝 Masukkan nama Anda:")
        return ASK_NAME
    elif query.data == 'back':
        await query.edit_message_text("Pilih menu:", reply_markup=get_main_menu())

# Step 1: Minta jumlah tiket
async def ask_ticket(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["name"] = update.message.text
    await update.message.reply_text("🎫 Berapa tiket yang ingin dipesan?")
    return ASK_TICKET

# Step 2: Proses pesanan & bayar
async def confirm_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = context.user_data.get("name")
    jumlah = update.message.text

    try:
        jumlah = int(jumlah)
    except ValueError:
        await update.message.reply_text("❌ Masukkan angka tiket yang valid.")
        return ASK_TICKET

    total = jumlah * 25000
    merchant_ref = f"TIKET-{uuid.uuid4().hex[:8]}"

    context.user_data.update({
        "jumlah": jumlah,
        "total": total,
        "merchant_ref": merchant_ref
    })

    # Request ke Tripay
    headers = {
        "Authorization": f"Bearer {TRIPAY_API_KEY}",
        "Content-Type": "application/json"
    }

    merchant_code = "T41441"
    private_key = "f6d74-UXI0X-dBqex-7zeXJ-fqcRo"
    merchant_ref = context.user_data["merchant_ref"]
    amount = context.user_data["total"]

    # Buat signature
    signature_str = merchant_code + merchant_ref + str(amount)
    signature = hmac.new(
        private_key.encode(),
        signature_str.encode(),
        hashlib.sha256
    ).hexdigest()
    
    payload = {
        "method": "QRIS",
        "merchant_ref": merchant_ref,
        "amount": amount,
        "customer_name": name,
        "customer_email": "user@example.com",
        "order_items": [
            {
                "sku": "TIKET",
                "name": "Tiket Masuk",
                "price": 25000,
                "quantity": jumlah
            }
        ],
        "callback_url": "https://5cd2-114-10-20-11.ngrok-free.app/tripay-webhook",
        "signature": signature  # Tambahkan ini
    }

    response = requests.post("https://tripay.co.id/api-sandbox/transaction/create", json=payload, headers=headers)
    data = response.json()

    # Tambahkan debug print!
    print("Tripay response:", data)

    if not data.get("success"):
        await update.message.reply_text("❌ Gagal membuat pembayaran. Coba lagi nanti.")
        return ConversationHandler.END

    qr_url = data["data"]["qr_url"]
    reference = data["data"]["reference"]

    user_orders[reference] = {
        "chat_id": update.message.chat_id,
        "name": name,
        "jumlah": jumlah,
        "total": total
    }

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Saya sudah bayar", url=data["data"]["checkout_url"])],
        [InlineKeyboardButton("🔙 Kembali ke Menu", callback_data='back')],
    ])

    await update.message.reply_photo(
        photo=qr_url,
        caption=(f"Silakan scan QR untuk bayar Rp{total:,}.\nRef: `{reference}`"),
        parse_mode='Markdown',
        reply_markup=keyboard
    )

    return ConversationHandler.END

# Handler cancel
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Pemesanan dibatalkan.")
    return ConversationHandler.END

# MAIN
if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).build()

    # Command
    app.add_handler(CommandHandler("start", start))

    # Flow pemesanan
    conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(button_handler, pattern="^order$")],
        states={
            ASK_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_ticket)],
            ASK_TICKET: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirm_order)],
        },
        fallbacks=[MessageHandler(filters.COMMAND, cancel)],
    )
    app.add_handler(conv_handler)

    # Handler tombol umum
    app.add_handler(CallbackQueryHandler(button_handler))

    print("Bot berjalan...")
    app.run_polling()