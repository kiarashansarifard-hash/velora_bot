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

# ✅ آدرس دامنه رندرت (مطمئن شو دقیق باشه، بدون / انتهایی)
RENDER_URL = "https://velora-bot.onrender.com"

# ست کردن webhook (اگر قبلاً ست نکردی)
try:
    bot.remove_webhook()
    set_result = bot.set_webhook(url=f"{RENDER_URL}/{TOKEN}")
    print(f"Webhook set result: {set_result}")
except Exception as e:
    print(f"⚠️ خطا در ست کردن webhook: {e}")

# -------------------- متغیرها --------------------
MUTE_COMMAND = "دهن گالتو ببند نیگا"
MUTE_DURATION_DEFAULT = 60
TRIGGER = {
    "ولورا": [
        "بله. کارت رو بگو", "اینجام. چیکار داری؟", "سلام 👋", "سلام داش ردیفی؟",
        "سلاااام🙌", "سلام بهونه قشنگ من برای زندگی🤣🤣🤣"
    ]
}
muted_users = {}  # key: "{chat_id}_{user_id}" -> timestamp_until_unmute

# -------------------- قیمت‌ها (همون توی فایلت) --------------------
def get_dollar_price():
    try:
        url = "https://open.er-api.com/v6/latest/USD"
        data = requests.get(url, timeout=10).json()
        if "rates" not in data or "IRR" not in data["rates"]:
            return "❌ خطا در دریافت نرخ دلار"
        irr = data["rates"]["IRR"]
        toman = irr / 10
        return f"{int(toman):,} تومان"
    except Exception as e:
        return f"❌ خطا در دریافت نرخ دلار: {str(e)}"

def get_gold_price():
    try:
        url = "https://api.coingecko.com/api/v3/simple/price?ids=gold&vs_currencies=usd"
        data = requests.get(url, timeout=10).json()
        usd_per_ounce = data["gold"]["usd"]
        usd_per_gram = usd_per_ounce / 31.1
        # توجه: ممکن است get_dollar_price یک پیام خطا برگرداند؛ مراقب باش
        dollar_text = get_dollar_price()
        if dollar_text.startswith("❌"):
            return dollar_text
        dollar_toman = float(dollar_text.split()[0].replace(",", ""))
        gold_price_toman = usd_per_gram * dollar_toman
        return f"{int(gold_price_toman):,} تومان"
    except Exception as e:
        return f"❌ خطا در دریافت قیمت طلا: {str(e)}"

def get_crypto_price(symbol):
    try:
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={symbol}&vs_currencies=usd"
        data = requests.get(url, timeout=5).json()
        usd_price = data[symbol]["usd"]
        return f"${usd_price:,.2f}"
    except:
        return "❌ خطا در دریافت قیمت رمزارز"

# -------------------- تاریخ و زمان --------------------
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

# -------------------- هندلر پیام‌ها (چت خصوصی فقط) --------------------
@bot.message_handler(func=lambda m: m.chat.type == 'private')
def handle_private(message: Message):
    if not message.text:
        return
    text = message.text.lower()
    if "ولورا" in text:
        if "قیمت دلار" in text:
            bot.reply_to(message, f"💵 قیمت دلار: {get_dollar_price()}")
        elif "قیمت طلا" in text:
            bot.reply_to(message, f"🏅 قیمت طلا ۱۸ عیار: {get_gold_price()}")
        elif "قیمت بیت کوین" in text:
            bot.reply_to(message, f"₿ قیمت بیت‌کوین: {get_crypto_price('bitcoin')}")
        elif "قیمت تتر" in text:
            bot.reply_to(message, f"💲 قیمت تتر: {get_crypto_price('tether')}")
        elif "قیمت اتریوم" in text:
            bot.reply_to(message, f"🪙 قیمت اتریوم: {get_crypto_price('ethereum')}")
        elif any(k in text for k in ['تاریخ','ساعت','چند وقته','چندمه']):
            bot.reply_to(message, get_current_datetime())
        else:
            bot.reply_to(message, random.choice(TRIGGER['ولورا']))

# -------------------- میوت در گروه (اصلی) --------------------
@bot.message_handler(func=lambda message: message.chat.type in ['group','supergroup'])
def group_assistant(message: Message):
    if not message.from_user:
        return

    chat_id = message.chat.id
    user_id = message.from_user.id
    text = (message.text or "").strip().lower()
    chat_user_key = f"{chat_id}_{user_id}"

    # ۱) اگر کاربر در لیست میوت هست -> پیام رو حذف کن
    if chat_user_key in muted_users:
        if time.time() < muted_users[chat_user_key]:
            try:
                bot.delete_message(chat_id, message.message_id)
                print(f"Deleted message from muted {user_id} in {chat_id}")
            except Exception as e:
                print(f"⚠️ خطا در حذف پیام: {e}")
            return
        else:
            # زمان میوت تموم شده، حذف از دیکشنری
            del muted_users[chat_user_key]

    # ۲) دستور ریپلای میوت (ریپلای به پیام هدف)
    if message.reply_to_message and text.startswith(MUTE_COMMAND.lower()):
        parts = text.split()
        try:
            duration = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else MUTE_DURATION_DEFAULT
        except:
            duration = MUTE_DURATION_DEFAULT

        target_user = message.reply_to_message.from_user
        target_key = f"{chat_id}_{target_user.id}"
        muted_users[target_key] = time.time() + duration

        # تلاش برای restrict (فقط اگر سوپرگروپ)
        if message.chat.type == "supergroup":
            try:
                until_date = datetime.now() + timedelta(seconds=duration)
                # توجه: برای بعضی نسخه‌ها ممکنه نام پارامترها فرق کنه؛ اگر خطا دیدی print می‌کنه
                bot.restrict_chat_member(chat_id, target_user.id, can_send_messages=False, until_date=until_date)
                bot.reply_to(message, f"🔇 {target_user.first_name} برای {duration} ثانیه میوت شد! ✅")
            except Exception as e:
                print(f"⚠️ restrict_chat_member error: {e}")
                bot.reply_to(message, f"❌ نتونستم میوت کنم. مطمئنی من ادمینم و حق Restrict دارم؟")
        else:
            # گروه معمولی — حذف پیام‌ها
            bot.reply_to(message, f"🔇 {target_user.first_name} پیامش حذف شد! (گروه عادی)")
        return

    # ۳) کامندهای /mute و /unmute (اختیاری)
    if text.startswith("/mute") and message.reply_to_message:
        # مثال: /mute 30
        parts = text.split()
        try:
            duration = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else MUTE_DURATION_DEFAULT
        except:
            duration = MUTE_DURATION_DEFAULT
        target_user = message.reply_to_message.from_user
        target_key = f"{chat_id}_{target_user.id}"
        muted_users[target_key] = time.time() + duration
        try:
            until_date = datetime.now() + timedelta(seconds=duration)
            bot.restrict_chat_member(chat_id, target_user.id, can_send_messages=False, until_date=until_date)
            bot.reply_to(message, f"🔇 {target_user.first_name} برای {duration} ثانیه میوت شد! ✅")
        except Exception as e:
            print(f"⚠️ restrict_chat_member error (mute cmd): {e}")
            bot.reply_to(message, "❌ نتونستم میوت کنم. مطمئن شو من ادمینم.")
        return

    if text.startswith("/unmute") and message.reply_to_message:
        target_user = message.reply_to_message.from_user
        target_key = f"{chat_id}_{target_user.id}"
        if target_key in muted_users:
            del muted_users[target_key]
        try:
            # برداشتن محدودیت‌ها
            bot.restrict_chat_member(chat_id, target_user.id, can_send_messages=True)
            bot.reply_to(message, f"🔊 {target_user.first_name} آن‌میوت شد ✅")
        except Exception as e:
            print(f"⚠️ restrict_chat_member error (unmute): {e}")
            bot.reply_to(message, "❌ نتونستم آن‌میوت کنم. شاید دسترسی ندارم.")
        return

    # ۴) بقیه رفتارهای گروهی (مثلاً trigger)
    if 'ولورا' in text:
        bot.reply_to(message, random.choice(TRIGGER['ولورا']))
    elif any(k in text for k in ['تاریخ','ساعت','چند وقته','چندمه']):
        bot.reply_to(message, get_current_datetime())

# -------------------- webhook endpoint --------------------
@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    try:
        json_str = request.get_data().decode("utf-8")
        update = telebot.types.Update.de_json(json_str)
        bot.process_new_updates([update])
    except Exception as e:
        print(f"⚠️ error processing webhook update: {e}")
    return "OK", 200

# -------------------- اجرای Flask --------------------
if __name__ == "__main__":
    print("ربات ولورا با Webhook فعاله ✅")
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
