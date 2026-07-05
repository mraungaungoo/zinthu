import requests
import telebot
import time
import os
import threading
import sqlite3
import random
import json
from telebot import types
from gatet import Tele
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

# ==========================================
# ========== CONFIGURATION SECTION ==========
# ==========================================
TOKEN = '8975822364:AAFrVZdq_2CzxgcxRz_NdW2muIDYBmnZ5v0'
ADMIN_ID = '5831292144'
bot = telebot.TeleBot(TOKEN, parse_mode="HTML")
DEVELOPER = "@cyber_404io"
BOT_NAME = "Cyber V"
DB_NAME = "cyber_v_master.db"

# ==========================================
# ========== DATABASE (SQLITE) SECTION =======
# ==========================================
def init_db():
    """Initializes the SQLite database and handles migration from JSON if exists."""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (user_id TEXT PRIMARY KEY, credits INTEGER, ban_until INTEGER)''')
    
    # Check for migration from old users_db.json
    if os.path.exists("users_db.json"):
        try:
            with open("users_db.json", "r") as f:
                old_data = json.load(f)
                for uid, val in old_data.items():
                    credits = val["credits"] if isinstance(val, dict) else val
                    ban_until = val.get("ban_until", 0) if isinstance(val, dict) else 0
                    c.execute("INSERT OR IGNORE INTO users (user_id, credits, ban_until) VALUES (?, ?, ?)", 
                              (str(uid), credits, ban_until))
            print("[DB] Migration from JSON completed.")
        except Exception as e:
            print(f"[DB] Migration Error: {e}")

    # Add Admin with infinite credits if not exists
    c.execute("INSERT OR IGNORE INTO users (user_id, credits, ban_until) VALUES (?, ?, ?)", 
              (ADMIN_ID, 999999, 0))
    conn.commit()
    conn.close()

def get_user_data(user_id):
    """Retrieves user credits and ban status from SQLite."""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT credits, ban_until FROM users WHERE user_id = ?", (str(user_id),))
    res = c.fetchone()
    if not res:
        c.execute("INSERT INTO users (user_id, credits, ban_until) VALUES (?, ?, ?)", (str(user_id), 0, 0))
        conn.commit()
        res = (0, 0)
    conn.close()
    return {"credits": res[0], "ban_until": res[1]}

def update_credits(user_id, amount):
    """Updates user credits (can be positive or negative)."""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("UPDATE users SET credits = credits + ? WHERE user_id = ?", (amount, str(user_id)))
    conn.commit()
    conn.close()

def penalty_user(user_id, rate):
    """Applies penalty: 50% credit deduction and 30-minute ban."""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("UPDATE users SET credits = credits / 2, ban_until = ? WHERE user_id = ?", 
              (int(time.time() + 1800), str(user_id)))
    conn.commit()
    conn.close()
    
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
    bot.send_message(user_id, warning)

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
    """Returns a random proxy from proxy.txt if available."""
    if os.path.exists("proxy.txt"):
        with open("proxy.txt", "r") as f:
            proxies = [line.strip() for line in f if line.strip()]
            if proxies:
                p = random.choice(proxies)
                if p.startswith("http"): return {"http": p, "https": p}
                return {"http": f"http://{p}", "https": f"http://{p}"}
    return None

def typewriter_msg(chat_id, text):
    """Sends a message with a typewriter animation effect."""
    msg = bot.send_message(chat_id, "⌛")
    curr = ""
    for char in text:
        curr += char
        try:
            bot.edit_message_text(chat_id=chat_id, message_id=msg.message_id, text=curr + " ▮")
            time.sleep(0.05)
        except: pass
    bot.edit_message_text(chat_id=chat_id, message_id=msg.message_id, text=curr)

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
    markup.row(btn1, btn2)
    markup.row(btn3)
    return text, markup

def get_progress_bar(current, total):
    """Calculates progress bar and percentage."""
    if total == 0: return '▭' * 10, 0
    filled = int(10 * current // total)
    bar = '▬' * filled + '▭' * (10 - filled)
    perc = int((current / total) * 100)
    return bar, perc

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

@bot.callback_query_handler(func=lambda call: call.data in ["user_info", "rule", "plan", "back_to_main"])
def menu_cb(call):
    """Handles multi-page navigation with Back button."""
    uid = str(call.message.chat.id)
    data = get_user_data(uid)
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🔙 Back", callback_data="back_to_main"))
    
    if call.data == "back_to_main":
        text, markup = get_main_menu(call.from_user.first_name, uid, data['credits'])
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=text, reply_markup=markup)
    elif call.data == "user_info":
        info = f"""
<b>👤 USER INFORMATION</b>
━━━━━━━━━━━━━━━━━━━━━━━━
<b>Name:</b> {call.from_user.first_name}
<b>ID:</b> <code>{uid}</code>
<b>Credits:</b> <code>{data['credits']}</code>
<b>Status:</b> {"Admin" if uid == ADMIN_ID else "Premium User"}
━━━━━━━━━━━━━━━━━━━━━━━━
"""
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=info, reply_markup=markup)
    elif call.data == "rule":
        rules = f"""
<b>📜 BOT RULES</b>
━━━━━━━━━━━━━━━━━━━━━━━━
1. No Gen/Fake cards allowed.
2. High CVV Error rate = Auto-ban.
3. One file at a time.
4. Don't spam the gateway.
━━━━━━━━━━━━━━━━━━━━━━━━
Violation will lead to 50% credit penalty!
"""
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=rules, reply_markup=markup)
    elif call.data == "plan":
        plans = f"""
<b>💎 PREMIUM PLANS</b>
━━━━━━━━━━━━━━━━━━━━━━━━
<b>Basic:</b> 100 Credits - 5$
<b>Pro:</b> 500 Credits - 20$
<b>Unlimited:</b> Contact Admin
━━━━━━━━━━━━━━━━━━━━━━━━
<b>Contact:</b> {DEVELOPER}
"""
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=plans, reply_markup=markup)
    bot.answer_callback_query(call.id)

# ========== ADMIN COMMANDS ==========
@bot.message_handler(commands=["addcredit"])
def add_credit(message):
    if str(message.chat.id) != ADMIN_ID: return
    try:
        args = message.text.split()
        update_credits(args[1], int(args[2]))
        bot.reply_to(message, f"✅ Added {args[2]} credits to {args[1]}")
    except: bot.reply_to(message, "Usage: /addcredit [user_id] [amount]")

@bot.message_handler(commands=["rmcredit"])
def rm_credit(message):
    if str(message.chat.id) != ADMIN_ID: return
    try:
        args = message.text.split()
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("UPDATE users SET credits = 0 WHERE user_id = ?", (args[1],))
        conn.commit()
        conn.close()
        bot.reply_to(message, f"✅ Credits cleared for {args[1]}")
    except: bot.reply_to(message, "Usage: /rmcredit [user_id]")

@bot.message_handler(commands=["stats"])
def stats(message):
    if str(message.chat.id) != ADMIN_ID: return
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users")
    total = c.fetchone()[0]
    conn.close()
    bot.reply_to(message, f"📊 <b>Bot Statistics</b>\n━━━━━━━━━━━━━━━━━━━━━━━━\n<b>Total Users:</b> {total}\n━━━━━━━━━━━━━━━━━━━━━━━━")

# ==========================================
# ========== CHECKER ENGINE SECTION ==========
# ==========================================
user_sessions = {}

def check_card(cc, session):
    """Core function to check a single card using the gateway."""
    if not session['is_running']: return
    
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
            bank = b.get('bank', {}).get('name', '𝒖𝒏𝒌𝒏𝒐𝒘𝒏')
            cn = b.get('country', {}).get('name', '𝒖𝒏𝒌𝒏𝒐𝒘𝒏')
            emj = b.get('country', {}).get('emoji', '🏳️')
            dicr = b.get('scheme', '𝒖𝒏𝒌𝒏𝒐𝒘𝒏')
            typ = b.get('type', '𝒖𝒏𝒌𝒏𝒐𝒘𝒏')
        except: bank, cn, emj, dicr, typ = "𝒖𝒏𝒌𝒏𝒐𝒘𝒏", "𝒖𝒏𝒌𝒏𝒐𝒘𝒏", "🏳️", "𝒖𝒏𝒌𝒏𝒐𝒘𝒏", "𝒖𝒏𝒌𝒏𝒐𝒘𝒏"
        
        msg = f"""CC ☛ <code>{cc}</code>
Status ☛ <b>{st}</b>
Gate ☛ <b>Stripe Charge ${amt}</b>
Response ☛ <b>{last}</b>
❖ BIN ☛ <b>{cc[:6]} - {cn} {emj}</b>
❖ Details ☛ <b>{dicr}-{typ}</b>
❖ Bank ☛ <b>{bank}</b>
⏱️ Taken <b>{rt}s</b>
🤖 BY: {DEVELOPER}"""
        bot.send_message(session['chat_id'], msg)

def update_ui_thread(chat_id, msg_id, session):
    """Thread function to update the Progress UI every 5 seconds."""
    while session['is_running']:
        markup = types.InlineKeyboardMarkup()
        markup.row(types.InlineKeyboardButton(f"🔥 Charged: {session['charged']}", callback_data='x'),
                   types.InlineKeyboardButton(f"✅ OTP: {session['otp']}", callback_data='x'))
        markup.row(types.InlineKeyboardButton(f"🥀 Low: {session['low']}", callback_data='x'),
                   types.InlineKeyboardButton(f"❌ Dead: {session['declined']}", callback_data='x'))
        markup.row(types.InlineKeyboardButton(f"🌐 NetErr: {session['net_err']}", callback_data='x'))
        markup.row(types.InlineKeyboardButton(f"🛑 Stop Check", callback_data=f"stop_{chat_id}"))

        elapsed = round(time.time() - session['start'], 1)
        bar, perc = get_progress_bar(session['processed'], session['total'])

        text = f"""<b>𝐂𝐘𝐁𝐄𝐑 𝐕 𝐌𝐀𝐒𝐒</b>

𝘾𝙖𝙧𝙙 ➲ <code>{session['last_cc']}</code>
𝙂𝙖𝙩𝙚𝙬𝙖𝙮 ➲ <code>Stripe Charged</code>
𝘼𝙢𝙤𝙪𝙣𝙩 ➲ <code>{session['total']}</code>
<pre>𝙋𝙧𝙤𝙜𝙧𝙚𝙨𝙨 ➲ {bar} {perc}%</pre>
𝙏𝙤𝙩𝙖𝙡 𝙏𝙖𝙠𝙚𝙣 ➲ <code>{elapsed}s</code>"""
        
        try:
            bot.edit_message_text(chat_id=chat_id, message_id=msg_id, text=text, reply_markup=markup)
        except: pass
        time.sleep(5)

@bot.message_handler(content_types=["document"])
def handle_docs(message):
    """Handles incoming .txt files for checking."""
    uid = str(message.chat.id)
    banned, mins = is_banned(uid)
    if banned: return bot.reply_to(message, f"🚫 Banned for {mins}m")
    
    user_data = get_user_data(uid)
    if user_data["credits"] <= 0 and uid != ADMIN_ID: 
        return bot.reply_to(message, "❌ Insufficient Credits. Please buy more.")

    file_info = bot.get_file(message.document.file_id)
    downloaded = bot.download_file(file_info.file_path)
    lines = [l.strip() for l in downloaded.decode().split('\n') if l.strip()]
    
    if not lines:
        return bot.reply_to(message, "❌ File is empty.")

    # Initialize Session
    user_sessions[uid] = {
        'user_id': uid, 'chat_id': message.chat.id, 'total': len(lines),
        'charged': 0, 'otp': 0, 'low': 0, 'declined': 0, 'net_err': 0, 'processed': 0, 'cvv_err': 0,
        'charged_list': [], 'otp_list': [], 'low_list': [],
        'is_running': True, 'manual_stop': False, 'start': time.time(), 'last_cc': 'Wait...'
    }
    
    session = user_sessions[uid]
    msg_id = bot.reply_to(message, "🚀 <b>Starting Ultimate Master Check...</b>").message_id
    
    # Start UI Updater Thread
    threading.Thread(target=update_ui_thread, args=(message.chat.id, msg_id, session)).start()

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
        status_title = "🛑 Stopped by User" if session['manual_stop'] else "✅ Successfully Completed!"
        
        final_ui = f"""
<b>{status_title}</b>
📅 <b>Date:</b> {datetime.now().strftime('%d %b %Y, %I:%M %p')}
⏱️ <b>Time Taken:</b> {duration}s

📊 <b>Summary Report</b>
<pre>
Total Cards : {session['total']}
━━━━━━━━━━━━━━━━━━━━
Charged     : {session['charged']}
OTP / CVV   : {session['otp']}
Low Funds   : {session['low']}
Declined    : {session['declined']}
Dead/NetErr : {session['net_err']}
</pre>
🤖 <b>BY:</b> {DEVELOPER}
"""
        bot.edit_message_text(chat_id=message.chat.id, message_id=msg_id, text=final_ui)

        # Send Result Files
        for lst, name in [(session['charged_list'], 'Charged'), (session['otp_list'], '3DS_OTP'), (session['low_list'], 'LowFunds')]:
            if lst:
                res_path = f"{name}_{uid}.txt"
                with open(res_path, "w") as f: f.write("\n".join(lst))
                with open(res_path, "rb") as f: bot.send_document(message.chat.id, f, caption=f"✅ {name} Results")
                os.remove(res_path)

        # Deduct 1 credit per file check (Admin exempt)
        if uid != ADMIN_ID: update_credits(uid, -1)

@bot.callback_query_handler(func=lambda call: call.data.startswith('stop_'))
def stop_cb(call):
    """Handles the immediate stop button."""
    uid = call.data.split('_')[1]
    if uid in user_sessions:
        user_sessions[uid]['is_running'] = False
        bot.answer_callback_query(call.id, "🛑 Stopping Immediately...")

# ==========================================
# ========== MAIN ENTRY POINT ================
# ==========================================
if __name__ == "__main__":
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {BOT_NAME} is starting...")
    bot.remove_webhook()
    bot.polling(none_stop=True)
