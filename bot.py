import os
import telebot
import random
import time
import requests
import pytz
from datetime import datetime, timedelta
from telebot.types import Message
from flask import Flask
from threading import Thread

app = Flask('')

@app.route('/')
def home():
    return "I'm alive!"

def run():
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))

Thread(target=run).start()

TOKEN = os.getenv("TOKEN")
if not TOKEN:
    raise ValueError("TOKEN environment variable is not set!")

bot = telebot.TeleBot(TOKEN)

MUTE_COMMAND = "دهن گالتو ببند نیگا"
MUTE_DURATION_DEFAULT = 60
TRIGGER = {
    "ولورا": [
        "بله. کارت رو بگو", "اینجام. چیکار داری؟", "سلام 👋", "سلام داش ردیفی؟",
        "سلاااام🙌", "سلام بهونه قشنگ من برای زندگی🤣🤣🤣"
    ]
}

muted_users = {}

def get_dollar_price():
    url = "https://www.tgju.org/profile/usd"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")
    for h3 in soup.find_all("h3"):
        if "نرخ فعلی" in h3.get_text():
            return h3.get_text()
    return "قیمت پیدا نشد 😕"


@bot.message_handler(func=lambda m: True)
def reply_to_price(message):
    text = message.text.lower()
    if "ولورا" in text and "قیمت دلار" in text:
        price = get_dollar_price()
        bot.reply_to(message, f"💵 قیمت دلار: {price}")
    
def get_crypto_prices():
    try:
        url = "https://api.coingecko.com/api/v3/simple/price"
        params = {
            "ids": "bitcoin,ethereum,tether",
            "vs_currencies": "usd",
            "include_24hr_change": "true"
        }
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        message = "📊 قیمت ارزهای دیجیتال:\n\n"

        if "bitcoin" in data:
            btc_price = data["bitcoin"]["usd"]
            btc_change = data["bitcoin"].get("usd_24h_change", 0)
            change_emoji = "📈" if btc_change > 0 else "📉"
            message += f"₿ بیت کوین: ${btc_price:,.2f}\n"
            message += f"{change_emoji} تغییرات 24 ساعت: {btc_change:.2f}%\n\n"

        if "ethereum" in data:
            eth_price = data["ethereum"]["usd"]
            eth_change = data["ethereum"].get("usd_24h_change", 0)
            change_emoji = "📈" if eth_change > 0 else "📉"
            message += f"Ξ اتریوم: ${eth_price:,.2f}\n"
            message += f"{change_emoji} تغییرات 24 ساعت: {eth_change:.2f}%\n\n"

        if "tether" in data:
            usdt_price = data["tether"]["usd"]
            message += f"₮ تتر (USDT): ${usdt_price:.4f}\n"

        message += "\n" + get_usd_price()

        return message
    except Exception as e:
        return f"❌ خطا در دریافت قیمت: {str(e)}"

def get_current_datetime():
    try:
        tehran_tz = pytz.timezone('Asia/Tehran')
        now = datetime.now(tehran_tz)

        persian_weekdays = {
            0: "دوشنبه",
            1: "سه‌شنبه",
            2: "چهارشنبه",
            3: "پنجشنبه",
            4: "جمعه",
            5: "شنبه",
            6: "یکشنبه"
        }

        weekday = persian_weekdays[now.weekday()]

        message = f"📅 تاریخ و ساعت دقیق:\n\n"
        message += f"📆 {weekday}\n"
        message += f"🗓 {now.strftime('%Y/%m/%d')}\n"
        message += f"⏰ {now.strftime('%H:%M:%S')}\n"
        message += f"🌍 منطقه زمانی: تهران (GMT+3:30)\n"

        return message
    except Exception as e:
        return f"❌ خطا در دریافت تاریخ: {str(e)}"

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

    elif 'ولورا' in text:
        bot.reply_to(message, random.choice(TRIGGER['ولورا']))
    elif any(k in text for k in ['قیمت','کریپتو','بیت کوین','اتریوم','تتر']):
        bot.reply_to(message, get_crypto_prices())
    elif any(k in text for k in ['تاریخ','ساعت','چند وقته','چندمه']):
        bot.reply_to(message, get_current_datetime())

print("ربات ولورا فعاله ✅")
bot.infinity_polling(skip_pending=True)
