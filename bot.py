import os
import time
import yt_dlp
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

# === ספריית האינסטגרם החדשה שלנו ===
from instagrapi import Client

# === תיקון בעיית התמונות ===
import PIL.Image
if not hasattr(PIL.Image, 'ANTIALIAS'):
    PIL.Image.ANTIALIAS = PIL.Image.LANCZOS

from moviepy.editor import VideoFileClip, ImageClip, CompositeVideoClip

# ==========================================
# הגדרות אישיות של הבוט
# ==========================================
TOKEN = "8253310052:AAHXTzZmKeXp6RexB6yjZiaDbsyUTrj-HCc"
LOGO_FILE = "IMG_0964.png" # שם הלוגו שלך
OUTPUT_FOLDER = "סרטונים מוכנים"

# פרטי ההתחברות לאינסטגרם
IG_USERNAME = "YOUR_INSTAGRAM_USERNAME"
IG_PASSWORD = "YOUR_INSTAGRAM_PASSWORD"

os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# ==========================================
# מנוע הווידאו 
# ==========================================
def download_reel(url, output_path):
    ydl_opts = {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'outtmpl': output_path,
        'quiet': True,
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        return True
    except Exception as e:
        print(f"שגיאת הורדה: {e}")
        return False

def add_logo(video_path, logo_path, final_path):
    try:
        video = VideoFileClip(video_path)
        logo = (ImageClip(logo_path)
                .set_duration(video.duration) 
                .resize(height=230) 
                .margin(right=100, top=2, opacity=0) 
                .set_pos(("right", "top"))) 
        
        final_video = CompositeVideoClip([video, logo])
        final_video.write_videofile(final_path, codec="libx264", audio_codec="aac", logger=None) 
        
        video.close()
        logo.close()
        return True
    except Exception as e:
        print(f"שגיאת עריכה: {e}")
        return False

# ==========================================
# לוגיקת הכפתורים והעלאה לאינסטגרם
# ==========================================
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer() 
    
    data = query.data
    
    if data == "cancel":
        await query.edit_message_text(text="🛑 בוטל. הסרטון יישאר רק בתיקייה שלך ולא יעלה לשום מקום.")
        
    elif data.startswith("upload_"):
        timestamp = data.split("_")[1]
        video_to_upload = os.path.join(OUTPUT_FOLDER, f"final_reel_{timestamp}.mp4")
        
        await query.edit_message_text(text="⏳ מתחבר לאינסטגרם ומתחיל העלאה (זה יכול לקחת 1-2 דקות)...")
        
        try:
            # מתחברים לאינסטגרם
            print("מתחיל התחברות לאינסטגרם...")
            cl = Client()
            cl.login(IG_USERNAME, IG_PASSWORD)
            
            # מעלים את הסרטון כ-Reel
            print("מעלה את הסרטון...")
            # אפשר לשנות את ה-caption למה שבא לך שיופיע בתיאור הפוסט
            cl.clip_upload(video_to_upload, caption="סרטון חדש עלה אוטומטית! 🚀") 
            
            await query.edit_message_text(text="✅ בום! ההעלאה לאינסטגרם הושלמה בהצלחה! הסרטון באוויר.")
            print("העלאה הסתיימה בהצלחה.")
            
        except Exception as e:
            print(f"שגיאה בהעלאה: {e}")
            await query.edit_message_text(text=f"❌ שגיאה בהעלאה לאינסטגרם. בדוק את הטרמינל לפירוט השגיאה.")

# ==========================================
# לוגיקת הטלגרם 
# ==========================================
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("אהלן! תשלח לי קישור ל-Reel ואני אדאג לכל השאר. 🎬")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text
    
    if "http" not in url:
        await update.message.reply_text("זה לא נראה כמו קישור... תנסה שוב.")
        return

    status_msg = await update.message.reply_text("⏳ קיבלתי! מתחיל להוריד את הסרטון...")
    
    timestamp = int(time.time())
    temp_video = f"raw_reel_{timestamp}.mp4"
    final_video = os.path.join(OUTPUT_FOLDER, f"final_reel_{timestamp}.mp4")

    if download_reel(url, temp_video):
        await status_msg.edit_text("✅ ההורדה הסתיימה. מדביק את הלוגו...")
        
        if add_logo(temp_video, LOGO_FILE, final_video):
            await status_msg.edit_text("✅ הסרטון מוכן! שולח לך תצוגה מקדימה...")
            
            with open(final_video, 'rb') as video_file:
                await update.message.reply_video(video=video_file, caption="הנה הסרטון המוכן שלך! 🚀")
            
            # הוספת הכפתורים לאישור ההעלאה
            keyboard = [
                [
                    InlineKeyboardButton("כן, תעלה לאינסטגרם! 🚀", callback_data=f"upload_{timestamp}"),
                    InlineKeyboardButton("לא, תשאיר פה 🛑", callback_data="cancel")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text("איך יצא? להעלות את זה עכשיו לאינסטגרם?", reply_markup=reply_markup)
            
            if os.path.exists(temp_video):
                os.remove(temp_video)
                
        else:
            await status_msg.edit_text("❌ שגיאה בשלב העריכה.")
    else:
        await status_msg.edit_text("❌ שגיאה בהורדה.")

def main():
    print("הבוט באוויר וממתין להודעות...")
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(button_callback))

    app.run_polling()

if __name__ == "__main__":
    main()
