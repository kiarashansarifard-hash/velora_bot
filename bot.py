import os
import telebot
import random
import time
import pytz
import requests
import jdatetime
from datetime import datetime, timedelta
from flask import Flask, request
from telebot import types
from telebot.types import Message

# -------------------- تنظیمات Flask --------------------
app = Flask(__name__)

@app.route("/", methods=["GET", "HEAD"])
def home():
    return "I'm alive!", 200

# -------------------- تنظیمات Bot --------------------
TOKEN = os.getenv("TOKEN")
if not TOKEN:
    raise ValueError("TOKEN environment variable is not set!")

bot = telebot.TeleBot(TOKEN)
RENDER_URL = "https://velora-bot.onrender.com"  # آدرس Render خودت رو بگذار

# ست کردن وبهوک
bot.remove_webhook()
bot.set_webhook(url=f"{RENDER_URL}/{TOKEN}")

# -------------------- متغیرها --------------------
MUTE_COMMAND = "دهن گالتو ببند نیگا"
MUTE_DURATION_DEFAULT = 60
muted_users = {}

TRIGGER = {
    "ولورا": [
        "بله. کارت رو بگو 😎", "اینجام، چیکار داری؟",
        "سلام 👋", "سلام داش ردیفی؟",
        "سلاااام🙌", "سلام بهونه قشنگ من برای زندگی 🤣🤣🤣"
    ]
}

# -------------------- تابع تاریخ --------------------
def get_datetime_text():
    try:
        tehran_tz = pytz.timezone('Asia/Tehran')
        now = datetime.now(tehran_tz)

        persian_weekdays = {
            0: "دوشنبه", 1: "سه‌شنبه", 2: "چهارشنبه",
            3: "پنجشنبه", 4: "جمعه", 5: "شنبه", 6: "یکشنبه"
        }

        weekday = persian_weekdays[now.weekday()]

        jnow = jdatetime.datetime.fromgregorian(datetime=now)

        text = (
            f"📅 تاریخ و ساعت دقیق:\n\n"
            f"🇮🇷 شمسی: {jnow.strftime('%Y/%m/%d')} ({weekday})\n"
            f"🌍 میلادی: {now.strftime('%Y/%m/%d')}\n"
            f"⏰ ساعت: {now.strftime('%H:%M:%S')}\n"
            f"🕓 منطقه زمانی: تهران (GMT+3:30)"
        )
        return text
    except Exception as e:
        return f"❌ خطا در دریافت تاریخ: {str(e)}"

# -------------------- راهنما --------------------
def get_help_text():
    return (
        "📘 *راهنمای دستورات ربات ولورا*\n\n"
        "💬 `ولورا` → جواب خوش‌آمد یا سلام مخصوص 😎\n"
        "📅 `ولورا تاریخ` یا فقط `تاریخ` → نمایش تاریخ شمسی و میلادی با ساعت تهران\n"
        "🔇 ریپلای کن و بنویس:\n"
        "   `دهن گالتو ببند نیگا 30` → میوت کاربر برای 30 ثانیه\n"
        "   `/mute 60` → (ریپلای کن) میوت 60 ثانیه‌ای\n"
        "   `/unmute` → (ریپلای کن) آن‌میوت کاربر\n"
        "🆘 `/help` → نمایش این راهنما\n\n"
        "⚙️ *نکته:* برای میوت باید ربات ادمین گروه باشه و دسترسی Restrict داشته باشه."
    )

# -------------------- کیبورد راهنما --------------------
def main_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("/help", "تاریخ", "ولورا")
    return markup

# -------------------- هندلر پیام‌ها (پی‌وی و گروه) --------------------
@bot.message_handler(commands=['help'])
def show_help(message: Message):
    bot.send_message(message.chat.id, get_help_text(), parse_mode="Markdown", reply_markup=main_keyboard())

@bot.message_handler(func=lambda m: m.chat.type == 'private')
def handle_private(message: Message):
    text = message.text.lower()

    if "ولورا" in text:
        bot.reply_to(message, random.choice(TRIGGER['ولورا']), reply_markup=main_keyboard())
    elif "تاریخ" in text or "ساعت" in text:
        bot.reply_to(message, get_datetime_text(), reply_markup=main_keyboard())
    elif text == "/help":
        show_help(message)
    else:
        bot.reply_to(message, "🫡 بنویس ولورا یا بزن /help برای راهنما", reply_markup=main_keyboard())

# -------------------- میوت در گروه --------------------
@bot.message_handler(func=lambda message: message.chat.type in ['group','supergroup'])
def group_assistant(message: Message):
    if not message.from_user or not message.text:
        return

    chat_id = message.chat.id
    user_id = message.from_user.id
    text = message.text.strip().lower()
    chat_user_key = f"{chat_id}_{user_id}"

    # حذف پیام اگه هنوز میوته
    if chat_user_key in muted_users and time.time() < muted_users[chat_user_key]:
        try:
            bot.delete_message(chat_id, message.message_id)
        except:
            pass
        return
    elif chat_user_key in muted_users:
        del muted_users[chat_user_key]

    # --- دستور میوت با ریپلای ---
    if message.reply_to_message and text.startswith(MUTE_COMMAND.lower()):
        parts = text.split()
        try:
            duration = int(parts[1])
        except:
            duration = MUTE_DURATION_DEFAULT

        target_user = message.reply_to_message.from_user
        target_key = f"{chat_id}_{target_user.id}"
        muted_users[target_key] = time.time() + duration

        try:
            until_date = datetime.now() + timedelta(seconds=duration)
            bot.restrict_chat_member(chat_id, target_user.id, can_send_messages=False, until_date=until_date)
            bot.reply_to(message, f"🔇 {target_user.first_name} برای {duration} ثانیه میوت شد ✅")
        except Exception as e:
            bot.reply_to(message, f"❌ نتونستم میوت کنم. ادمینم؟ خطا: {e}")
        return

    # --- /mute و /unmute ---
    if text.startswith("/mute") and message.reply_to_message:
        parts = text.split()
        duration = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else MUTE_DURATION_DEFAULT
        target_user = message.reply_to_message.from_user
        target_key = f"{chat_id}_{target_user.id}"
        muted_users[target_key] = time.time() + duration
        try:
            until_date = datetime.now() + timedelta(seconds=duration)
            bot.restrict_chat_member(chat_id, target_user.id, can_send_messages=False, until_date=until_date)
            bot.reply_to(message, f"🔇 {target_user.first_name} برای {duration} ثانیه میوت شد ✅")
        except Exception as e:
            bot.reply_to(message, f"❌ نتونستم میوت کنم: {e}")
        return

    if text.startswith("/unmute") and message.reply_to_message:
        target_user = message.reply_to_message.from_user
        target_key = f"{chat_id}_{target_user.id}"
        if target_key in muted_users:
            del muted_users[target_key]
        try:
            bot.restrict_chat_member(chat_id, target_user.id, can_send_messages=True)
            bot.reply_to(message, f"🔊 {target_user.first_name} آن‌میوت شد ✅")
        except Exception as e:
            bot.reply_to(message, f"❌ خطا در آن‌میوت: {e}")
        return

    # --- پاسخ‌های ساده ---
    if 'ولورا' in text:
        bot.reply_to(message, random.choice(TRIGGER['ولورا']))
    elif 'تاریخ' in text or 'ساعت' in text:
        bot.reply_to(message, get_datetime_text())
    elif text == '/help':
        show_help(message)

# -------------------- Webhook --------------------
@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    json_str = request.get_data().decode("utf-8")
    update = telebot.types.Update.de_json(json_str)
    bot.process_new_updates([update])
    return "OK", 200

# -------------------- اجرای Flask --------------------
if __name__ == "__main__":
    print("🔥 ربات ولورا با Webhook فعاله ✅")
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))        
