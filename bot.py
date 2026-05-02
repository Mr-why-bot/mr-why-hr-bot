import os
import sqlite3
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

TOKEN = os.getenv("8714800328:AAFuj_8fUL4NmgNERTnRb3TmTe7wsjEfo9Y")

# Database
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

# Menu
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
    await update.message.reply_text("👋 Welcome to Mr. Why HR System", reply_markup=menu)

async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = update.message.text
    today = datetime.now().strftime("%Y-%m-%d")
    now = datetime.now().strftime("%H:%M")

    if "Start Work" in text:
        cur.execute(
            "INSERT INTO attendance(user_id,name,date,time,status) VALUES(?,?,?,?,?)",
            (user.id, user.full_name, today, now, "IN")
        )
        db.commit()
        await update.message.reply_text("✅ Started Work")

    elif "Leave Work" in text:
        cur.execute(
            "INSERT INTO attendance(user_id,name,date,time,status) VALUES(?,?,?,?,?)",
            (user.id, user.full_name, today, now, "OUT")
        )
        db.commit()
        await update.message.reply_text("⛔ Left Work")

    elif "Report" in text:
        cur.execute(
            "SELECT COUNT(DISTINCT user_id) FROM attendance WHERE date=? AND status='IN'",
            (today,)
        )
        total = cur.fetchone()[0]
        await update.message.reply_text(f"📊 Today Present: {total}")

    elif "Salary" in text:
        await update.message.reply_text("💰 Monthly Salary\nBase = $500\nBonus = $50")

app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT, handle))

app.run_polling()async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Welcome to Mr. Why HR System",
        reply_markup=menu
    )

# Button Actions
async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = update.message.text
    today = datetime.now().strftime("%Y-%m-%d")
    now = datetime.now().strftime("%H:%M")

    if "Start Work" in text:
        cur.execute(
            "INSERT INTO attendance(user_id,name,date,time,status) VALUES(?,?,?,?,?)",
            (user.id, user.full_name, today, now, "IN")
        )
        db.commit()
        await update.message.reply_text("✅ Started Work Successfully")

    elif "Leave Work" in text:
        cur.execute(
            "INSERT INTO attendance(user_id,name,date,time,status) VALUES(?,?,?,?,?)",
            (user.id, user.full_name, today, now, "OUT")
        )
        db.commit()
        await update.message.reply_text("⛔ Left Work Successfully")

    elif "Report" in text:
        cur.execute(
            "SELECT COUNT(DISTINCT user_id) FROM attendance WHERE date=? AND status='IN'",
            (today,)
        )
        total = cur.fetchone()[0]
        await update.message.reply_text(f"📊 Today Present: {total}")

    elif "Salary" in text:
        await update.message.reply_text(
            "💰 Monthly Salary\nBase = $500\nBonus = $50 (Full Attendance)"
        )

# Run Bot
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT, handle))

app.run_polling()os
import sqlite3
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

TOKEN = os.getenv("BOT_TOKEN")

# Database
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
["🟢 Start Work / ចូលធ្វើការ"],
["🔴 Leave Work / ចេញការងារ"],
["📊 Report / របាយការណ៍"],
["💰 Salary / ប្រាក់ខែ"]
],
resize_keyboard=True
)

# Start Command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Welcome to Mr. Why HR System",
        reply_markup=menu
    )

# Button Actions
async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = update.message.text
    today = datetime.now().strftime("%Y-%m-%d")
    now = datetime.now().strftime("%H:%M")

    if "Start Work" in text:
        cur.execute(
            "INSERT INTO attendance(user_id,name,date,time,status) VALUES(?,?,?,?,?)",
            (user.id, user.full_name, today, now, "IN")
        )
        db.commit()
        await update.message.reply_text("✅ Started Work Successfully")

    elif "Leave Work" in text:
        cur.execute(
            "INSERT INTO attendance(user_id,name,date,time,status) VALUES(?,?,?,?,?)",
            (user.id, user.full_name, today, now, "OUT")
        )
        db.commit()
        await update.message.reply_text("⛔ Left Work Successfully")

    elif "Report" in text:
        cur.execute(
            "SELECT COUNT(DISTINCT user_id) FROM attendance WHERE date=? AND status='IN'",
            (today,)
        )
        total = cur.fetchone()[0]
        await update.message.reply_text(f"📊 Today Present: {total}")

    elif "Salary" in text:
        await update.message.reply_text(
            "💰 Monthly Salary\nBase = $500\nBonus = $50 (Full Attendance)"
        )

# Run Bot
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT, handle))

app.run_polling()
