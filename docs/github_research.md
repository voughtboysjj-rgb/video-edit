# تحقیق محدود فنی — 2026-10-22
این سند بررسی جامع همهٔ منابع پرامپت نیست؛ وضعیت بررسی‌نشده عمداً پنهان نمی‌شود.

## بررسی‌شده و استفاده‌شده
- FFmpeg/FFprobe: https://ffmpeg.org/ffmpeg-filters.html — فهرست رسمی فیلترها مرور شد؛ نسخهٔ اجرایی محلی 7.1.5. select/scene، showinfo، scale، volumedetect و encode/decode واقعاً اجرا شدند. CPU-only. نسخه و build در گزارش خروجی موجود است. مجوز نهایی به build و گزینه‌ها بستگی دارد؛ بررسی کامل حقوق توزیع binary انجام نشده. Python wrapper نداریم.
- Pillow: https://pillow.readthedocs.io/en/stable/ — صفحهٔ رسمی باز شد؛ نسخهٔ نصب‌شده و قفل‌شده 12.3.0 (نه ادعای آخرین نسخه). رسم، متن، blur و عملیات ترکیب تصویر روی CPU اجرا شدند. مجوز و وضعیت آسیب‌پذیری‌ها در این تحویل ممیزی کامل نشده‌اند. Python 3.13 محلی آزمایش شده؛ 3.11 هنوز فقط هدف CI است.
- SQLite: کتابخانهٔ استاندارد Python؛ ثبت Job و کنترل رندر تکراری در اجرای واقعی استفاده شدند.

## FreeLLM
https://freellm.sh/#models باز شد و فهرست لینک به Providerها دیده شد. این بررسی، تأیید یک endpoint مشترک یا تست هیچ Provider نیست. اتصال غیرفعال و endpoint برابر null است. هیچ مدل یا کلیدی استفاده نشد.

## منابع ثبت‌شده اما بررسی/ادغام‌نشده
همهٔ موارد زیر در وضعیت not_reviewed / not_tested هستند؛ نسخه، مجوز، امنیت و سازگاری 3.11 آن‌ها تأیید نشده. تصمیم فعلی: خارج از هستهٔ حداقلی تا تحقیق و نیاز واقعی.
- https://github.com/FFmpeg/FFmpeg
- https://ffmpeg.org/documentation.html
- https://github.com/Breakthrough/PySceneDetect
- https://github.com/librosa/librosa
- https://librosa.org/doc/latest/index.html
- https://github.com/kkroening/ffmpeg-python
- https://github.com/Zulko/moviepy
- https://github.com/googleapis/google-api-python-client
- https://github.com/yt-dlp/yt-dlp
- https://github.com/OpenShot/openshot-qt
- https://github.com/Chamanrajragu/purffle-shorts
- https://developers.google.com/youtube/v3
- https://developers.google.com/youtube/analytics

سیاست‌های جاری Shorts و افشای محتوای مصنوعی هنوز مستقلاً بررسی نشده‌اند؛ خروجی محلی به معنی تأیید پذیرش پلتفرم نیست.
