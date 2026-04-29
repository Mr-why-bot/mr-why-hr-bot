import os
import sqlite3
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

TOKEN = os.getenv("BOT_TOKEN")

db = sqlite3.connect("data.db", check_same_thread=False)
cur = db.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS attendance(
id INTEGER PRIMARY KEY AUTOINCREMENT,
user_id TEXT,
name TEXT,
date TEXT,
status TEXT
)
""")
db.commit()

menu = ReplyKeyboardMarkup(
[
["🟢 Start Work / ចូលធ្វើការ"],
["🔴 Leave Work / ចេញការងារ"],
["📊 Report / របាយការណ៍"],
["💰 Salary / ប្រាក់ខែ"]
],
resize_keyboard=True
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Welcome to Mr. Why HR System",
        reply_markup=menu
    )

async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = update.message.text
    today = datetime.now().strftime("%Y-%m-%d")
    now = datetime.now().strftime("%H:%M")

    if "Start Work" in text:
        cur.execute("INSERT INTO attendance(user_id,name,date,status) VALUES(?,?,?,?)",
                    (user.id, user.full_name, today, "IN"))
        db.commit()
        await update.message.reply_text("✅ Started Work")

    elif "Leave Work" in text:
        cur.execute("UPDATE attendance SET status=? WHERE user_id=? AND date=?",
                    ("OUT", user.id, today))
        db.commit()
        await update.message.reply_text("⛔ Left Work")

    elif "Report" in text:
        cur.execute("SELECT COUNT(*) FROM attendance WHERE date=?", (today,))
        total = cur.fetchone()[0]
        await update.message.reply_text(f"📊 Today Present: {total}")

    elif "Salary" in text:
        await update.message.reply_text("💰 Salary = $500 + $50 Bonus (Full Attendance)")

app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT, handle))

app.run_polling()
