import asyncio
import os
import json
from datetime import datetime, timedelta

from splusthon import SoroushClient, events
from splusthon.tl.functions.account import UpdateProfileRequest
from splusthon.sessions import StringSession


# =========================================================
# ⚙️ تنظیمات
# =========================================================

PHONE_NUMBER = "+989900254474"

SESSION_FILE = "fonex12plssession.txt"
TEXTS_FILE = "texts_config.json"
SUBSCRIPTION_FILE = "subscription.json"

SUBSCRIPTION_DAYS = 99999
ALLOWED_GROUPS = []

SLOT_IDS = (1, 2, 3)


# =========================================================
# 📋 سیستم اشتراک
# =========================================================

def create_subscription():
    now = datetime.now()
    expire_at = now + timedelta(days=SUBSCRIPTION_DAYS)

    data = {
        "started_at": now.isoformat(),
        "expire_at": expire_at.isoformat()
    }

    with open(SUBSCRIPTION_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    return expire_at


def get_expire_time():
    if not os.path.exists(SUBSCRIPTION_FILE):
        return create_subscription()

    try:
        with open(SUBSCRIPTION_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        expire_at = data.get("expire_at")
        if not expire_at:
            return create_subscription()

        return datetime.fromisoformat(expire_at)

    except Exception as e:
        print(f"❌ خطا در خواندن اشتراک: {e}")
        return None


def get_subscription_status():
    expire_at = get_expire_time()

    if expire_at is None:
        return "❌ وضعیت اشتراک نامشخص است."

    remaining = expire_at - datetime.now()

    if remaining.total_seconds() <= 0:
        return "⛔ اشتراک شما به پایان رسیده است."

    total_seconds = int(remaining.total_seconds())

    days = total_seconds // 86400
    total_seconds %= 86400

    hours = total_seconds // 3600
    total_seconds %= 3600

    minutes = total_seconds // 60

    return (
        "📋 اشتراک فعال\n"
        "━━━━━━━━━━━━━━\n"
        f"⏳ {days} روز، {hours} ساعت، {minutes} دقیقه باقی‌مانده"
    )


def subscription_is_valid():
    expire_at = get_expire_time()

    if expire_at is None:
        return False

    return datetime.now() < expire_at


# =========================================================
# 📝 مدیریت متن‌ها
# =========================================================

def load_texts():
    default = {
        "spam1": [],
        "spam2": [],
        "spam3": [],

        "reply1": [],
        "reply2": [],
        "reply3": [],

        "delete_reply": (
            "🔔 پیام حذف شد\n"
            "━━━━━━━━━━━━━━\n"
            "👤 نام: {user_name}\n"
            "🆔 شناسه: {user_id}\n"
            "🔗 یوزرنیم: {username}\n"
            "📝 شناسه پیام: {msg_id}\n"
            "📄 متن: {text}"
        ),

        "edit_reply": (
            "📝 پیام ویرایش شد\n"
            "━━━━━━━━━━━━━━\n"
            "👤 نام: {user_name}\n"
            "🆔 شناسه: {user_id}\n"
            "🔗 یوزرنیم: {username}\n"
            "📝 شناسه پیام: {msg_id}\n"
            "📄 متن جدید: {text}"
        )
    }

    if not os.path.exists(TEXTS_FILE):
        return default

    try:
        with open(TEXTS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        for key, value in default.items():
            if key not in data:
                data[key] = value

        return data

    except Exception:
        return default


def save_texts(data):
    with open(TEXTS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


texts = load_texts()


# =========================================================
# 🔐 Session
# =========================================================

if os.path.exists(SESSION_FILE):
    try:
        with open(SESSION_FILE, "r", encoding="utf-8") as f:
            session_string = f.read().strip()

        if session_string:
            session = StringSession(session_string)
            print("✅ سشن قبلی پیدا شد!")
        else:
            session = StringSession()
            print("🆕 سشن جدید ساخته شد!")

    except Exception:
        session = StringSession()
        print("🆕 سشن جدید ساخته شد!")

else:
    session = StringSession()
    print("🆕 سشن جدید ساخته شد!")


client = SoroushClient(session)


# =========================================================
# 🕐 ساعت اسم اکانت
# =========================================================

async def clock_name():
    while True:
        try:
            hour = datetime.now().strftime("%H:%M")

            await client(
                UpdateProfileRequest(
                    first_name=f"- MMD | {hour}"
                )
            )

            print(f"🕐 نام اکانت: - MMD | {hour}")

            await asyncio.sleep(
                max(1, 60 - datetime.now().second)
            )

        except asyncio.CancelledError:
            break

        except Exception as e:
            print(f"❌ خطا در تغییر اسم: {e}")
            await asyncio.sleep(5)


# =========================================================
# 📦 متغیرهای اصلی — سه اسلات مستقل
# =========================================================

saved_messages = {
    1: None,
    2: None,
    3: None
}

forward_tasks = {
    1: {},
    2: {},
    3: {}
}

spam_tasks = {
    1: {},
    2: {},
    3: {}
}

spam_configs = {
    1: {},
    2: {},
    3: {}
}

reply_tasks = {
    1: {},
    2: {},
    3: {}
}

reply_configs = {
    1: {},
    2: {},
    3: {}
}

sent_messages = {
    1: {},
    2: {},
    3: {}
}

stats = {
    1: {"spam": 0, "forward": 0, "reply": 0, "total": 0},
    2: {"spam": 0, "forward": 0, "reply": 0, "total": 0},
    3: {"spam": 0, "forward": 0, "reply": 0, "total": 0}
}

user_cache = {}


# =========================================================
# 🧰 ابزارهای عمومی
# =========================================================

def is_group_allowed(chat_id):
    if not ALLOWED_GROUPS:
        return True

    return chat_id in ALLOWED_GROUPS


def slot_text(kind, slot):
    return texts.get(f"{kind}{slot}", [])


def save_slot_text(kind, slot, values):
    texts[f"{kind}{slot}"] = values
    save_texts(texts)


def add_sent_message(slot, chat_id, message_id):
    sent_messages[slot].setdefault(chat_id, []).append(message_id)


def get_sent_messages(slot, chat_id):
    return sent_messages[slot].get(chat_id, [])


def reset_stats(slot, chat_id=None):
    if chat_id is None:
        stats[slot] = {
            "spam": 0,
            "forward": 0,
            "reply": 0,
            "total": 0
        }
    else:
        stats[slot] = {
            "spam": 0,
            "forward": 0,
            "reply": 0,
            "total": 0
        }


# =========================================================
# 😈 ENEMY — سه لیست مستقل
# =========================================================

ENEMY_FILES = {
    1: "enemy_users1.json",
    2: "enemy_users2.json",
    3: "enemy_users3.json"
}

enemy_users = {
    1: {},
    2: {},
    3: {}
}

enemy_indexes = {
    1: {},
    2: {},
    3: {}
}


def load_json_file(filename):
    if not os.path.exists(filename):
        return {}

    try:
        with open(filename, "r", encoding="utf-8") as f:
            data = json.load(f)

        return data if isinstance(data, dict) else {}

    except Exception:
        return {}


def save_json_file(filename, data):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


for slot in SLOT_IDS:
    enemy_users[slot] = load_json_file(ENEMY_FILES[slot])


# =========================================================
# 😈 متن‌های ENEMY 1
# این 50 متن فقط برای /enemy1 هستند
# =========================================================

enemy_replies_1 = [
    "کسننت",
    "بیناموس",
    "شاشیدم دهن مادرت",
    "الو جاکش خان",
    "ریدم دهن مادر کسکشت",
    "شاشیدم تا خرتناق دهن مادرت",
    "گوز مادر",
    "Madar Sag",
    "بیناموس",
    "الو شاشخور",
    "سگ دخترا",
    "مادرتو میبرم تو کوهو کمند میکنمش",
    "مرده کونی",
    "دستو پا نزن مامان کونی",
    "الو ریدم دهت مادر",
    "ساکت کیر تو همه کست",
    "مگه نمیگم ساکت بیناموس",
    "خار مادر کسکش گفتم ساکت",
    "لال کیرم تو خرتناق مادرت",
    "شاشیدم رو سینه های کتو کلفت مادرت",
    "جاکش خانوم",
    "ریدم تو کسننت",
    "چسیدم دهن مادرت مادرت بو کشید بی هوش شد",
    "ناموس جقی",
    "الو کیرم تو مرده او زدنت",
    "ناموس خر ساکت",
    "Kos nanant",
    "مرده خر",
    "Nanato Karadm",
    "Shashidam To Levan Madart Fekr Karaf Delster Hast Ta Tah Khord",
    "Namos koni",
    "Jendeh Namos",
    "Alo benamos",
    "Nnt",
    "Kharkose",
    "Abji Koni",
    "کسناموست",
    "ریدم دهن مادرت",
    "میشاشم تو بطری بجای ویتامین سی میدم مادرت میل کنه",
    "انقد نادرتو خوب کردم بابات کیلید خونه ر داده بهم میگه‌هروقت دوست داری بیا",
    "ابجی تو طوری گاییدم بلند شد رفت دست مامانتو گرفت گفت بیا تریسام",
    "اب کیرمو ریختم دهنت مادرت اونم یه دور قرقره کردو تا ته خورد",
    "مامان کسکش",
    "برده",
    "جاکش",
    "اسلیو",
    "کتکخور",
    "بیناموس",
    "فشخور",
    "سگ دخارا",
    "هاپو",
    "جسی",
    "هاپ هاپ کن",
    "Goz Namos",
    "Shol Namos",
    "Sag Namos",
    "الو بی بخار",
    "محارم کونی",
    "ناموس کسو",
    "شاش خور",
    "الو کیرم تو خرتناق مادرت",
    "مادرتو کشتم",
    "ناموس کسکش",
    "کیرم تو گولبول سفید های بدن مادرت",
    "کیرمو تک به تک فرو کردم تو تمامی موی رگ های موجود در کس مادرت",
    "میام دستتو میگیزم با هم بریم مادرتو بکنیم",
    "سلطان فش نده بیا دوست باشی با هم بریم ننتو بکنیم",
    "مادرتو میبرم وسط جنگل های هیرکانی با طناب میبندمش به درخت روش بی دی اس ام اجرا میکنم",
    "با جانسینا بگیریم ننتو بکنیم",
    "بدخا مدخا داشتی ایدی بده مادرتو بگام",
    "خایه خور",
    "ناموس پلشت",
    "ابکون",
    "کسننت",
    "مادرتو جلوی کولر گرفتم کردم که گرما اذیتش نکنه",
    "مادرت انقد عرق سگی خورده کسش اسیدی شده با هر لیسی که به کس مادرت میزنم زبونم اتیش میگیره",
    "کیرم تو PH لول کسمادرت",
    "ناموس کسخل",
    "برده",
    "مرده کسکش",
    "پدر کسکش",
    "یه تاکتیک خیلی نابی به ذهنم رسید من میام دست تورو میگیرم با هم میریم پیش بابات دست باباتومیگیریم سه تایی میریم ننتو میکنیم",
    "جدی جدی به مادرت گفتن کیر چند حرفه برگشته گفته کیر که حرف نداره؟",
    "عاشق اون تایمی شدم که اومدی خونه دیدی دارم ننتو میکنم سر اینکه این صحنه رو نبینی لامپ رو خاموش کردی",
    "بیغیرت",
    "محارم کونی",
    "بی بخار",
    "ناموس فلج",
    "کسناموست",
    "سکسناموس",
    "Kos nnt",
    "Namos khar",
    "Abji Koni",
    "Kos Nnt",
    "Madaro Kardam",
    "Ridam Dahan Madart",
    "Morde Goz",
    "Goz Khor",
    "الو بیناموس",
    "خارکسه",
    "شاشخور",
    "کسناموست",
    "خروار خروار کیر تو کسننت",
    "ناموست سگ",
    "الو همه کس کسکش",
    "شاش دهن مادرت",
    "صد دانه آلت هم رنگ کونت با نظم و ترتیب یک جا تو کسننت مادر قهبه عه مرده کسکش اینجا قافیه مافیه نداریم",
]

# =========================================================
# 😈 متن‌های ENEMY 2
# این 50 متن فقط برای /enemy2 هستند
# =========================================================

enemy_replies_2 = [
    "مادرتو میبرم پاهاشو میدم بالا شروع میکنم به خوردن کصش بابای تریاکیتم عین خیالش نیستو پای پکنیک کامشو میگیره بی غیرت زاده",
    "ادم های بی سروپای تازه لود  و خزوخیل عین تو میخان از ما نردبان بزنن ولی خیال اضافی ممنوع مادر جنده ",
    "حرف اضافی نباشه با فندک کس داغ مادرتو آتیش میزنم",
    "ریدم دهن اون مادر هرزه ی بدکارت همیشه درحال داد زدن کس پنجا هست",
    "صداتو بیار پایین هنجره ی مامانتو با چاقو زنجانی می‌برم میدم دهن بابات ",
    "ممبرای ناشناخته اپلیکشینی افتادی وردلمون تا سرشناسی و افتخاری ازمون کسب کنی اما کور خوندی کسکش ناموس",
    "افقونیه ناشی بر پشت تویتا سوار با نوامیست اینا درحال عبور از مرزو ورد به ایران اسوپاس",
    "باروت گزاشتیم دره کس نوامیستو با فوت جانانه دلهوره اور کسو موس مامانتو عینهو فنچ نیم وجبی میترکونیم",
    "دفعه بعد ریپلایی ازت ببینم کسیه صفرای مادرتو عینهو بغالی سر کوچه میکنم",
    "عقب موندی گدا ابجی جونتو میگیرم میبرم کسشو می‌زارم برا فروش",
    "کیرم پسه کله جرثومه هندوانه بغله مادرت ",
    "پوستر چیه گوناگون شکلو شباهیت گوریل خفنه دست به کونو مالیدنو ماساژور شبانه کیرو خایه ما بوسره دره کس مامانتو",
    "برو گمشو تا ناموستو با گوه سگ به درو دیوار نخوابوندم",
    "گمشو اونور تا مرده های گهواره نشینت که زیر یه ترانزیت خاک در حال پاسور با روحه مادره بی دستو پا و بابای دسته بزن نداره خدا نیامرزت میخوان با دو هبه قند گوه بزنن",
    "وقتی میگم لال مونی بگیر میگی چشم قربان ورگنه کیر کلفتمو میکنم تو رحم آبجی کوچیکت",
    "لال شو تا دندون های که برا پدر بزرگ کاکولدت مونده رو نریختم کف آسفالت کرده کونی ",
    "به پدر کسکشو بیغیرتت میگم این چه طرز تربیت کردنه  زنتو گاییدم مرده قهبه",
    "استخون های مادر جندتو از قبر میکشم بیرون و میشاشم رو قبر",
    "سگه بی غروره خار تا مادر پیاز خوره عقبمونده ی سادیسمی",
    " چرا دستات با سرعت نور میلرزه انقد ازم ترس داری خوابیدم روی مرده های حله خوره اسپم خوره مهلکه بی نفسه ترسوت",
    "چرا لرزش گرفتی شاشیدم به روحیه نازو نازکه مادره بی حاله مهلکه معتاده ابزار دزده عشایر نشینه کم پر حالت",
    "حرف اضافی نباشه که میزنم دونه دونه دندونای مادرت به همراه عصبش در میارم میزارم جا قرنیه مرده های کج شده بی دستو پای هلاگ شدت",
    "نمک نریز دندونای اموالته مشکل دارت و با سنگ میشکونم مرده خر",
    "گمشو اونور تا با قدرت یه تیکه عنه سگه هاسکی به شیردون تا شیرون مرده های وقیحه حقیرت نزدم",
    "میگیرم میشاشم تو ریه های مرده های پاسور بازت عقبمونده ی کسخل",
    "گمشو اونور تو صف وایستا تا یه ضربه مهلک دیگه به مرده های درون خاکه یه تخته مفتخورت بزنم",
    "کسکشه مفعوله بیچاره و دچار عقده های بچگیه جنده بودن مادرت",
    "سر پایین ریدم رو هیکل فرمالیته ی ناموس زشتو انترت",
    "شاش زرد و کف شده ی بچه سیزده ساله تویه دهن مادر کسکشت",
    "تو دکتر بازی هات با خاهرت که ته بیغیرتی و فسادتو نشون میداد هم مفعول بودی ",
    "نحس و نکره ی کتک خور مدفوع خوره بی‌غیرت ",
    "تلنباری مدفوع تویه طالع نحس و نگونه مادر بدعنق و بی عفاف ترکیز کشت",
    "شاشیدیم دره کس بیکرانو پره خطو خطوطو رد کیر مادر ",
    "از جایی که گفتن دست بالای دست بسیار هست ما میگیم کیر بالای کیر درکس ابجیت بسیار هست",
    "نوامیس گونی پوش پشتیبانی انواع جنده های خیابانی",
    "الت مذکور دره ناموسه چش سفیدو سر خیابونیت",
    "سیرکیه دماق قرمزی با گریمی دلقک نما و زشت مرده کونی",
    "تیروتار نیاکانو پودمانو فامیل نزدیک و دور پیرپاتالتو ریدم کس مادر",
    "شناس دیپلم ردی دیلاقه بیسوادو بی خرد ناملا و بی نوا ی کسکش ناموس",
    "دستمال کشه بی پدرمادره مفت گرونه بی عفاف و چاپار قوم و قبایل منشهور شده",
    " نایی برای استحفاظو احتراس موندن پرده بکارت خاهرو همشیره خودت رو  نداری",
    "موش خپل بی مصرف اونارانتیونومی گوگولیه مگولی ی مادر قهبه",
    "نفسگیر ترین دقایق ومراسم سیاه پوشونی ناموست به فرا رسیده",
    "سخت درتلاشی به گرده و خاکه پای نازو قلقلی مون برسی افقونیه مادر جنده ",
    "مادر سیب قرمز خوره عشایر نشنیه یه تخته کتک خوره مشکل داره سادیسمی",
    "کیر تو خمیده گاه مادره بدکاری جندت",
    "کیرمون تو مادره ذمیمه و ناستوده و نکوهیدت هری اونور",
    "مذکور دره چشو حدقه ابجی تو دل برو و زیبا عیالو کرست بدستت",
    "تکه تکه ازین اصطلاح معنای به جنده بودن مادرته افتادی",
    "بیا اینور زعیفه له شده زیر اوار"
]

# =========================================================
# 😈 متن‌های ENEMY 3
# این 50 متن فقط برای /enemy3 هستند
# =========================================================

enemy_replies_3 = [
    "هیچ جوره نمیتونی به اعتبار ما لطمه وارد کنی توله ی زنا",
    "فکر کردی ما باخت میدیم اشتباع فکر کردی ناموس سکسی",
    "خفه بمیر خارومادرکسکشه زنازاده کیر تویه اون دریچه های تنفسی مادرت",
    "مادرجنده ی زیر اب کاه مانند",
    "سلول های بنیادی بدن مادرتو گاییدم",
    "جیشه سگ توی دم و دستگاه واژیناله ناموست",
    "الت تناسلی زرافه تو کونه مادرت",
    "الت تناسلی زرافه تو کونه مادرت",
    "کلاهک اتمی کیرم توی اون لحظه یه وجود اومدن یوزرت",
    "جفت تخمام روی سینه مادرت گاگول ناموس",
    "النگو های مادرتو میفروشم خواهرتو میخرم",
    "شاش و ادرار و فضولات حیوانی و انسانی تو دهن ناموست",
    "حریف نیستی پلن خورده ی ولد کیر",
    "اسپرم های قدرتمندمو عین دلار میریزم رو سر مادرت",
    "امام علی و یاران باوفاش تو کونه مادرت",
    "گوه توی لوزالمعده ناموست ساکت",
    "کتک خور ترین و الت تناسلی پرست ترین فرد روی کره زمین لال",
    "تاریخ جلو میره ولی تو همون ادمه بیضه چرون و ولد زنا باقی موندی",
    "خروار خروار لجن توی حلقومه پدر و مادرت",
    "بزدل ناموسه خوش خنده یه قوم و خویش کونی",
    "یکی دو کانتیر آلته پرو پیمون ترو تازه تو کسه مامانه کریحت",
    "گوه توی دین و ایمون و هر چی که مادرت میپرسته",
    "ممبر دو روزه در دهاتی شاش تو کسه چروکیده ناموست",
    "تمومیه استخون بندی های بدن ناموست رو خورد کردم",
    "تخمام توی کونه مونث و مذکر های دودمان پودمان طایفه پیر پاتالت",
    "آلت های کمیاب و نادر توی شکل و شمایل بی ریخت و قیافه مادرت ",
    "خون ناموست رو عین ومپایر مکیدم",
    "خایه هامو برق بنداز کیر توی گور و کفن مرده هات",
    "سگه گوش به فرمان گوساله ناموس ",
    "ناموس تدوینگر بی ننه بابا ",
    "خاورمادر فاشیست بی ابرو صحبت نکن",
    "روزگار مادرتو سیاه میکنم ",
    "پدافند یکپارچه سپاه ننتو شکار کنه الهی",
    "فیس خوشگل خواهرتو با تیزی دفتر نقاشی کردم",
    "کسه خواهره اوتیسمیتو حلق اویز میکنم",
    "با شاتگان شلیک کردم تو قلب سیاه مادره بی احساست ",
    "سوتین مادر بزرگ کونیتو تو بانه حراج کردم ",
    "قالپاق پراید مادرتو دزدیدم ",
    "بهزیستی نبود تو و مادرت از گشنگی میمردید",
    "ناموس وابسته به کمیته امداد خفه ",
    "خداوند متعال با بیلاخ گذاشته سینه قبر مادرت خبر داری ",
    "وسط خیابون کیرمو میزارم دهن ناموست",
    "مادرتو با همزمن دستی هم زدم",
    "هروئین پدر معتاد قالتاقتو شبانه دزدیدم",
    "کیرم تو اون کله کچلت مادرجنده متادونی ",
    "التم داخله رحمه پر از عفونت ناموست",
    "مامانتو زیر بارون اسیدی تو قفس زندانی کردم ",
    "از خرپشته ملق زدم رو سر مادرت ",
    "عن دماغمو با شورت مادرت پاک کردم بیناموس ",
    "دهن مادرتو با کپسول اکسیژنی که سگای محلمون توش چسیدن بستم "
]

# اتصال هر نسخه به لیست مخصوص خودش
enemy_replies = {
    1: enemy_replies_1,
    2: enemy_replies_2,
    3: enemy_replies_3
}


def get_enemy_reply(slot, user_id):
    user_id = str(user_id)

    index = enemy_indexes[slot].get(user_id, 0)
    replies = enemy_replies[slot]

    reply = replies[index % len(replies)]

    enemy_indexes[slot][user_id] = (
        (index + 1) % len(replies)
    )

    return reply


# =========================================================
# 💚 FRIEND — سه لیست مستقل
# =========================================================

FRIEND_FILES = {
    1: "friend_users1.json",
    2: "friend_users2.json",
    3: "friend_users3.json"
}

friend_users = {
    1: {},
    2: {},
    3: {}
}

friend_indexes = {
    1: {},
    2: {},
    3: {}
}

for slot in SLOT_IDS:
    friend_users[slot] = load_json_file(FRIEND_FILES[slot])


friend_replies = {
    1: [
        "خان", "جنگی", "مشتی", "سوتون", "یدونه",
        "سلطان", "اشتباه کرد", "ولشکن", "بامرام",
        "سوتون", "جیگر", "عشق", "داش", "بزرگی کن",
        "با مرام", "با وقار", "لوتی", "لوتی منش",
        "جنگی", "سرور", "نوکرته", "مشتی", "عشق",
        "بزرگی کن", "ببخشش", "مشتی ای", "نایاب", "تک",
        "خاکی", "تودلی", "سالار", "پهلوون", "کاردرست",
        "اقا", "توپر", "با وجود", "تک پر", "عقاب",
        "شیر", "پرچمدار", "آس", "گنگ"
    ],
    2: [
        "خان", "جنگی", "مشتی", "سوتون", "یدونه",
        "سلطان", "اشتباه کرد", "ولشکن", "خفن",
        "لوتی منش", "جیگر", "عشق", "داش", "بزرگی کن",
        "با مرام", "با وقار", "لوتی", "لوتی منش",
        "جنگی", "سرور", "نوکرته", "لوتی", "گنگستر",
        "بزرگی کن", "ببخشش", "مشتی ای", "نایاب", "تک",
        "خاکی", "تودلی", "سالار", "پهلوون", "کاردرست",
        "اقا", "توپر", "با وجود", "تک پر", "عقاب",
        "شیر", "پرچمدار", "آس", "گنگ"
    ],
    3: [
        "خان", "جنگی", "مشتی", "سوتون", "یدونه",
        "سلطان", "اشتباه کرد", "ولشکن", "خفن",
        "جنگی", "جیگر", "عشق", "داش", "بزرگی کن",
        "با مرام", "با وقار", "لوتی", "لوتی منش",
        "جنگی", "سرور", "نوکرته", "یدونه", "سلطان",
        "بزرگی کن", "ببخشش", "مشتی ای", "نایاب", "تک",
        "خاکی", "تودلی", "سالار", "پهلوون", "کاردرست",
        "اقا", "توپر", "با وجود", "تک پر", "عقاب",
        "شیر", "پرچمدار", "آس", "مشتی"
    ]
}

# =========================================================
# 👩 ANTIGIRL — سه لیست مستقل
# =========================================================

ANTIGIRL_FILES = {
    1: "antigirl_users1.json",
    2: "antigirl_users2.json",
    3: "antigirl_users3.json"
}

antigirl_users = {
    1: {},
    2: {},
    3: {}
}

antigirl_indexes = {
    1: {},
    2: {},
    3: {}
}

for slot in SLOT_IDS:
    antigirl_users[slot] = load_json_file(
        ANTIGIRL_FILES[slot]
    )


# =========================================================
# 👩 متن‌های ANTIGIRL 1
# این 50 متن فقط برای /antigirl1 هستند
# =========================================================

antigirl_replies_1 = [
        "جنده ساکت",
    "مغزمو خوردی ساکت شو جنده",
    "مگه نمیگم ساکت؟",
    "بو تن ماهی گپو برداشت",
    "لفتو بزن گپو بوی تن ماهی گرفت",
    "اه اه چندش بزن بیرون",
    "ریدی به گپ با کست",
    "با بوی کست خفه مون کردی🤮",
    "د برو بیرون پتیاره",
    "تو کستو با مسواک هم تمیز نمیتونی کنی",
    "دفعه بعدی که یکی اومد بکنتت بگو جای روان کننده او وازلین مایع دستشویی بریزه بکنتت بلکه کست تمیز شد",
    "البته این کسی که تو داری وایتکس هم بریزن تو تمیز نمیشه که نمیشه",
    "کیرم تو PH لول کست",
    "انقد عرق سگی به خوردت دادن کسو کونت گزاشتن کست اسیدی شده",
    "بوی کست کشتمون گمشو بیرون دیگه",
    "حال به هم زن جای جق زدن وایتکس بریز تو کست",
    "خداسر شاهده کستو که دیدم از پشت گوشی فهمیدم بوی تن ماهی میده از لحاظ ظاهر که چه عررررض کنم کست شبیه زیر بقل گربه مرده بود",
    "تو بمن میگفتی کست صورتیه پس چرا ذغالی بود😭",
    "برو بیرون دخترک سکسچتر",
    "سکس چت پیوی این فرد ریپلای شده",
    "این فردی که روش ریپلای کردم دنبال 7272627میلیون فرد برای سکسچت کردن میباشد",
    "سکس چت پیوی ایشون فقط لطفا رفتید پیویش درخواست شات از کس این شخص نکنید که اب کمرتون خشک میشه با دیدن کسش",
    "با تکس های این فرد جق بزنید بهتر از اینکه که عکس کسشو بگیرید جق بزنید من دیدم واقعا ریدم",
    "چرا کست اینجوریه انگاری یکی ریده تو کست",
    "سکستچتر برو بیرون",
    "چک خورو لگد خور پسرا بزن بیرون",
    "من بین گاو هلندی و تو گاو هلندی رو انتخاب میکنم . اون حداقل بیرونش مشکیه توش صورتیه برا تو پشت او رو او داخلو بیرونو همه جاااات ذغالیه کثیف",
    "خیلی حال بهم زنی",
    "حس میکنم جای روان کننده و وازلین از روغن تن ماهی استفاده میکنن میکننت ",
    "ولا بخدا این کسی که تو داری من اگه دختر بودم جات داشتم میرفتم عمل تغیر جنسیت انجام میدادم پسر میشدم",
    "تو خودت خودتو جلوی اینه میبینی حالت بد نمیشه؟",
    "فش خور پسرا",
    "همینجوری ادامه بدی ماه بعد یه پنله سکس چت پیوی فوروارد میکنی تو گپا که مدل های سکس چت توش ذکر شده با قیمت",
    "سکس چت از نوع بی دی اس ام پیوی این شخص کاملا رایگان",
    "اگه پیوی این شخص رفتید برای سکس چت و ازتون پول خواست از کد تخفیف #تن‌ماهی استفاده کنید شامل 100 درصد تخفیف میشید",
    "والا من شنیدم پیویت عکس کیر میفرستن گوشی رو بوس میکنی یا میمالی به سرو صورتت قضیه چیه",
    "سر تو سایت دیجی کالا که کاملا قانونی و اسلامی هست اومد دیلدو موجود کرد",
    "یکی از بچها رو برده بودی خونتون برای درست کردن نذری یارو رفته بود تو اتاقت دیده بود کلکسیون دیلدو داری ریده بود",
    "سکس چت که میکنی پوزیشن هم میگیری؟",
    "عکس کستو باید بزنیم در قندون بچها ببینن بترسن دست نزنن به قندون",
    "یه زمان بچه کوچیک هارو با صدا و عکس ممد قلی میترسوندن از سال 400 به بعد که تو پا گزاشتی تو عرصه سکس چتری بجای ممد قلی عکس کس تورو به بچها نشون میدن و بچها میترست",
    "تروخدا به هرکی میخوای نود بدی تایمی بده این صحنه رو یارو تا ابد نبینه ۱۰ ثانیه ببینه بگذره",
    "هرچند عکس کس تو که بوی تن ناهی میده و شباهت داره به گربه مرده تا سالیان سال از یاد ها و خاطره ها نخواهد رفت",
    "ابو علی سینا اومد گفت واژن انقدر زیباست و خوس بو عه که باید تسبیهش ورد به گل نرگس. فکر کنم بدبختی کس تورو ندیده بود مگر نه شباهت میداد به گربه های توی سطل اشغال",
    "سکس چت داستانی هم میری یا فقط تک کلمه؟",
    "سیکتیر لگد خور",
    "فش خور پسرا",
    "سکس چتر معروف",
    "جهت سکس چت برید پیوی این شخص با کد تخفیف #تن‌ماهی وارد شوید شامل یه پک عکس از کسو کون بیریختش میشوید",
    "من باشم کد تخفیف نمیزنم عکس کستو نبینم حال مالم بد شه"
]

# =========================================================
# 👩 متن‌های ANTIGIRL 2
# این 50 متن فقط برای /antigirl2 هستند
# =========================================================

antigirl_replies_2 = [
    "یه نود بده",
    "یه نود بده اذیت نکن",
    "یه نوده نودو رد کن بیاد",
    "ردش کن نودو",
    "اصلا نخواستم کی مشتاقه کسه جروکیده و سیاه زشت تورو ببین؟",
    "چندشه بو گندو",
    "گپو بو تن ناهی برداشت",
    "سیکتیر بیرون ریدی به گپ با بوی کست",
    "میشه بیام برینم دهنت انقد برینم تا خرتناق پر بشی از گوه",
    "سکس چت رایگان میکنی یا پولی",
    "سگ تورو رایگان هم نمیکنه",
    "کسه زشت",
    "عوق",
    "سیکتیر اون ور کسه بد بو🤮",
    "حال به هم زن",
    "سیکتیر جاکش",
    "دخترکه سکسچتر",
    "سکس چت پیوی این شخص ریپلای شده",
    "این شخصی که روش ریپلای شده علاقه خواصی به کیر داره",
    "شنیدم سر کیر دعوا میکنی",
    "جنده سر کیر دعوا نکن",
    "صب تا شب داری سر کیرو خایه این پسر اون پسر دعوا و بحث میکنی",
    "یه دو دقیقه ول کن کیرو خایمو",
    "نمیدم دستت خایه مو",
    "کست بد بود",
    "کسه زشت",
    "شنیدم دوست پسرت ازت نود خواسته برداشتی لوله پلیکا رو کردی تو کست ویدیو فرستادی بهش",
    "کست انقد گشاده که کیر بکن هات توی کست حکم موی رگ داره",
    "برینم تو کست بوی کست باز هم نمیره",
    "یعنی برینم توی کست بوی کست نمیزاره بوی ریدن من بیاد",
    "چقد کسه بد بویی داری",
    "برا گاییدنت باید رو سرت چهار تا گونی کشید",
    "برای بو کشیدن کست باید وان میلیون دالرز پول خرج خرید ماسک کرد",
    "شنیدم از بقل سطل اشغال رد میشی گربه های مرده از بوی کست بیدار میشن فرار میکنن",
    "عرق زیر بقلمو بریزم تو کست",
    " تو که میگفتی کست صورتیههه😭😭",
    "کسه بد بو🤮😭",
    "خیلی حال بهم زنی",
    "واقعا عوقم گرفت",
    "چندش",
    "بد بو",
    "کسه زشت",
    "کسه بیریخت",
    "حالمون از کست بهم خورد",
    "برو بیرون کسه زشت",
    "کستو با مسواک هم بشوری دیگه درست نمیشه",
    "برو کستو با چاغو ببر یکی دسگه جاش بزار",
    "کستو باید با نخ سوزن بدوزن شاید بوش در نیومد",
    "کست چرا انقد بیریخته؟",
    "جنده خانوم هیس حالمونو بهم زدی"
]

# =========================================================
# 👩 متن‌های ANTIGIRL 3
# این 50 متن فقط برای /antigirl3 هستند
# =========================================================

antigirl_replies_3 = [
    "Sag Pesara",
    "kir Khor",
    "Khaeyh Khor",
    "Kost Chera Enghad Zeshteh ? ",
    "Ridam To Koset",
    "koset khafamon kard",
    "Sag Pesara",
    "Khayeh Khor",
    "Kir Khor Pesara",
    "Chak Khor",
    "Fosh Khor",
    "Sag Hame Kare",
    "Dastam Gir Kard To Koset",
    "Kost Cheghad Bo medeh🤮",
    "Chak Khor",
    "Fosh Khor",
    "Zir Dast Pesara",
    "Zir Khab Pesara",
    "Kir Tak Tak Pesaray In Gap To Koset",
    "Kheli Koset Bo Mede",
    "Hal B Ham Zan",
    "Chendeshh",
    "Kos khol",
    "Sekter Biron",
    "Kose Bad Bo",
    "Hal B Ham Zan",
    "Kore Khar",
    "Boroooo Birooon",
    "Jende",
    "Jendeh Khanom",
    "Hal B ham Zan",
    "Sekter Biron",
    "Chendesh",
    "Sag Pesara ",
    "Zir Khab",
    "Kir khor",
    "Khaye Khor",
    "Kam Khayeh Bokhor",
    "Goz khor",
    "Boz Maje",
    "Sage Zesht",
    "Koseto Nemekhoram",
    "Kos Zesht",
    "Sage Zesht",
    "Koset Shabeh Gorbeh Mordeh Hast",
    "Khele Koset Zeshte",
    "Jendeh",
    "birooon borooo",
    "Koset khafamon Kard",
    "Sekter Biron Jende Khanom Ker To Kose zrshtet Berh"
]

# اتصال هر نسخه به لیست مخصوص خودش
antigirl_replies = {
    1: antigirl_replies_1,
    2: antigirl_replies_2,
    3: antigirl_replies_3
}


def get_antigirl_reply(slot, user_id):
    user_id = str(user_id)

    index = antigirl_indexes[slot].get(user_id, 0)
    replies = antigirl_replies[slot]

    reply = replies[index % len(replies)]

    antigirl_indexes[slot][user_id] = (
        (index + 1) % len(replies)
    )

    return reply


# =========================================================
# 👤 ذخیره اطلاعات کاربران
# =========================================================

@client.on(events.NewMessage)
async def cache_user_info(event):
    try:
        if (
            event.sender_id
            and event.sender_id not in user_cache
        ):
            try:
                user = await client.get_entity(
                    event.sender_id
                )

                username = (
                    f"@{user.username}"
                    if getattr(user, "username", None)
                    else "ندارد"
                )

                user_cache[event.sender_id] = {
                    "name": (
                        getattr(user, "first_name", None)
                        or str(event.sender_id)
                    ),
                    "id": event.sender_id,
                    "username": username
                }

            except Exception:
                user_cache[event.sender_id] = {
                    "name": str(event.sender_id),
                    "id": event.sender_id,
                    "username": "ندارد"
                }

    except Exception:
        pass


# =========================================================
# 🗑 پیام حذف شده
# =========================================================

@client.on(events.MessageDeleted)
async def on_delete(event):
    try:
        if not is_group_allowed(event.chat_id):
            return

        if not event.deleted_id or not event.chat_id:
            return

        deleted_msg = None

        try:
            deleted_msg = await client.get_messages(
                event.chat_id,
                ids=event.deleted_id
            )
        except Exception:
            pass

        if not deleted_msg:
            return

        me = await client.get_me()

        if deleted_msg.sender_id == me.id:
            return

        sender_id = deleted_msg.sender_id

        if sender_id in user_cache:
            info = user_cache[sender_id]

        else:
            try:
                user = await client.get_entity(sender_id)

                username = (
                    f"@{user.username}"
                    if getattr(user, "username", None)
                    else "ندارد"
                )

                info = {
                    "name": (
                        getattr(user, "first_name", None)
                        or str(sender_id)
                    ),
                    "id": sender_id,
                    "username": username
                }

                user_cache[sender_id] = info

            except Exception:
                info = {
                    "name": str(sender_id),
                    "id": sender_id,
                    "username": "ندارد"
                }

        reply_text = texts["delete_reply"].format(
            user_id=info["id"],
            user_name=info["name"],
            username=info["username"],
            msg_id=deleted_msg.id,
            text=(
                deleted_msg.text
                or "پیام بدون متن"
            )
        )

        await client.send_message(
            event.chat_id,
            reply_text,
            reply_to=event.deleted_id
        )

        await client.send_message(
            "me",
            f"🗑 حذف در گروه {event.chat_id}\n\n"
            f"{reply_text}"
        )

    except Exception as e:
        print(f"❌ on_delete error: {e}")


# =========================================================
# 📝 پیام ویرایش شده
# =========================================================

@client.on(events.MessageEdited)
async def on_edit(event):
    try:
        if not is_group_allowed(event.chat_id):
            return

        me = await client.get_me()

        if event.sender_id == me.id:
            return

        sender_id = event.sender_id

        if sender_id in user_cache:
            info = user_cache[sender_id]

        else:
            try:
                user = await client.get_entity(sender_id)

                username = (
                    f"@{user.username}"
                    if getattr(user, "username", None)
                    else "ندارد"
                )

                info = {
                    "name": (
                        getattr(user, "first_name", None)
                        or str(sender_id)
                    ),
                    "id": sender_id,
                    "username": username
                }

                user_cache[sender_id] = info

            except Exception:
                info = {
                    "name": str(sender_id),
                    "id": sender_id,
                    "username": "ندارد"
                }

        reply_text = texts["edit_reply"].format(
            user_id=info["id"],
            user_name=info["name"],
            username=info["username"],
            msg_id=event.id,
            text=(
                event.message.text
                or "پیام بدون متن"
            )
        )

        await client.send_message(
            event.chat_id,
            reply_text,
            reply_to=event.id
        )

        await client.send_message(
            "me",
            f"📝 ویرایش در گروه {event.chat_id}\n\n"
            f"{reply_text}"
        )

    except Exception as e:
        print(f"❌ on_edit error: {e}")


# =========================================================
# 🧩 مدیریت لیست‌ها
# =========================================================

async def get_replied_target(event):
    if not event.message.reply_to_msg_id:
        await event.reply(
            "↩️ روی پیام شخص ریپلای کن."
        )
        return None

    try:
        target_msg = await client.get_messages(
            event.chat_id,
            ids=event.message.reply_to_msg_id
        )

        if not target_msg or not target_msg.sender_id:
            await event.reply("❌ کاربر پیدا نشد.")
            return None

        return target_msg

    except Exception as e:
        print(f"❌ Target Error: {e}")
        await event.reply("❌ کاربر پیدا نشد.")
        return None


async def add_list_user(event, slot, kind, me):
    target_msg = await get_replied_target(event)

    if target_msg is None:
        return

    if target_msg.sender_id == me.id:
        await event.reply(
            "❌ خودت رو نمی‌تونی اضافه کنی."
        )
        return

    target_id = str(target_msg.sender_id)

    if kind == "friend":
        users = friend_users[slot]
        filename = FRIEND_FILES[slot]
        title = "دوست"
        emoji = "💚"

    elif kind == "antigirl":
        users = antigirl_users[slot]
        filename = ANTIGIRL_FILES[slot]
        title = "ضد دختر"
        emoji = "👩"

    else:
        users = enemy_users[slot]
        filename = ENEMY_FILES[slot]
        title = "بدخواه"
        emoji = "😈"

    if target_id in users:
        await event.reply(
            f"⚠️ این کاربر قبلاً در لیست {title} نسخه {slot} است."
        )
        return

    users[target_id] = {
        "chat_id": event.chat_id,
        "added_at": datetime.now().isoformat()
    }

    if kind == "friend":
        friend_indexes[slot][target_id] = 0
    elif kind == "antigirl":
        antigirl_indexes[slot][target_id] = 0
    else:
        enemy_indexes[slot][target_id] = 0

    save_json_file(filename, users)

    await event.reply(
        f"{emoji} به لیست {title} نسخه {slot} اضافه شد"
    )


async def remove_list_user(event, slot, kind):
    target_msg = await get_replied_target(event)

    if target_msg is None:
        return

    target_id = str(target_msg.sender_id)

    if kind == "friend":
        users = friend_users[slot]
        filename = FRIEND_FILES[slot]
        indexes = friend_indexes[slot]
        title = "دوست"
        emoji = "💚"

    elif kind == "antigirl":
        users = antigirl_users[slot]
        filename = ANTIGIRL_FILES[slot]
        indexes = antigirl_indexes[slot]
        title = "ضد دختر"
        emoji = "👩"

    else:
        users = enemy_users[slot]
        filename = ENEMY_FILES[slot]
        indexes = enemy_indexes[slot]
        title = "بدخواه"
        emoji = "😈"

    if target_id not in users:
        await event.reply(
            f"⚠️ این کاربر در لیست {title} نسخه {slot} نیست."
        )
        return

    del users[target_id]
    indexes.pop(target_id, None)

    save_json_file(filename, users)

    await event.reply(
        f"{emoji} از لیست {title} نسخه {slot} حذف شد"
    )


# =========================================================
# 🎛 Handler اصلی
# =========================================================

@client.on(events.NewMessage)
async def handler(event):
    global ALLOWED_GROUPS
    global saved_messages

    chat_id = event.chat_id
    text = event.message.text or ""

    try:
        me = await client.get_me()
    except Exception:
        me = None

    # -----------------------------------------------------
    # 😈 Enemy — هر سه نسخه مستقل
    # -----------------------------------------------------

    if event.sender_id:
        for slot in SLOT_IDS:
            if str(event.sender_id) in enemy_users[slot]:
                try:
                    await event.reply(
                        get_enemy_reply(
                            slot,
                            event.sender_id
                        )
                    )
                except Exception as e:
                    print(
                        f"❌ Enemy {slot} Error: {e}"
                    )
                return

    # -----------------------------------------------------
    # 👩 AntiGirl — هر سه نسخه مستقل
    # -----------------------------------------------------

    if event.sender_id:
        for slot in SLOT_IDS:
            if str(event.sender_id) in antigirl_users[slot]:
                try:
                    await event.reply(
                        get_antigirl_reply(
                            slot,
                            event.sender_id
                        )
                    )
                except Exception as e:
                    print(
                        f"❌ AntiGirl {slot} Error: {e}"
                    )
                return

    # -----------------------------------------------------
    # 💚 Friend — هر سه نسخه مستقل
    # -----------------------------------------------------

    if event.sender_id:
        for slot in SLOT_IDS:
            if str(event.sender_id) in friend_users[slot]:
                try:
                    await event.reply(
                        get_friend_reply(
                            slot,
                            event.sender_id
                        )
                    )
                except Exception as e:
                    print(
                        f"❌ Friend {slot} Error: {e}"
                    )
                return

    # -----------------------------------------------------
    # 🔐 فقط صاحب اکانت
    # -----------------------------------------------------

    if me and event.sender_id != me.id:
        return

    print(f"📩 {text}")

    # =====================================================
    # 💚 FRIEND 1/2/3
    # =====================================================

    for slot in SLOT_IDS:

        if text == f"/friend{slot}":
            await add_list_user(
                event,
                slot,
                "friend",
                me
            )
            return

        if text == f"/friend{slot} remove":
            await remove_list_user(
                event,
                slot,
                "friend"
            )
            return

    # =====================================================
    # 👩 ANTIGIRL 1/2/3
    # =====================================================

    for slot in SLOT_IDS:

        if text == f"/antigirl{slot}":
            await add_list_user(
                event,
                slot,
                "antigirl",
                me
            )
            return

        if text == f"/antigirl{slot} remove":
            await remove_list_user(
                event,
                slot,
                "antigirl"
            )
            return

    # =====================================================
    # 😈 ENEMY 1/2/3
    # =====================================================

    for slot in SLOT_IDS:

        if text == f"/enemy{slot}":
            await add_list_user(
                event,
                slot,
                "enemy",
                me
            )
            return

        if text == f"/enemy{slot} remove":
            await remove_list_user(
                event,
                slot,
                "enemy"
            )
            return

    # =====================================================
    # 📖 HELP
    # =====================================================

    # =====================================================
    # 📖 HELP
    # =====================================================

    if text == "/help":
        help_text = (
            "🔰 راهنما\n"
            "━━━━━━━━━━━━━━\n\n"

            "👥 لیست‌ها\n"
            "💚 /friend1  /friend2  /friend3\n"
            "💚 /friend1 remove\n"
            "💚 /friend2 remove\n"
            "💚 /friend3 remove\n\n"

            "👩 /antigirl1  /antigirl2  /antigirl3\n"
            "👩 /antigirl1 remove\n"
            "👩 /antigirl2 remove\n"
            "👩 /antigirl3 remove\n\n"

            "😈 /enemy1  /enemy2  /enemy3\n"
            "😈 /enemy1 remove\n"
            "😈 /enemy2 remove\n"
            "😈 /enemy3 remove\n\n"

            "📝 متن‌ها\n"
            "• /setspam1  /setspam2  /setspam3\n"
            "• /setreply1  /setreply2  /setreply3\n"
            "• /showtexts\n\n"

            "🚀 اجرا\n"
            "• /start1 تعداد زمان\n"
            "• /start2 تعداد زمان\n"
            "• /start3 تعداد زمان\n\n"

            "💬 ریپلای\n"
            "• /reply1 تعداد زمان\n"
            "• /reply2 تعداد زمان\n"
            "• /reply3 تعداد زمان\n\n"

            "📤 فوروارد\n"
            "• /setfor1  /setfor2  /setfor3\n"
            "• /for1 تعداد زمان\n"
            "• /for2 تعداد زمان\n"
            "• /for3 تعداد زمان\n\n"

            "🛑 توقف\n"
            "• /stop\n"
            "• /stopspam1  /stopspam2  /stopspam3\n"
            "• /stopreply1  /stopreply2  /stopreply3\n"
            "• /stopfor1  /stopfor2  /stopfor3\n\n"

            "🗑 مدیریت\n"
            "• /deletetex1\n"
            "• /deletetex2\n"
            "• /deletetex3\n"
            "• /deletetex1 all\n"
            "• /deletetex2 all\n"
            "• /deletetex3 all\n"
            "• /stats\n\n"

            "⚙️ گروه\n"
            "• /setgroup\n"
            "• /showgroups\n\n"

            "━━━━━━━━━━━━━━\n"
            f"{get_subscription_status()}"
        )

        await event.reply(help_text)
        return
    # =====================================================
    # ⚙️ SET GROUP
    # =====================================================

    if text == "/setgroup":
        group_id = chat_id

        if group_id not in ALLOWED_GROUPS:
            ALLOWED_GROUPS.append(group_id)

            await event.reply(
                "⚙️ گروه به لیست مجاز اضافه شد"
            )
        else:
            await event.reply(
                "⚠️ این گروه قبلاً در لیست مجاز است."
            )

        return

    # =====================================================
    # 📋 SHOW GROUPS
    # =====================================================

    if text == "/showgroups":
        if ALLOWED_GROUPS:
            groups = "\n".join(
                f"• {group_id}"
                for group_id in ALLOWED_GROUPS
            )

            await event.reply(
                "📋 گروه‌های مجاز\n"
                "━━━━━━━━━━━━━━\n"
                f"{groups}"
            )
        else:
            await event.reply(
                "📋 هیچ گروهی تنظیم نشده."
            )

        return

    # =====================================================
    # 📝 SET SPAM 1/2/3
    # =====================================================

    for slot in SLOT_IDS:
        command = f"/setspam{slot}"

        if text.startswith(command):
            parts = text.split(maxsplit=1)

            if len(parts) < 2:
                await event.reply(
                    f"❌ فرمت صحیح:\n"
                    f"{command} متن1 | متن2"
                )
                return

            new_texts = [
                t.strip()
                for t in parts[1].split("|")
                if t.strip()
            ]

            if not new_texts:
                await event.reply(
                    "❌ حداقل یک متن وارد کن."
                )
                return

            save_slot_text(
                "spam",
                slot,
                new_texts
            )

            await event.reply(
                f"📝 اسپم {slot}: "
                f"{len(new_texts)} متن ذخیره شد"
            )
            return

    # =====================================================
    # 💬 SET REPLY 1/2/3
    # =====================================================

    for slot in SLOT_IDS:
        command = f"/setreply{slot}"

        if text.startswith(command):
            parts = text.split(maxsplit=1)

            if len(parts) < 2:
                await event.reply(
                    f"❌ فرمت صحیح:\n"
                    f"{command} متن1 | متن2"
                )
                return

            new_texts = [
                t.strip()
                for t in parts[1].split("|")
                if t.strip()
            ]

            if not new_texts:
                await event.reply(
                    "❌ حداقل یک متن وارد کن."
                )
                return

            save_slot_text(
                "reply",
                slot,
                new_texts
            )

            await event.reply(
                f"💬 ریپلای {slot}: "
                f"{len(new_texts)} متن ذخیره شد"
            )
            return

    # =====================================================
    # 📋 SHOW TEXTS
    # =====================================================

    if text == "/showtexts":
        sections = ["📋 متن‌ها", "━━━━━━━━━━━━━━"]

        for slot in SLOT_IDS:
            spam_list = slot_text("spam", slot)
            reply_list = slot_text("reply", slot)

            spam_texts = (
                "\n".join(
                    f"• {x}" for x in spam_list
                )
                if spam_list
                else "تنظیم نشده"
            )

            reply_texts = (
                "\n".join(
                    f"• {x}" for x in reply_list
                )
                if reply_list
                else "تنظیم نشده"
            )

            sections.extend([
                "",
                f"🚀 اسپم {slot}:",
                spam_texts,
                "",
                f"💬 ریپلای {slot}:",
                reply_texts,
                "",
                "━━━━━━━━━━━━━━"
            ])

        await event.reply("\n".join(sections))
        return

    # =====================================================
    # 📊 STATS
    # =====================================================

    if text == "/stats":
        sections = [
            "📊 آمار",
            "━━━━━━━━━━━━━━"
        ]

        for slot in SLOT_IDS:
            s = stats[slot]

            sections.extend([
                "",
                f"🔹 نسخه {slot}",
                f"🚀 اسپم: {s['spam']}",
                f"💬 ریپلای: {s['reply']}",
                f"📤 فوروارد: {s['forward']}",
                f"📌 مجموع: {s['total']}"
            ])

        await event.reply("\n".join(sections))
        return

    # =====================================================
    # 🗑 DELETE TEXT 1/2/3
    # =====================================================

    for slot in SLOT_IDS:
        command = f"/deletetex{slot}"

        if text == command or text == f"{command} all":
            message_ids = get_sent_messages(
                slot,
                chat_id
            )

            if not message_ids:
                await event.reply(
                    f"❌ نسخه {slot} پیامی برای پاک کردن ندارد."
                )
                return

            all_mode = text == f"{command} all"

            msg = await event.reply(
                f"🗑 نسخه {slot}: "
                f"در حال پاک کردن {len(message_ids)} پیام..."
            )

            deleted_count = 0

            if all_mode:
                chunk_size = 10

                for i in range(
                    0,
                    len(message_ids),
                    chunk_size
                ):
                    chunk = message_ids[
                        i:i + chunk_size
                    ]

                    try:
                        await client.delete_messages(
                            chat_id,
                            chunk
                        )

                        deleted_count += len(chunk)

                    except Exception:
                        for mid in chunk:
                            try:
                                await client.delete_messages(
                                    chat_id,
                                    mid
                                )
                                deleted_count += 1
                            except Exception:
                                pass

            else:
                for mid in message_ids:
                    try:
                        await client.delete_messages(
                            chat_id,
                            mid
                        )
                        deleted_count += 1
                    except Exception:
                        pass

            sent_messages[slot][chat_id] = []
            reset_stats(slot)

            await msg.edit(
                f"🗑 نسخه {slot}: "
                f"{deleted_count} پیام پاک شد"
            )

            return

    # =====================================================
    # 📌 SET FORWARD 1/2/3
    # =====================================================

    for slot in SLOT_IDS:
        if text == f"/setfor{slot}":
            if not event.message.reply_to_msg_id:
                await event.reply(
                    f"❌ روی پیام موردنظر ریپلای کن.\n"
                    f"نسخه: {slot}"
                )
                return

            try:
                msg_id = event.message.reply_to_msg_id

                replied = await client.get_messages(
                    chat_id,
                    ids=msg_id
                )

                if replied:
                    saved_messages[slot] = {
                        "chat_id": chat_id,
                        "msg_id": msg_id
                    }

                    await event.reply(
                        f"📌 پیام برای فوروارد نسخه {slot} ذخیره شد"
                    )

            except Exception as e:
                await event.reply(
                    f"❌ خطا: {e}"
                )

            return

    # =====================================================
    # 💬 REPLY 1/2/3
    # =====================================================

    for slot in SLOT_IDS:
        command = f"/reply{slot}"

        if text.startswith(command):
            if not event.message.reply_to_msg_id:
                await event.reply(
                    "❌ روی پیام موردنظر ریپلای کن."
                )
                return

            reply_texts = slot_text(
                "reply",
                slot
            )

            if not reply_texts:
                await event.reply(
                    f"❌ هنوز متنی برای ریپلای {slot} تنظیم نشده."
                )
                return

            parts = text.split()

            count = 5
            delay = 0.5

            try:
                if len(parts) >= 2:
                    count = int(parts[1])

                if len(parts) >= 3:
                    delay = float(parts[2])

            except Exception:
                await event.reply(
                    f"❌ فرمت:\n"
                    f"{command} تعداد زمان"
                )
                return

            target = event.message.reply_to_msg_id

            reply_configs[slot][chat_id] = {
                "target_msg_id": target,
                "texts": reply_texts,
                "count": count,
                "delay": max(delay, 0.1)
            }

            old_task = reply_tasks[slot].get(chat_id)

            if old_task and not old_task.done():
                old_task.cancel()

            reply_tasks[slot][chat_id] = (
                asyncio.create_task(
                    reply_loop(
                        slot,
                        chat_id
                    )
                )
            )

            await event.reply(
                f"💬 ریپلای {slot} شروع شد\n"
                f"🔢 تعداد: {count}\n"
                f"⏱ فاصله: {delay}"
            )

            return

    # =====================================================
    # 🚀 START SPAM 1/2/3
    # =====================================================

    for slot in SLOT_IDS:
        command = f"/start{slot}"

        if text.startswith(command):
            spam_texts = slot_text(
                "spam",
                slot
            )

            if not spam_texts:
                await event.reply(
                    f"❌ هنوز متن اسپم {slot} تنظیم نشده."
                )
                return

            parts = text.split()

            count = 10
            delay = 0.01

            try:
                if len(parts) >= 2:
                    count = int(parts[1])

                if len(parts) >= 3:
                    delay = float(parts[2])

            except Exception:
                await event.reply(
                    f"❌ فرمت:\n"
                    f"{command} تعداد زمان"
                )
                return

            spam_configs[slot][chat_id] = {
                "texts": spam_texts,
                "count": count,
                "delay": max(delay, 0.01)
            }

            old_task = spam_tasks[slot].get(chat_id)

            if old_task and not old_task.done():
                old_task.cancel()

            spam_tasks[slot][chat_id] = (
                asyncio.create_task(
                    spam_loop(
                        slot,
                        chat_id
                    )
                )
            )

            await event.reply(
                f"🚀 اسپم {slot} شروع شد\n"
                f"🔢 تعداد: {count}\n"
                f"⏱ فاصله: {delay}"
            )

            return

    # =====================================================
    # 📤 FORWARD 1/2/3
    # =====================================================

    for slot in SLOT_IDS:
        command = f"/for{slot}"

        if text.startswith(command):
            saved = saved_messages[slot]

            if saved is None:
                await event.reply(
                    f"❌ اول /setfor{slot} را اجرا کن."
                )
                return

            parts = text.split()

            try:
                count = (
                    int(parts[1])
                    if len(parts) > 1
                    else 5
                )

                delay = (
                    float(parts[2])
                    if len(parts) > 2
                    else 0.01
                )

            except Exception:
                await event.reply(
                    f"❌ فرمت:\n"
                    f"{command} تعداد زمان"
                )
                return

            old_task = forward_tasks[slot].get(chat_id)

            if old_task and not old_task.done():
                old_task.cancel()

            forward_tasks[slot][chat_id] = (
                asyncio.create_task(
                    forward_loop(
                        slot,
                        chat_id,
                        count,
                        delay
                    )
                )
            )

            await event.reply(
                f"📤 فوروارد {slot} شروع شد\n"
                f"🔢 تعداد: {count}\n"
                f"⏱ فاصله: {delay}"
            )

            return

    # =====================================================
    # 🛑 STOP ALL
    # =====================================================

    if text == "/stop":
        stopped = False

        for slot in SLOT_IDS:
            for task_map in (
                spam_tasks[slot],
                forward_tasks[slot],
                reply_tasks[slot]
            ):
                task = task_map.get(chat_id)

                if task and not task.done():
                    task.cancel()
                    stopped = True

        await event.reply(
            "⛔ همه عملیات متوقف شد"
            if stopped
            else
            "⚠️ عملیاتی در حال اجرا نیست"
        )

        return

    # =====================================================
    # 🛑 STOP SPAM 1/2/3
    # =====================================================

    for slot in SLOT_IDS:
        if text == f"/stopspam{slot}":
            task = spam_tasks[slot].get(chat_id)

            if task and not task.done():
                task.cancel()

                await event.reply(
                    f"⛔ اسپم {slot} متوقف شد"
                )
            else:
                await event.reply(
                    f"⚠️ اسپم {slot} در حال اجرا نیست."
                )

            return

    # =====================================================
    # 🛑 STOP REPLY 1/2/3
    # =====================================================

    for slot in SLOT_IDS:
        if text == f"/stopreply{slot}":
            task = reply_tasks[slot].get(chat_id)

            if task and not task.done():
                task.cancel()

                await event.reply(
                    f"⛔ ریپلای {slot} متوقف شد"
                )
            else:
                await event.reply(
                    f"⚠️ ریپلای {slot} در حال اجرا نیست."
                )

            return

    # =====================================================
    # 🛑 STOP FORWARD 1/2/3
    # =====================================================

    for slot in SLOT_IDS:
        if text == f"/stopfor{slot}":
            task = forward_tasks[slot].get(chat_id)

            if task and not task.done():
                task.cancel()

                await event.reply(
                    f"⛔ فوروارد {slot} متوقف شد"
                )
            else:
                await event.reply(
                    f"⚠️ فوروارد {slot} در حال اجرا نیست."
                )

            return


# =========================================================
# 🚀 SPAM LOOP
# =========================================================

async def spam_loop(slot, chat_id):
    config = spam_configs[slot].get(chat_id)

    if not config:
        return

    count = config["count"]
    texts_list = config["texts"]
    delay = config["delay"]

    i = 0

    try:
        while True:
            i += 1

            msg = await client.send_message(
                chat_id,
                texts_list[
                    (i - 1) % len(texts_list)
                ]
            )

            add_sent_message(
                slot,
                chat_id,
                msg.id
            )

            stats[slot]["spam"] += 1
            stats[slot]["total"] += 1

            if count > 0 and i >= count:
                break

            await asyncio.sleep(delay)

    except asyncio.CancelledError:
        pass

    except Exception as e:
        print(
            f"❌ Spam {slot} Error: {e}"
        )

    finally:
        spam_tasks[slot].pop(
            chat_id,
            None
        )


# =========================================================
# 💬 REPLY LOOP
# =========================================================

async def reply_loop(slot, chat_id):
    config = reply_configs[slot].get(chat_id)

    if not config:
        return

    count = config["count"]
    target = config["target_msg_id"]
    texts_list = config["texts"]
    delay = config["delay"]

    i = 0

    try:
        while True:
            i += 1

            msg = await client.send_message(
                chat_id,
                texts_list[
                    (i - 1) % len(texts_list)
                ],
                reply_to=target
            )

            add_sent_message(
                slot,
                chat_id,
                msg.id
            )

            stats[slot]["reply"] += 1
            stats[slot]["total"] += 1

            if count > 0 and i >= count:
                break

            await asyncio.sleep(delay)

    except asyncio.CancelledError:
        pass

    except Exception as e:
        print(
            f"❌ Reply {slot} Error: {e}"
        )

    finally:
        reply_tasks[slot].pop(
            chat_id,
            None
        )


# =========================================================
# 📤 FORWARD LOOP
# =========================================================

async def forward_loop(slot, chat_id, count, delay):
    saved = saved_messages[slot]

    if saved is None:
        return

    i = 0

    try:
        while True:
            i += 1

            msg = await client.forward_messages(
                chat_id,
                saved["msg_id"],
                saved["chat_id"]
            )

            if hasattr(msg, "id"):
                add_sent_message(
                    slot,
                    chat_id,
                    msg.id
                )

            stats[slot]["forward"] += 1
            stats[slot]["total"] += 1

            if count > 0 and i >= count:
                break

            await asyncio.sleep(delay)

    except asyncio.CancelledError:
        pass

    except Exception as e:
        print(
            f"❌ Forward {slot} Error: {e}"
        )

    finally:
        forward_tasks[slot].pop(
            chat_id,
            None
        )


# =========================================================
# 🔄 KEEP ALIVE
# =========================================================

async def keep_alive():
    while True:
        try:
            await asyncio.sleep(30)

            await client.send_message(
                PHONE_NUMBER,
                "🔄"
            )

        except Exception:
            await asyncio.sleep(10)


# =========================================================
# ▶️ MAIN
# =========================================================

async def main():
    print("🔐 در حال بررسی اشتراک...")

    if not subscription_is_valid():
        print(
            "⛔ اشتراک این نسخه به پایان رسیده است."
        )
        print(
            "📞 برای تمدید پیام بدید @shmar"
        )
        return

    print(
        f"📋 {get_subscription_status()}"
    )

    print("🚀 در حال اتصال...")

    try:
        await client.start(
            phone=PHONE_NUMBER
        )

        with open(
            SESSION_FILE,
            "w",
            encoding="utf-8"
        ) as f:
            f.write(
                client.session.save()
            )

        me = await client.get_me()

        print(f"👤 ID: {me.id}")
        print(f"📱 Phone: {me.phone}")
        print("✅ ربات آماده است!")
        print("🔥 روشن شد! /help")

    except Exception as e:
        print(
            f"❌ خطا در اتصال: {e}"
        )
        return

    asyncio.create_task(
        keep_alive()
    )

    asyncio.create_task(
        clock_name()
    )

    await client.run_until_disconnected()


# =========================================================
# ▶️ RUN
# =========================================================

if __name__ == "__main__":
    try:
        asyncio.run(main())

    except KeyboardInterrupt:
        print("\n⛔ متوقف شد!")
