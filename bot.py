import os
import telebot
import random
import time
import requests
import pytz
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from telebot.types import Message
from flask import Flask, request

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
RENDER_URL = "https://velora-bot.onrender.com"
bot.remove_webhook()
bot.set_webhook(url=f"{RENDER_URL}/{TOKEN}")
MUTE_COMMAND = "دهن گالتو ببند نیگا"
MUTE_DURATION_DEFAULT = 60
TRIGGER = {
    "ولورا": [
        "بله. کارت رو بگو", "اینجام. چیکار داری؟", "سلام 👋", "سلام داش ردیفی؟",
        "سلاااام🙌", "سلام بهونه قشنگ من برای زندگی🤣🤣🤣"
    ]
}
muted_users = {}




def get_nobitex_prices():
    """دریافت قیمت‌ها از API رسمی نوبیتکس"""
    try:
        url = "https://api.nobitex.ir/market/stats"
        res = requests.get(url, timeout=10)
        data = res.json()["stats"]

        usdt = float(data["usdt-irt"]["latest"])
        btc_usdt = float(data["btc-usdt"]["latest"])
        eth_usdt = float(data["eth-usdt"]["latest"])
        xrp_usdt = float(data["xrp-usdt"]["latest"])

        message = (
            f"📊 قیمت‌ها از نوبیتکس:\n\n"
            f"💵 دلار (تتر): {usdt:,.0f} تومان\n"
            f"₿ بیت‌کوین: ${btc_usdt:,.2f}\n"
            f"Ξ اتریوم: ${eth_usdt:,.2f}\n"
            f"💠 ریپل: ${xrp_usdt:,.3f}"
        )
        return message
    except Exception as e:
        return f"❌ خطا در دریافت داده از نوبیتکس: {e}"

def get_current_datetime():
    try:
        tehran_tz = pytz.timezone('Asia/Tehran')
        now = datetime.now(tehran_tz)
        persian_weekdays = {
            0: "دوشنبه", 1: "سه‌شنبه", 2: "چهارشنبه",
            3: "پنجشنبه", 4: "جمعه", 5: "شنبه", 6: "یکشنبه"
        }
        weekday = persian_weekdays[now.weekday()]
        message = f"📅 تاریخ و ساعت دقیق:\n\n📆 {weekday}\n🗓 {now.strftime('%Y/%m/%d')}\n⏰ {now.strftime('%H:%M:%S')}\n🌍 منطقه زمانی: تهران (GMT+3:30)"
        return message
    except Exception as e:
        return f"❌ خطا در دریافت تاریخ: {str(e)}"




@bot.message_handler(func=lambda m: True)
def handle_all_messages(message):
    text = message.text.lower()

    if "ولورا" in text:
        if any(k in text for k in ["قیمت", "دلار", "بیت", "تتر", "اتریوم", "ریپل", "کریپتو"]):
            bot.reply_to(message, get_nobitex_prices())
        elif any(k in text for k in ['تاریخ', 'ساعت', 'چند وقته', 'چندمه']):
            bot.reply_to(message, get_current_datetime())
        else:
            bot.reply_to(message, random.choice(TRIGGER['ولورا']))



@bot.message_handler(func=lambda message: message.chat.type in ['group','supergroup'])
def group_assistant(message: Message):
    if not message.from_user or not message.text:
        return

    chat_id = message.chat.id
    user_id = message.from_user.id
    text = message.text.strip().lower()
    chat_user_key = f"{chat_id}_{user_id}"

    if chat_user_key in muted_users and time.time() < muted_users[chat_user_key]:
        try:
            bot.delete_message(chat_id, message.message_id)
        except:
            pass
        return
    elif chat_user_key in muted_users:
        del muted_users[chat_user_key]

    if message.reply_to_message and message.reply_to_message.from_user and text.startswith(MUTE_COMMAND.lower()):
        parts = text.split()
        try:
            duration = int(parts[1])
        except:
            duration = MUTE_DURATION_DEFAULT

        target_user_id = message.reply_to_message.from_user.id
        target_key = f"{chat_id}_{target_user_id}"
        muted_users[target_key] = time.time() + duration

        if message.chat.type == "supergroup":
            try:
                until_date = datetime.now() + timedelta(seconds=duration)
                bot.restrict_chat_member(chat_id, target_user_id, can_send_messages=False, until_date=until_date)
                bot.reply_to(message, f"🔇 {message.reply_to_message.from_user.first_name} برای {duration} ثانیه میوت شد! (سوپرگروپ)")
            except:
                bot.reply_to(message, f"🔇 {message.reply_to_message.from_user.first_name} برای {duration} ثانیه میوت شد! (حذف پیام)")
        else:
            bot.reply_to(message, f"🔇 {message.reply_to_message.from_user.first_name} پیامش حذف شد! (گروه عادی)")

# Webhook
@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    json_str = request.get_data().decode("utf-8")
    update = telebot.types.Update.de_json(json_str)
    bot.process_new_updates([update])
    return "OK", 200

# -------------------- اجرای Flask --------------------
if __name__ == "__main__":
    print("ربات ولورا با Webhook فعاله ✅")
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000))) 
