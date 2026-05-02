import sqlite3
from datetime import datetime, time, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import asyncio

# ========== CONFIG ==========
TOKEN = "8714800328:AAFuj_8fUL4NmgNERTnRb3TmTe7wsjEfo9Y"
SALARY_PER_MONTH = 500  # 500 USD
WORK_DAY_SHIFT = ["09:00", "21:00"]   # វេនថ្ងៃ 9ព្រឹក-9យប់
NIGHT_SHIFT = ["21:00", "09:00"]      # វេនយប់ 9យប់-9ព្រឹក
LATE_THRESHOLD = 15  # យឺតបើចូលក្រោយ 15 នាទី
OFF_DAYS_PER_MONTH = 2  # ឈប់សម្រាក 2ថ្ងៃ/ខែ

# ========== DATABASE ==========
conn = sqlite3.connect("company_bot.db", check_same_thread=False)
c = conn.cursor()

c.execute('''CREATE TABLE IF NOT EXISTS employees (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    shift_type TEXT,  -- "day" or "night"
    is_active BOOLEAN DEFAULT 1
)''')

c.execute('''CREATE TABLE IF NOT EXISTS attendance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    emp_id INTEGER,
    date TEXT,
    check_in TEXT,
    status TEXT,  -- "on_time", "late"
    shift_type TEXT
)''')

c.execute('''CREATE TABLE IF NOT EXISTS salary_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    month_year TEXT,
    emp_id INTEGER,
    days_worked INTEGER,
    late_days INTEGER,
    salary REAL
)''")
conn.commit()

# ========== HELPER FUNCTIONS ==========
def get_shift_by_time():
    now = datetime.now().strftime("%H:%M")
    if WORK_DAY_SHIFT[0] <= now < WORK_DAY_SHIFT[1]:
        return "day"
    else:
        return "night"

def is_late(check_in_time_str, shift_type):
    check_in = datetime.strptime(check_in_time_str, "%H:%M")
    if shift_type == "day":
        limit = datetime.strptime(WORK_DAY_SHIFT[0], "%H:%M")
    else:
        limit = datetime.strptime(NIGHT_SHIFT[0], "%H:%M")
    diff = (check_in - limit).total_seconds() / 60
    return diff > LATE_THRESHOLD

def generate_report():
    today = datetime.now().strftime("%Y-%m-%d")
    c.execute('''SELECT e.name, a.check_in, a.status, a.shift_type 
                 FROM attendance a JOIN employees e ON a.emp_id = e.id 
                 WHERE a.date = ?''', (today,))
    rows = c.fetchall()
    if not rows:
        return "ថ្ងៃនេះមិនទាន់មានការចូលធ្វើការទេ។"
    report = "📋 **របាយការណ៍ប្រចាំថ្ងៃ**\n\n"
    for name, check_in, status, shift in rows:
        report += f"👤 {name} | {shift} shift | ចូល: {check_in} | {status.upper()}\n"
    return report

def calculate_salary(emp_id, month_year):
    c.execute('''SELECT COUNT(*) FROM attendance 
                 WHERE emp_id=? AND strftime('%Y-%m', date)=? AND status='on_time' ''', (emp_id, month_year))
    on_time = c.fetchone()[0]
    c.execute('''SELECT COUNT(*) FROM attendance 
                 WHERE emp_id=? AND strftime('%Y-%m', date)=? AND status='late' ''', (emp_id, month_year))
    late_days = c.fetchone()[0]
    total_days = on_time + late_days
    # បើធ្វើការតិចជាង 30 - OFF_DAYS_PER_MONTH ថ្ងៃ កាត់ប្រាក់
    expected_days = 30 - OFF_DAYS_PER_MONTH
    if total_days < expected_days:
        salary = SALARY_PER_MONTH * (total_days / expected_days)
    else:
        salary = SALARY_PER_MONTH
    # កាត់ប្រាក់ 5$ រាល់ថ្ងៃយឺត
    salary -= late_days * 5
    if salary < 0:
        salary = 0
    return round(salary, 2), on_time, late_days

def get_all_employees():
    c.execute("SELECT id, name, shift_type FROM employees WHERE is_active=1")
    return c.fetchall()

# ========== BOT COMMANDS ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("សូមស្វាគមន៍! ប្រើ /checkin ដើម្បីចូលធ្វើការ\nប្រើ /report ដើម្បីមើលរបាយការណ៍ថ្ងៃនេះ\nប្រើ /salary ដើម្បីមើលប្រាក់ខែ")

async def check_in(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_name = update.effective_user.first_name
    # ស្វែងរកបុគ្គលិកតាមឈ្មោះ (សន្មតថាឈ្មោះ Telegram ដូចឈ្មោះក្នុង DB)
    c.execute("SELECT id, shift_type FROM employees WHERE name=?", (user_name,))
    emp = c.fetchone()
    if not emp:
        await update.message.reply_text("អ្នកមិនមែនជាបុគ្គលិកក្នុងប្រព័ន្ធ។ សូមទាក់ទងអ្នកគ្រប់គ្រង។")
        return
    emp_id, shift_type = emp
    today = datetime.now().strftime("%Y-%m-%d")
    now_time = datetime.now().strftime("%H:%M")
    # ពិនិត្យមើលថាតើ shift ដែលស្លាកទុកត្រូវនឹងពេលបច្ចុប្បន្នដែរឬទេ?
    current_shift = get_shift_by_time()
    if shift_type != current_shift:
        await update.message.reply_text(f"វេនរបស់អ្នកគឺ {shift_type} ប៉ុន្តែពេលនេះជាវេន {current_shift}។ សូមពិនិត្យម្តងទៀត។")
        return
    # ពិនិត្យថាបាន checkin ហើយឬនៅ
    c.execute("SELECT id FROM attendance WHERE emp_id=? AND date=?", (emp_id, today))
    if c.fetchone():
        await update.message.reply_text("អ្នកបានចូលធ្វើការថ្ងៃនេះរួចហើយ។")
        return
    late_status = "late" if is_late(now_time, shift_type) else "on_time"
    c.execute("INSERT INTO attendance (emp_id, date, check_in, status, shift_type) VALUES (?, ?, ?, ?, ?)",
              (emp_id, today, now_time, late_status, shift_type))
    conn.commit()
    await update.message.reply_text(f"✅ ចូលធ្វើការថ្ងៃនេះនៅម៉ោង {now_time} | ស្ថានភាព: {late_status.upper()}")

async def show_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    report = generate_report()
    await update.message.reply_text(report, parse_mode="Markdown")

async def show_salary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_name = update.effective_user.first_name
    c.execute("SELECT id FROM employees WHERE name=?", (user_name,))
    emp = c.fetchone()
    if not emp:
        await update.message.reply_text("មិនឃើញឈ្មោះអ្នកក្នុងប្រព័ន្ធ។")
        return
    emp_id = emp[0]
    month_year = datetime.now().strftime("%Y-%m")
    salary, on_time, late_days = calculate_salary(emp_id, month_year)
    await update.message.reply_text(f"💵 **ប្រាក់ខែខែនេះ**: ${salary}\n"
                                    f"📆 ធ្វើការទាន់ពេល: {on_time} ថ្ងៃ\n"
                                    f"⚠️ យឺត: {late_days} ថ្ងៃ\n"
                                    f"*(កាត់ $5 រាល់ថ្ងៃយឺត)*", parse_mode="Markdown")

async def admin_add_employee(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # ប្រើសម្រាប់តែ admin: /add_employee ឈ្មោះ shift_type (day/night)
    if update.effective_user.id != YOUR_ADMIN_ID:  # ប្តូរ YOUR_ADMIN_ID ទៅជា Telegram ID Admin
        await update.message.reply_text("អ្នកគ្មានសិទ្ធិប្រើពាក្យបញ្ជានេះទេ។")
        return
    try:
        args = context.args
        name = args[0]
        shift_type = args[1]
        if shift_type not in ["day", "night"]:
            raise ValueError
        c.execute("INSERT INTO employees (name, shift_type) VALUES (?, ?)", (name, shift_type))
        conn.commit()
        await update.message.reply_text(f"បានបន្ថែមបុគ្គលិក {name} វេន {shift_type} ដោយជោគជ័យ។")
    except:
        await update.message.reply_text("ប្រើប្រាស់: /add_employee ឈ្មោះ shift_type (day/night)")

# ========== AUTO DAILY REPORT AT 12:00 & 00:00 ==========
async def auto_daily_report(context: ContextTypes.DEFAULT_TYPE):
    report = generate_report()
    # ផ្ញើទៅកាន់ Channel ឬ Admin
    await context.bot.send_message(chat_id=YOUR_ADMIN_ID, text=report, parse_mode="Markdown")

async def auto_night_report(context: ContextTypes.DEFAULT_TYPE):
    # របាយការណ៍វេនយប់
    await auto_daily_report(context)

# ========== MAIN ==========
def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("checkin", check_in))
    app.add_handler(CommandHandler("report", show_report))
    app.add_handler(CommandHandler("salary", show_salary))
    app.add_handler(CommandHandler("add_employee", admin_add_employee))

    # កំណត់ម៉ោងផ្ញើរបាយការណ៍ស្វ័យប្រវត្តិ (ម៉ោង 12:00 ថ្ងៃត្រង់ និង 00:00 យប់)
    j = app.job_queue
    j.run_daily(auto_daily_report, time=time(hour=12, minute=0), days=tuple(range(7)))
    j.run_daily(auto_night_report, time=time(hour=0, minute=0), days=tuple(range(7)))

    print("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
