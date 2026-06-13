# بوت حديث يومي لرياض الصالحين على Telegram

هذا المشروع يرسل حديثًا واحدًا يوميًا إلى قناة أو مجموعة Telegram اعتمادًا على ملف `hadiths.json` الموجود في المشروع.
لا يحتاج إلى سيرفر مدفوع؛ يعمل مجانًا عبر GitHub Actions.

## الملفات الأساسية

- `bot.py`: كود Python الذي يقرأ JSON ويرسل الحديث.
- `hadiths.json`: قاعدة الأحاديث، وفيها 1896 حديثًا.
- `requirements.txt`: مكتبات Python المطلوبة.
- `.github/workflows/daily.yml`: جدولة التشغيل اليومي.

## 1) إنشاء بوت Telegram

1. افتح Telegram وابحث عن `@BotFather`.
2. أرسل الأمر `/newbot`.
3. اختر اسمًا للبوت، مثل: `حديث اليوم`.
4. اختر username للبوت، ويجب أن ينتهي بـ `bot`، مثل: `riyad_daily_hadith_bot`.
5. سيعطيك BotFather قيمة اسمها token. لا ترسلها لأحد ولا تضعها داخل الكود.

## 2) تجهيز القناة أو المجموعة

### إن كانت قناة عامة

اجعل للقناة username مثل:

```text
@my_hadith_channel
```

ثم أضف البوت إلى القناة كمسؤول، وأعطه صلاحية نشر الرسائل.
قيمة `TELEGRAM_CHAT_ID` ستكون نفس username القناة، مثل:

```text
@my_hadith_channel
```

### إن كانت مجموعة

أضف البوت إلى المجموعة. الأفضل تحويلها إلى supergroup واستخدام username إن أمكن.

## 3) رفع المشروع إلى GitHub

ارفع كل ملفات المشروع إلى مستودع GitHub جديد. تأكد أن هذه الملفات موجودة في الجذر:

```text
bot.py
hadiths.json
requirements.txt
.github/workflows/daily.yml
```

## 4) إضافة أسرار Telegram في GitHub

من صفحة المستودع:

```text
Settings → Secrets and variables → Actions → New repository secret
```

أضف سرين:

```text
TELEGRAM_BOT_TOKEN = التوكن الذي أعطاك إياه BotFather
TELEGRAM_CHAT_ID = @username_القناة أو رقم chat_id
```

## 5) اختبار التشغيل يدويًا

اذهب إلى:

```text
Actions → Daily Telegram Hadith → Run workflow
```

إذا نجح التشغيل، ستصل رسالة حديث إلى القناة/المجموعة.

## 6) تغيير وقت النشر

افتح الملف:

```text
.github/workflows/daily.yml
```

الإعداد الحالي:

```yaml
schedule:
  - cron: "30 8 * * *"
    timezone: "Europe/Istanbul"
```

هذا يعني النشر يوميًا الساعة 08:30 بتوقيت إسطنبول.
مثال للنشر الساعة 06:15:

```yaml
schedule:
  - cron: "15 6 * * *"
    timezone: "Europe/Istanbul"
```

## 7) تخصيص نص الرسالة

داخل `.github/workflows/daily.yml` يمكنك تغيير:

```yaml
MESSAGE_TITLE: "📚 حديث اليوم"
DEFAULT_SOURCE: "رياض الصالحين"
```

## ملاحظات مهمة

- لا تضع `TELEGRAM_BOT_TOKEN` داخل الملفات العامة.
- إذا كانت القناة خاصة، قد تحتاج إلى معرفة الرقم الداخلي للـ `chat_id` بدل username.
- Telegram يسمح بإرسال الرسائل عبر `sendMessage`، والكود يقسم الرسائل الطويلة تلقائيًا حتى لا تتجاوز الحد المسموح.
- تحقق من حقوق النشر والاستخدام عند النشر العام.
