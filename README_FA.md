# pythash bot

ربات کامل مدیریت گروه تلگرام با پاسخ هوشمند، سیستم اعتبار، اتصال به هر API دلخواه
و بخش دونیت داخلی. تقریباً همه‌چیز هنگام اجرا و با دستورهای داخل ربات تنظیم می‌شود؛
فقط BOT_TOKEN و OWNER_ID در فایل .env قرار می‌گیرند.

## امکانات
- پاسخ هوشمند (منشن در گروه یا پیوی). FAQ اولویت دارد و اعتبار کم نمی‌کند.
- سرویس هوش مصنوعی قابل تعویض (پیش‌فرض: FreeModel — سازگار با OpenAI).
- سیستم اعتبار: هزینهٔ ثابت یا بر اساس توکن، همه قابل تنظیم در ربات.
- ابزار مدیریت: وارن/بن/کیک/میوت، قفل، فیلتر کلمات، سیاست لینک + وایت‌لیست.
- ضداسپم و وریفای هنگام ورود (پیش‌فرض خاموش، قابل روشن/خاموش در هر گروه).
- دونیت: کیف‌پول‌های کریپتو و/یا ریالی، با تنظیم از داخل ربات.
- ابزارها: نظرسنجی، یادآور، آمار، اعلامیه، کانال لاگ.

💸 حمایت مالی
حمایت مالی اختیاری است. اگر می‌خواهید از توسعه ادامه‌دار پروژه حمایت کنید، از یکی از آدرس‌های زیر استفاده کنید:

| 💰شبکه |🔐آدرس |
| --- | --- |
| TON	| UQDjrFdQK9hI8_m8yS-1JIkO_vNs7fjvGzbFDNgneenTKkYh|
| USDT Tron (TRC20)	| TUJgXLeVerr5QYxqr9RLYTQayanfnPgbAR|
| USDT BNB Smart Chain (BEP20) |	0xab83ebB5c57887E464B11AA2e2C919F1b33336c6|

# 🚀 راهنمای کامل بالا آوردن ربات روی سرور مجازی (قدم‌به‌قدم — مخصوص تازه‌کارها)

<aside>
🧭

این بخش را طوری نوشته‌ایم که اگر تا حالا هرگز با سرور کار نکرده‌ای هم بتوانی قدم‌به‌قدم جلو بروی. کافیست دستورها را دقیقاً همان‌طور که نوشته شده کپی کنی.

</aside>

## مرحله ۰ — سه چیزی که قبل از هر کاری لازم داری

**۱) توکن ربات (BOT_TOKEN):**

- در تلگرام به @BotFather پیام بده.
- دستور `/newbot` را بفرست.
- یک نام و یک یوزرنیم (که به `bot` ختم شود) بده.
- یک رشته طولانی مثل `123456:ABC-DEF...` به‌ت می‌دهد — همین توکن است.

**۲) شناسه عددی خودت (OWNER_ID):**

- به @userinfobot پیام بده؛ عددی که تحت عنوان `Id` می‌دهد همان OWNER_ID توست.

**۳) کلید FreeModel (FREEMODEL_API_KEY):**

- به freemodel.dev برو، با ایمیل ثبت‌نام کن و حساب را وریفای کن.
- از داشبورد، بخش API Key را کپی کن.

<aside>
⚠️

این سه مقدار را جایی یادداشت کن؛ در مراحل بعد به‌شان احتیاج داری. این‌ها رمز ورود ربات تو هستند — به کسی نده.

</aside>

## مرحله ۱ — خرید سرور مجازی (VPS)

- یک سرور مجازی (VPS) از هر ارائه‌دهنده‌ای تهیه کن (داخلی یا خارجی). ارزان‌ترین پلن هم کافیست.
- هنگام ساخت، **سیستم‌عامل Ubuntu 22.04** را انتخاب کن (ساده‌ترین گزینه).
- بعد از خرید، سه چیز به‌ت می‌دهند:
    - **IP سرور** (مثل `203.0.113.45`)
    - **نام کاربری** (معمولاً `root`)
    - **رمز عبور**

## مرحله ۲ — وصل شدن به سرور (SSH)

**اگر ویندوز داری:**

- برنامه **PowerShell** را باز کن (دکمه Start را بزن، تایپ کن PowerShell).
- دستور زیر را بزن (IP خودت را جایگزین کن):

```bash
ssh root@203.0.113.45
```

**اگر مک داری:** برنامه **Terminal** را باز کن و همین دستور بالا را بزن.

- اولین بار می‌پرسد ادامه بدهی؟ تایپ کن `yes` و Enter.
- سپس رمز سرور را وارد کن (هنگام تایپ چیزی دیده نمی‌شود — طبیعی است) و Enter.
- وقتی خطی مثل `root@server:~#` دیدی، یعنی وصل شدی. ✅

## مرحله ۳ — آماده‌سازی سرور

دستورهای زیر را یکی‌یکی بزن (هر خط را کپی کن، Enter):

```bash
apt update && apt upgrade -y
apt install -y python3 python3-venv python3-pip git nano
```

- اگر وسط کار پنجره آبی‌رنگی باز شد، فقط Enter بزن تا رد شود.

## مرحله ۴ — آوردن کدها روی سرور

دو راه داری؛ راه اول ساده‌تر است:

**راه الف — ساخت دستی پوشه‌ها و کپی کدها:**

```bash
mkdir -p pythash-bot/app/handlers pythash-bot/data
cd pythash-bot
```

سپس هر فایل را با ویرایشگر nano بساز و محتوای همان فایل را از بالای همین صفحه کپی کن. مثال:

```bash
nano app/config.py
```

- محتوای بلاک `app/config.py` را داخلش Paste کن (در ویندوز/مک با راست‌کلیک یا Ctrl+Shift+V).
- برای ذخیره: `Ctrl+O` سپس Enter؛ برای خروج: `Ctrl+X`.
- این کار را برای همه فایل‌های لیست‌شده در «ساختار فایل‌ها» تکرار کن (`requirements.txt`، `app/db.py`، `app/permissions.py`، `app/ai_provider.py`، `app/main.py` و همه فایل‌های داخل `app/handlers/`).

**راه ب — اگر کدها را روی GitHub گذاشتی:**

```bash
git clone https://github.com/USERNAME/pythash-bot.git
cd pythash-bot
```

## مرحله ۵ — ساخت محیط مجازی و نصب وابستگی‌ها

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

- اگر در ابتدای خط `(venv)` دیدی، یعنی درست است.

## مرحله ۶ — ساخت فایل تنظیمات (.env)

```bash
nano .env
```

محتوای زیر را بگذار و مقادیر را با موارد مرحله ۰ پر کن:

```bash
BOT_TOKEN=توکن_ربات_تو
OWNER_ID=شناسه_عددی_تو
FREEMODEL_API_KEY=کلید_freemodel
DATABASE_PATH=data/bot.sqlite3
DEFAULT_CREDITS=100
CREDIT_COST_MODE=fixed
CREDIT_COST_PER_MESSAGE=1
TOKENS_PER_CREDIT=1000
```

- ذخیره: `Ctrl+O` ، Enter ، `Ctrl+X`.

## مرحله ۷ — تست اجرا

```bash
python -m app.main
```

- اگر جمله `pythash bot started.` را دیدی، ربات روشن است! حالا در تلگرام به ربات `/start` بفرست.
- برای توقف موقت: `Ctrl+C`.

<aside>
⚠️

اگر پنجره را ببندی ربات خاموش می‌شود. برای اینکه همیشه و حتی بعد از ریست سرور روشن بماند، مرحله ۸ را انجام بده.

</aside>

## مرحله ۸ — روشن نگه داشتن دائمی با systemd

اول مسیر پوشه را پیدا کن:

```bash
pwd
```

خروجی مثلاً `/root/pythash-bot` است. حالا یک فایل سرویس بساز:

```bash
nano /etc/systemd/system/pythashbot.service
```

محتوای زیر را بگذار (اگر مسیر تو فرق دارد، `/root/pythash-bot` را عوض کن):

```
[Unit]
Description=pythash telegram bot
After=network.target

[Service]
WorkingDirectory=/root/pythash-bot
ExecStart=/root/pythash-bot/venv/bin/python -m app.main
Restart=always
RestartSec=5
User=root

[Install]
WantedBy=multi-user.target
```

ذخیره کن (`Ctrl+O`، Enter، `Ctrl+X`) و سپس:

```bash
systemctl daemon-reload
systemctl enable pythashbot
systemctl start pythashbot
```

ربات حالا دائمی روشن است و حتی بعد از ریست سرور خودبه‌خود بالا می‌آید. می‌توانی پنجره SSH را ببندی.

## مرحله ۹ — دستورات مدیریت ربات روی سرور

```bash
systemctl status pythashbot      # دیدن وضعیت (روشن/خاموش)
systemctl restart pythashbot     # ریستارت بعد از تغییر کد
systemctl stop pythashbot        # خاموش کردن
journalctl -u pythashbot -f      # دیدن لاگ‌ها و خطاها به صورت زنده (خروج: Ctrl+C)
```

## مرحله ۱۰ — به‌روزرسانی یا تغییر کدها

```bash
cd /root/pythash-bot
source venv/bin/activate
# فایل‌ها را با nano ویرایش کن یا git pull بزن
systemctl restart pythashbot
```

## عیب‌یابی خطاهای رایج

| علامت | علت احتمالی | راه‌حل |
| --- | --- | --- |
| `BOT_TOKEN در .env تنظیم نشده` | توکن خالی است | فایل .env را دوباره باز کن و توکن را درست بگذار |
| ربات در گروه کاری نمی‌کند | ادمین نیست | ربات را در گروه ادمین کن و دسترسی حذف/بن/محدودیت بده |
| خطا در ارتباط با API | کلید غلط | با `/test_api` تست کن؛ کلید FreeModel را بررسی کن |
| پاسخ هوش مصنوعی نمی‌دهد | API فعال نیست | `/list_apis` سپس `/activate_api freemodel` |

<aside>
✅

تمام! اگر تا اینجا را درست رفتی، ربات pythash bot روی سرور تو به‌صورت دائمی روشن است و آماده کار است. 🎉

</aside>
