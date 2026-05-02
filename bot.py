import sqlite3
from datetime import datetime, time, timedelta
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import asyncio
import re

# ========== CONFIG ==========
TOKEN = "8714800328:AAFuj_8fUL4NmgNERTnRb3TmTe7wsjEfo9Y"
SALARY_PER_MONTH = 500  # 500 USD
WORK_DAY_SHIFT = ["09:00", "21:00"]   # វេនថ្ងៃ 9ព្រឹក-9យប់
NIGHT_SHIFT = ["21:00", "09:00"]      # វេនយប់ 9យប់-9ព្រឹក
LATE_THRESHOLD = 15  # យឺតបើចូលក្រោយ 15 នាទី
OFF_DAYS_PER_MONTH = 2  # ឈប់សម្រាក 2ថ្ងៃ/ខែ
YOUR_ADMIN_ID = @gmepl_bot  # ប្តូរទៅជា Telegram ID របស់អ្នក

# ========== DATABASE ==========
conn = sqlite3.connect("company_bot.db", check_same_thread=False)
c = conn.cursor()

# បង្កើតតារាងបុគ្គលិក
c.execute('''CREATE TABLE IF NOT EXISTS employees (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE,
    shift_type TEXT,
    is_active INTEGER DEFAULT 1
)''')

# បង្កើតតារាងកំណត់វត្តមាន
c.execute('''CREATE TABLE IF NOT EXISTS attendance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    emp_id INTEGER,
    date TEXT,
    check_in TEXT,
    status TEXT,
    shift_type TEXT
)''')

# បង្កើតតារាងប្រាក់ខែ
c.execute('''CREATE TABLE IF NOT EXISTS salary_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    month_year TEXT,
    emp_id INTEGER,
    days_worked INTEGER,
    late_days INTEGER,
    salary REAL
)''')

# បង្កើតតារាងស្នើសុំឈប់សម្រាក
c.execute('''CREATE TABLE IF NOT EXISTS leave_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    emp_id INTEGER,
    start_date TEXT,
    end_date TEXT,
    status TEXT DEFAULT 'pending'
)''')

conn.commit()

# ========== HELPER FUNCTIONS ==========
def get_shift_by_time():
    """កំណត់វេនបច្ចុប្បន្នតាមម៉ោង"""
    now = datetime.now().strftime("%H:%M")
    if WORK_DAY_SHIFT[0] <= now < WORK_DAY_SHIFT[1]:
        return "day"
    else:
        return "night"

def is_late(check_in_time_str, shift_type):
    """ពិនិត្យមើលថាយឺតឬអត់"""
    check_in = datetime.strptime(check_in_time_str, "%H:%M")
    if shift_type == "day":
        limit = datetime.strptime(WORK_DAY_SHIFT[0], "%H:%M")
    else:
        limit = datetime.strptime(NIGHT_SHIFT[0], "%H:%M")
    diff = (check_in - limit).total_seconds() / 60
    return diff > LATE_THRESHOLD

def generate_report():
    """បង្កើតរបាយការណ៍ប្រចាំថ្ងៃ"""
    today = datetime.now().strftime("%Y-%m-%d")
    c.execute("""
        SELECT e.name, a.check_in, a.status, a.shift_type 
        FROM attendance a 
        JOIN employees e ON a.emp_id = e.id 
        WHERE a.date = ?
    """, (today,))
    rows = c.fetchall()
    
    if not rows:
        return "ថ្ងៃនេះមិនទាន់មានការចូលធ្វើការទេ។"
    
    report = "📋 របាយការណ៍ប្រចាំថ្ងៃ\n"
    report += "=" * 30 + "\n\n"
    for name, check_in, status, shift in rows:
        status_text = "✓ ទាន់ពេល" if status == "on_time" else "⚠ យឺត"
        report += f"👤 {name} | {shift} shift | ចូល: {check_in} | {status_text}\n"
    return report

def calculate_salary(emp_id, month_year):
    """គណនាប្រាក់ខែបុគ្គលិកម្នាក់"""
    # រាប់ថ្ងៃធ្វើការ
    c.execute("""
        SELECT COUNT(*) FROM attendance 
        WHERE emp_id=? AND strftime('%Y-%m', date)=? AND status='on_time'
    """, (emp_id, month_year))
    on_time = c.fetchone()[0]
    
    c.execute("""
        SELECT COUNT(*) FROM attendance 
        WHERE emp_id=? AND strftime('%Y-%m', date)=? AND status='late'
    """, (emp_id, month_year))
    late_days = c.fetchone()[0]
    
    total_days = on_time + late_days
    expected_days = 30 - OFF_DAYS_PER_MONTH
    
    # គណនាប្រាក់ខែ
    if total_days < expected_days:
        salary = SALARY_PER_MONTH * (total_days / expected_days)
    else:
        salary = SALARY_PER_MONTH
    
    # កាត់ប្រាក់ពេលយឺត (5$ ក្នុងមួយថ្ងៃ)
    salary -= late_days * 5
    if salary < 0:
        salary = 0
    
    return round(salary, 2), on_time, late_days

def get_all_employees():
    """ទាញយកបុគ្គលិកទាំងអស់"""
    c.execute("SELECT id, name, shift_type FROM employees WHERE is_active=1")
    return c.fetchall()

# ========== BOT COMMANDS ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ពាក្យបញ្ជា /start"""
    await update.message.reply_text(
        "🤖 សូមស្វាគមន៍!\n\n"
        "📌 ពាក្យបញ្ជាដែលអាចប្រើបាន:\n"
        "/checkin - ចូលធ្វើការ\n"
        "/report - មើលរបាយការណ៍ថ្ងៃនេះ\n"
        "/salary - មើលប្រាក់ខែរបស់ខ្ញុំ\n"
        "/list_employees - បង្ហាញបុគ្គលិកទាំងអស់ (សម្រាប់ Admin)\n"
        "/add_employee - បន្ថែមបុគ្គលិកថ្មី (Admin only)"
    )

async def check_in(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ពាក្យបញ្ជា /checkin"""
    user_name = update.effective_user.first_name
    
    # ស្វែងរកបុគ្គលិក
    c.execute("SELECT id, shift_type FROM employees WHERE name=? AND is_active=1", (user_name,))
    emp = c.fetchone()
    
    if not emp:
        await update.message.reply_text("❌ អ្នកមិនមែនជាបុគ្គលិកក្នុងប្រព័ន្ធ។ សូមទាក់ទងអ្នកគ្រប់គ្រង។")
        return
    
    emp_id, shift_type = emp
    today = datetime.now().strftime("%Y-%m-%d")
    now_time = datetime.now().strftime("%H:%M")
    
    # ពិនិត្យវេន
    current_shift = get_shift_by_time()
    if shift_type != current_shift:
        await update.message.reply_text(
            f"⚠️ វេនរបស់អ្នកគឺ {shift_type} ប៉ុន្តែពេលនេះជាវេន {current_shift}។\n"
            f"សូមពិនិត្យម៉ោងធ្វើការរបស់អ្នក។"
        )
        return
    
    # ពិនិត្យថាបាន checkin ហើយឬនៅ
    c.execute("SELECT id FROM attendance WHERE emp_id=? AND date=?", (emp_id, today))
    if c.fetchone():
        await update.message.reply_text("✅ អ្នកបានចូលធ្វើការថ្ងៃនេះរួចហើយ។")
        return
    
    # ពិនិត្យយឺត
    late_status = "late" if is_late(now_time, shift_type) else "on_time"
    
    # រក្សាទុក
    c.execute("""
        INSERT INTO attendance (emp_id, date, check_in, status, shift_type) 
        VALUES (?, ?, ?, ?, ?)
    """, (emp_id, today, now_time, late_status, shift_type))
    conn.commit()
    
    status_text = "⚠️ យឺត" if late_status == "late" else "✓ ទាន់ពេល"
    await update.message.reply_text(
        f"✅ ចូលធ្វើការថ្ងៃនេះនៅម៉ោង {now_time}\n"
        f"ស្ថានភាព: {status_text}"
    )

async def show_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ពាក្យបញ្ជា /report"""
    report = generate_report()
    await update.message.reply_text(report)

async def show_salary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ពាក្យបញ្ជា /salary"""
    user_name = update.effective_user.first_name
    c.execute("SELECT id FROM employees WHERE name=?", (user_name,))
    emp = c.fetchone()
    
    if not emp:
        await update.message.reply_text("❌ មិនឃើញឈ្មោះអ្នកក្នុងប្រព័ន្ធ។")
        return
    
    emp_id = emp[0]
    month_year = datetime.now().strftime("%Y-%m")
    salary, on_time, late_days = calculate_salary(emp_id, month_year)
    
    await update.message.reply_text(
        f"💰 ប្រាក់ខែខែនេះ: ${salary}\n"
        f"📆 ធ្វើការទាន់ពេល: {on_time} ថ្ងៃ\n"
        f"⚠️ យឺត: {late_days} ថ្ងៃ\n"
        f"📌 កាត់ $5 រាល់ថ្ងៃយឺត"
    )

async def list_employees(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ពាក្យបញ្ជា /list_employees (សម្រាប់ Admin)"""
    if update.effective_user.id != YOUR_ADMIN_ID:
        await update.message.reply_text("❌ អ្នកគ្មានសិទ្ធិប្រើពាក្យបញ្ជានេះទេ។")
        return
    
    employees = get_all_employees()
    if not employees:
        await update.message.reply_text("📭 មិនទាន់មានបុគ្គលិកក្នុងប្រព័ន្ធទេ។")
        return
    
    text = "👥 បញ្ជីបុគ្គលិក\n" + "=" * 30 + "\n\n"
    for emp_id, name, shift_type in employees:
        text += f"ID: {emp_id} | {name} | វេន: {shift_type}\n"
    
    await update.message.reply_text(text)

async def add_employee(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ពាក្យបញ្ជា /add_employee [ឈ្មោះ] [day/night]"""
    if update.effective_user.id != YOUR_ADMIN_ID:
        await update.message.reply_text("❌ អ្នកគ្មានសិទ្ធិប្រើពាក្យបញ្ជានេះទេ។")
        return
    
    try:
        args = context.args
        if len(args) < 2:
            await update.message.reply_text("ប្រើប្រាស់: /add_employee ឈ្មោះ shift_type (day/night)")
            return
        
        name = " ".join(args[:-1])
        shift_type = args[-1].lower()
        
        if shift_type not in ["day", "night"]:
            await update.message.reply_text("shift_type ត្រូវតែជា 'day' ឬ 'night' ប៉ុណ្ណោះ។")
            return
        
        c.execute("INSERT INTO employees (name, shift_type) VALUES (?, ?)", (name, shift_type))
        conn.commit()
        await update.message.reply_text(f"✅ បានបន្ថែមបុគ្គលិក {name} វេន {shift_type} ដោយជោគជ័យ។")
    
    except sqlite3.IntegrityError:
        await update.message.reply_text("❌ ឈ្មោះបុគ្គលិកនេះមានរួចហើយក្នុងប្រព័ន្ធ។")
    except Exception as e:
        await update.message.reply_text(f"❌ មានបញ្ហា: {str(e)}")

async def delete_employee(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ពាក្យបញ្ជា /delete_employee [ឈ្មោះ]"""
    if update.effective_user.id != YOUR_ADMIN_ID:
        await update.message.reply_text("❌ អ្នកគ្មានសិទ្ធិប្រើពាក្យបញ្ជានេះទេ។")
        return
    
    if not context.args:
        await update.message.reply_text("ប្រើប្រាស់: /delete_employee ឈ្មោះ")
        return
    
    name = " ".join(context.args)
    c.execute("UPDATE employees SET is_active=0 WHERE name=?", (name,))
    conn.commit()
    
    if c.rowcount > 0:
        await update.message.reply_text(f"✅ បានលុបបុគ្គលិក {name} ពីប្រព័ន្ធ។")
    else:
        await update.message.reply_text(f"❌ រកមិនឃើញបុគ្គលិកឈ្មោះ {name} ទេ។")

# ========== AUTO DAILY REPORT ==========
async def auto_daily_report(context: ContextTypes.DEFAULT_TYPE):
    """ផ្ញើរបាយការណ៍ស្វ័យប្រវត្តិម៉ោង 12:00"""
    report = generate_report()
    await context.bot.send_message(chat_id=YOUR_ADMIN_ID, text=report)

async def auto_night_report(context: ContextTypes.DEFAULT_TYPE):
    """ផ្ញើរបាយការណ៍ស្វ័យប្រវត្តិម៉ោង 00:00"""
    report = generate_report()
    await context.bot.send_message(chat_id=YOUR_ADMIN_ID, text=report)

# ========== MAIN ==========
def main():
    """មុខងារចម្បងសម្រាប់បើកដំណើរការ Bot"""
    app = Application.builder().token(TOKEN).build()
    
    # បន្ថែម Command Handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("checkin", check_in))
    app.add_handler(CommandHandler("report", show_report))
    app.add_handler(CommandHandler("salary", show_salary))
    app.add_handler(CommandHandler("list_employees", list_employees))
    app.add_handler(CommandHandler("add_employee", add_employee))
    app.add_handler(CommandHandler("delete_employee", delete_employee))
    
    # កំណត់ការផ្ញើរបាយការណ៍ស្វ័យប្រវត្តិ
    job_queue = app.job_queue
    if job_queue:
        job_queue.run_daily(auto_daily_report, time=time(hour=12, minute=0), days=tuple(range(7)))
        job_queue.run_daily(auto_night_report, time=time(hour=0, minute=0), days=tuple(range(7)))
    
    print("🤖 Bot is running successfully...")
    app.run_polling()

if __name__ == "__main__":
    main()
