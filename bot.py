import os
import sqlite3
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# Load Token
TOKEN = os.environ.get("8227579183:AAHs7nvKMPMFh_UllusgKhJMaoMPgMDsmoQ")

# Database setup
db = sqlite3.connect("hr.db", check_same_thread=False)
cur = db.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS attendance(
id INTEGER PRIMARY KEY AUTOINCREMENT,
user_id TEXT,
name TEXT,
date TEXT,
time TEXT,
status TEXT
)
""")
db.commit()

# Menu Buttons
menu = ReplyKeyboardMarkup(
    [
        ["🟢 Start Work"],
        ["🔴 Leave Work"],
        ["📊 Report"],
        ["💰 Salary"]
    ],
    resize_keyboard=True
)

# Start Command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Welcome Mr Why HR Bot", reply_markup=menu)

# Handle Buttons
async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = update.message.text

    today = datetime.now().strftime("%Y-%m-%d")
    now = datetime.now().strftime("%H:%M")

    if text == "🟢 Start Work":
        cur.execute(
            "INSERT INTO attendance(user_id,name,date,time,status) VALUES(?,?,?,?,?)",
            (user.id, user.full_name, today, now, "IN")
        )
        db.commit()
        await update.message.reply_text("✅ Checked In")

    elif text == "🔴 Leave Work":
        cur.execute(
            "INSERT INTO attendance(user_id,name,date,time,status) VALUES(?,?,?,?,?)",
            (user.id, user.full_name, today, now, "OUT")
        )
        db.commit()
        await update.message.reply_text("⛔ Checked Out")

    elif text == "📊 Report":
        cur.execute(
            "SELECT COUNT(DISTINCT user_id) FROM attendance WHERE date=? AND status='IN'",
            (today,)
        )
        total = cur.fetchone()[0]
        await update.message.reply_text(f"📊 Today Working: {total}")

    elif text == "💰 Salary":
        await update.message.reply_text("💰 Salary = $500 + $50 Bonus")

# Run Bot
def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT, handle))

    print("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
