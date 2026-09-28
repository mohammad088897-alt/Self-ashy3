import asyncio
import os
import json
import random
import time
from datetime import datetime
from splusthon import SoroushClient, events
from splusthon.sessions import StringSession
from splusthon.tl.functions.account import UpdateProfileRequest

# ===============================
# 🔑 تنظیمات
# ===============================
PHONE_NUMBER = "989900254474"
SESSION_FILE = "fon88lsession.txt"
DOWNLOADS_DIR = "downloads"
os.makedirs(DOWNLOADS_DIR, exist_ok=True)

SPAM_FILE = f"{DOWNLOADS_DIR}/spam_texts.txt"
TIME_FILE = f"{DOWNLOADS_DIR}/time.txt"
ALLOWED_GROUPS_FILE = f"{DOWNLOADS_DIR}/allowed_groups.json"
FORWARD_SPEED_FILE = f"{DOWNLOADS_DIR}/forward_speed.txt"

for file, default in [
    (TIME_FILE, "1"),
    (FORWARD_SPEED_FILE, "0.5"),
    (SPAM_FILE, "")
]:
    if not os.path.exists(file):
        with open(file, 'w', encoding='utf-8') as f:
            f.write(default)

if not os.path.exists(ALLOWED_GROUPS_FILE):
    with open(ALLOWED_GROUPS_FILE, 'w', encoding='utf-8') as f:
        json.dump([], f)

# ===============================
# 🌐 متغیرها
# ===============================
is_spamming = False
is_attacking = False
ALLOWED_GROUPS = []
spam_tasks = {}
attack_tasks = {}
forward_tasks = {}
saved_messages = []
sent_messages = []
stats = {'spam': 0, 'attack': 0, 'forward': 0, 'total': 0}
bot_start_time = time.time()

# ===============================
# 📂 توابع مدیریت
# ===============================
def load_allowed_groups():
    try:
        with open(ALLOWED_GROUPS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return []

def save_allowed_groups(groups):
    try:
        with open(ALLOWED_GROUPS_FILE, 'w', encoding='utf-8') as f:
            json.dump(groups, f)
    except Exception as e:
        print(f"⚠️ Error: {e}")

def load_spam_texts():
    try:
        with open(SPAM_FILE, 'r', encoding='utf-8') as f:
            content = f.read()
            if not content:
                return []
            return [t.strip() for t in content.split('---SPLIT---') if t.strip()]
    except:
        return []

def save_spam_texts(spam_list):
    try:
        with open(SPAM_FILE, 'w', encoding='utf-8') as f:
            f.write('\n---SPLIT---\n'.join(spam_list))
    except Exception as e:
        print(f"⚠️ Error: {e}")

def load_forward_speed():
    try:
        with open(FORWARD_SPEED_FILE, 'r', encoding='utf-8') as f:
            return float(f.read().strip() or "0.5")
    except:
        return 0.5

def save_forward_speed(speed):
    try:
        with open(FORWARD_SPEED_FILE, 'w', encoding='utf-8') as f:
            f.write(str(speed))
    except Exception as e:
        print(f"⚠️ Error: {e}")

# ===============================
# 📖 راهنما
# ===============================
HELP_TEXT = """🔥 ATTACKER HELP
━━━━━━━━━━━━━━━━━━━━━━
/addspam - 
/delspam [number] - 
/listspam - 
/delallspam - 
/spam on -
/spam off - 
/start - 
/stop - 
/settime [seconds] - 
/attack - 
/stopattack - 
/setfor - 
/for [count] - 
/stopfor -
/showfor - 
/delfor [number] - 
/setforspeed [seconds] - 
/amar -
/deletetex -
/setgroup - 
/showgroups - 
/ping -
━━━━━━━━━━━━━━━━━━━━━━"""

# ===============================
# 🚀 راه‌اندازی کلاینت
# ===============================
if os.path.exists(SESSION_FILE):
    try:
        with open(SESSION_FILE, "r") as f:
            session_string = f.read().strip()
        session = StringSession(session_string) if session_string else StringSession()
    except:
        session = StringSession()
else:
    session = StringSession()

client = SoroushClient(session)

# ===============================
# 📋 هندلر دستورات
# ===============================
@client.on(events.NewMessage)
async def handler(event):
    global is_spamming, is_attacking, ALLOWED_GROUPS, sent_messages, stats, saved_messages
    
    try:
        me = await client.get_me()
        if event.sender_id != me.id:
            return
    except:
        return
    
    chat_id = event.chat_id
    text = (event.message.text or "").strip()
    
    if not text:
        return
    
    print(f"📩 {text}")

    # ===== HELP =====
    if text == "/help":
        await event.reply(HELP_TEXT)
        return

    # ===== PING =====
    if text == "/ping":
        start = time.time()
        msg = await event.reply("🏓 Pinging...")
        end = time.time()
        ms = round((end - start) * 1000, 1)
        uptime = int(time.time() - bot_start_time)
        hours = uptime // 3600
        minutes = (uptime % 3600) // 60
        await msg.edit(f"🏓 Pong!\nResponse: {ms}ms\nUptime: {hours}h {minutes}m")
        return

    # ===== ADDSPAM =====
    if text == "/addspam" and event.message.reply_to_msg_id:
        try:
            replied = await client.get_messages(chat_id, ids=event.message.reply_to_msg_id)
            if replied and replied.text:
                spam_list = load_spam_texts()
                full_text = replied.text.strip()
                if full_text in spam_list:
                    await event.reply("⚠️ Already exists!")
                else:
                    spam_list.append(full_text)
                    save_spam_texts(spam_list)
                    preview = full_text[:50].replace('\n', ' ') + ('...' if len(full_text) > 50 else '')
                    await event.reply(f"✅ Added! ({len(spam_list)})\n📝 {preview}")
            else:
                await event.reply("⚠️ Reply to a text message!")
        except Exception as e:
            await event.reply(f"❌ {e}")
        return

    # ===== DELSPAM =====
    if text.startswith("/delspam"):
        parts = text.split()
        if len(parts) >= 2:
            try:
                index = int(parts[1]) - 1
                spam_list = load_spam_texts()
                if 0 <= index < len(spam_list):
                    spam_list.pop(index)
                    save_spam_texts(spam_list)
                    await event.reply(f"✅ Removed! ({len(spam_list)})")
                else:
                    await event.reply(f"❌ Invalid number!")
            except ValueError:
                await event.reply("⚠️ /delspam [number]")
            return
        elif event.message.reply_to_msg_id:
            try:
                replied = await client.get_messages(chat_id, ids=event.message.reply_to_msg_id)
                if replied and replied.text:
                    spam_list = load_spam_texts()
                    if replied.text in spam_list:
                        spam_list.remove(replied.text)
                        save_spam_texts(spam_list)
                        await event.reply(f"✅ Removed! ({len(spam_list)})")
                    else:
                        await event.reply("❌ Not found!")
                else:
                    await event.reply("⚠️ Reply to a text message!")
            except Exception as e:
                await event.reply(f"❌ {e}")
            return
        else:
            await event.reply("⚠️ /delspam [number] or reply")
        return

    # ===== LISTSPAM =====
    if text == "/listspam":
        spam_list = load_spam_texts()
        if not spam_list:
            await event.reply("📭 Empty!")
            return
        msg = "📋 SPAM TEXTS:\n━━━━━━━━━━━━━━━\n"
        for i, s in enumerate(spam_list, 1):
            display = s[:40].replace('\n', ' ') + ('...' if len(s) > 40 else '')
            msg += f"{i}. {display}\n"
        msg += f"\n📊 Total: {len(spam_list)}"
        await event.reply(msg)
        return

    # ===== DELALLSPAM =====
    if text == "/delallspam":
        spam_list = load_spam_texts()
        if not spam_list:
            await event.reply("📭 Empty!")
            return
        save_spam_texts([])
        await event.reply(f"🗑️ {len(spam_list)} deleted!")
        return

    # ===== SPAM ON/OFF =====
    if text == "/spam on":
        if not load_spam_texts():
            await event.reply("❌ No spam texts! /addspam first")
            return
        await event.reply("✅ SPAM ENABLED!")
        return

    if text == "/spam off":
        is_spamming = False
        if chat_id in spam_tasks and not spam_tasks[chat_id].done():
            spam_tasks[chat_id].cancel()
        await event.reply("❌ SPAM DISABLED!")
        return

    # ===== SETTIME =====
    if text.startswith("/settime"):
        parts = text.split()
        if len(parts) < 2:
            await event.reply("⚠️ /settime [seconds]")
            return
        try:
            delay = float(parts[1])
            if delay < 0.1:
                delay = 0.1
            with open(TIME_FILE, 'w') as f:
                f.write(str(delay))
            await event.reply(f"⏱️ Speed: {delay}s")
        except:
            await event.reply("⚠️ Invalid number!")
        return

    # ===== START =====
    if text == "/start":
        spam_list = load_spam_texts()
        if not spam_list:
            await event.reply("❌ No spam texts! /addspam")
            return
        if is_spamming:
            await event.reply("⚠️ Already running!")
            return
        
        is_spamming = True
        await event.reply(f"🚀 SPAM STARTED! ({len(spam_list)})")
        
        try:
            with open(TIME_FILE, 'r') as f:
                delay = float(f.read().strip() or "1")
        except:
            delay = 1
        
        async def spam_loop():
            global is_spamming
            count = 0
            while is_spamming:
                try:
                    spam_list = load_spam_texts()
                    if not spam_list:
                        is_spamming = False
                        await client.send_message(chat_id, "⚠️ No texts left!")
                        break
                    chosen = random.choice(spam_list)
                    msg = await client.send_message(chat_id, chosen)
                    sent_messages.append(msg.id)
                    stats['spam'] += 1
                    stats['total'] += 1
                    count += 1
                    await asyncio.sleep(delay)
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    print(f"❌ {e}")
                    await asyncio.sleep(1)
            await client.send_message(chat_id, f"⛔ STOPPED! Total: {count}")
        
        if chat_id in spam_tasks:
            spam_tasks[chat_id].cancel()
        spam_tasks[chat_id] = asyncio.create_task(spam_loop())
        return

    # ===== STOP =====
    if text == "/stop":
        is_spamming = False
        if chat_id in spam_tasks and not spam_tasks[chat_id].done():
            spam_tasks[chat_id].cancel()
        await event.reply("⛔ STOPPING...")
        return

    # ===== ATTACK =====
    if text == "/attack":
        spam_list = load_spam_texts()
        if len(spam_list) < 5:
            await event.reply("❌ Need 5+ texts!")
            return
        if is_attacking:
            await event.reply("⚠️ Attack already running!")
            return
        
        is_attacking = True
        await event.reply(f"💥 ATTACK STARTED! ({len(spam_list)})")
        
        async def attack_loop():
            global is_attacking
            count = 0
            while is_attacking:
                try:
                    spam_list = load_spam_texts()
                    if not spam_list:
                        is_attacking = False
                        break
                    for _ in range(3):
                        chosen = random.choice(spam_list)
                        msg = await client.send_message(chat_id, chosen)
                        sent_messages.append(msg.id)
                        stats['attack'] += 1
                        stats['total'] += 1
                        count += 1
                    await asyncio.sleep(0.001)
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    print(f"❌ {e}")
                    await asyncio.sleep(0.1)
            await client.send_message(chat_id, f"⛔ ATTACK STOPPED! Total: {count}")
        
        if chat_id in attack_tasks:
            attack_tasks[chat_id].cancel()
        attack_tasks[chat_id] = asyncio.create_task(attack_loop())
        return

    # ===== STOP ATTACK =====
    if text == "/stopattack":
        is_attacking = False
        if chat_id in attack_tasks and not attack_tasks[chat_id].done():
            attack_tasks[chat_id].cancel()
        await event.reply("⛔ ATTACK STOPPED!")
        return

    # ===== SETFOR =====
    if text == "/setfor" and event.message.reply_to_msg_id:
        try:
            replied = await client.get_messages(chat_id, ids=event.message.reply_to_msg_id)
            if replied:
                saved_messages.append({
                    'chat_id': chat_id,
                    'msg_id': event.message.reply_to_msg_id,
                    'text': replied.text[:50] if replied.text else "No text"
                })
                await event.reply(f"✅ Saved! ({len(saved_messages)})")
            else:
                await event.reply("❌ Not found!")
        except Exception as e:
            await event.reply(f"❌ {e}")
        return

    # ===== SHOWFOR =====
    if text == "/showfor":
        if not saved_messages:
            await event.reply("📭 No saved messages!")
            return
        msg = "📋 SAVED:\n━━━━━━━━━━━━━━━\n"
        for i, sm in enumerate(saved_messages, 1):
            msg += f"{i}. {sm['text']}\n"
        await event.reply(msg)
        return

    # ===== DELFOR =====
    if text.startswith("/delfor"):
        parts = text.split()
        if len(parts) < 2:
            await event.reply("⚠️ /delfor [number]")
            return
        try:
            index = int(parts[1]) - 1
            if 0 <= index < len(saved_messages):
                saved_messages.pop(index)
                await event.reply(f"✅ Removed! ({len(saved_messages)})")
            else:
                await event.reply("❌ Invalid!")
        except:
            await event.reply("❌ Invalid!")
        return

    # ===== SETFORSPEED =====
    if text.startswith("/setforspeed"):
        parts = text.split()
        if len(parts) < 2:
            await event.reply("⚠️ /setforspeed [seconds]")
            return
        try:
            speed = float(parts[1])
            if speed < 0.1:
                speed = 0.1
            save_forward_speed(speed)
            await event.reply(f"⏱️ Forward speed: {speed}s")
        except:
            await event.reply("⚠️ Invalid number!")
        return

    # ===== FOR =====
    if text.startswith("/for"):
        if not saved_messages:
            await event.reply("❌ /setfor first!")
            return
        parts = text.split()
        count = 5
        try:
            if len(parts) >= 2:
                count = int(parts[1])
            if count <= 0:
                count = 1
        except:
            await event.reply("⚠️ /for [count]")
            return
        
        await event.reply(f"🔄 FORWARD STARTED! ({count})")
        speed = load_forward_speed()
        
        async def forward_loop():
            i = 0
            while i < count:
                try:
                    for sm in saved_messages:
                        if i >= count:
                            break
                        msg = await client.forward_messages(chat_id, sm['msg_id'], sm['chat_id'])
                        if hasattr(msg, 'id'):
                            sent_messages.append(msg.id)
                        stats['forward'] += 1
                        stats['total'] += 1
                        i += 1
                        await asyncio.sleep(speed)
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    print(f"❌ {e}")
                    await asyncio.sleep(1)
            await client.send_message(chat_id, f"✅ FORWARD DONE! ({i})")
        
        if chat_id in forward_tasks:
            forward_tasks[chat_id].cancel()
        forward_tasks[chat_id] = asyncio.create_task(forward_loop())
        return

    # ===== STOPFOR =====
    if text == "/stopfor":
        if chat_id in forward_tasks and not forward_tasks[chat_id].done():
            forward_tasks[chat_id].cancel()
            await event.reply("⛔ FORWARD STOPPED!")
        else:
            await event.reply("⚠️ Not running!")
        return

    # ===== AMAR =====
    if text == "/amar":
        spam_list = load_spam_texts()
        await event.reply(f"""
📊 STATS:
━━━━━━━━━━━━━━━
Spam: {stats['spam']}
Attack: {stats['attack']}
Forward: {stats['forward']}
Total: {stats['total']}
━━━━━━━━━━━━━━━
Texts: {len(spam_list)}
Sent: {len(sent_messages)}
Saved: {len(saved_messages)}
        """)
        return

    # ===== DELETETEX =====
    if text == "/deletetex":
        if not sent_messages:
            await event.reply("📭 No messages!")
            return
        msg = await event.reply(f"🗑️ Deleting {len(sent_messages)}...")
        deleted = 0
        for mid in sent_messages:
            try:
                await client.delete_messages(chat_id, mid)
                deleted += 1
            except:
                pass
            await asyncio.sleep(0.1)
        sent_messages = []
        stats = {'spam': 0, 'attack': 0, 'forward': 0, 'total': 0}
        await msg.edit(f"✅ {deleted} deleted!")
        return

    # ===== SETGROUP =====
    if text == "/setgroup":
        if chat_id not in ALLOWED_GROUPS:
            ALLOWED_GROUPS.append(chat_id)
            save_allowed_groups(ALLOWED_GROUPS)
            await event.reply(f"✅ Group added! ID: {chat_id}")
        else:
            await event.reply("⚠️ Already added!")
        return

    # ===== SHOWGROUPS =====
    if text == "/showgroups":
        if ALLOWED_GROUPS:
            await event.reply("📋 GROUPS:\n" + "\n".join([str(g) for g in ALLOWED_GROUPS]))
        else:
            await event.reply("📭 No groups set! (All allowed)")
        return

# ===============================
# 🚀 اجرای اصلی
# ===============================
async def main():
    print("🚀 Connecting...")
    try:
        ALLOWED_GROUPS.extend(load_allowed_groups())
        await client.start(phone=PHONE_NUMBER)
        with open(SESSION_FILE, "w") as f:
            f.write(client.session.save())
        me = await client.get_me()
        print(f"👤 Name: {me.first_name}")
        print(f"📱 Phone: {me.phone}")
        print(f"📋 Spam texts: {len(load_spam_texts())}")
        print("✅ Bot is ready!")
        print("🔥 Type /help for commands")
        await client.run_until_disconnected()
    except Exception as e:
        print(f"❌ {e}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⛔ Stopped!")
