import telegram
from telegram import (
Update,InlineKeyboardMarkup,InlineKeyboardButton
)
from telegram.ext import (
    Updater,
    MessageHandler,
    CallbackContext,
    Filters,
    CallbackDataCache,
    ConversationHandler, CommandHandler,CallbackQueryHandler
)

import sqlite3

TOKEN = '8585672085:AAEz_MYrelrJ1obeLq60ojBOMVKJPwyBooY'
ADMIN_ID = 1371451367

db=sqlite3.connect('movies.db',check_same_thread=False) # tekshirmay qoyaver degan buyruq false bilan
cursor=db.cursor()

cursor.execute('''CREATE TABLE IF NOT EXISTS movies (
code TEXT PRIMARY KEY,
file_id TEXT,
captions TEXT
);
''')

cursor.execute('''CREATE TABLE IF NOT EXISTS channels (
channel TEXT PRIMARY KEY
);
''')

db.commit()#bu ma’lumotlar bazasida (database) qilingan o‘zgarishlarni saqlab qo‘yish (tasdiqlash) uchun ishlatiladigan buyruq.


(MOVIE_CODE,
 MOVIE_FILE,
 MOVIE_CAPTION) = range(3)

def get_channels():
    cursor.execute("SELECT channel FROM channels")
    return [i[0] for i in cursor.fetchall()]

def check_subscription(bot,user_id):
    channels = get_channels()
    if not channels:
        return True

    for channel in channels:
        try:
            member = bot.get_chat_member(user_id,channel)
            if member.status in ['left', 'kicked']:
                return False

        except:
            return False

    return True

def subscription_keyboard():
    keyboard =[]

    for ch in get_channels():
        if ch.startswith('@'):
            url=f"https://t.me/{ch[1:]}"
        else:
            url=ch

        keyboard.append([
            InlineKeyboardButton(f'{ch}',url=url)
        ])

    keyboard.append([
        InlineKeyboardButton('Tekshirish✅',callback_data='check_sub')
    ])
    return InlineKeyboardMarkup(keyboard)


def start(update:Update,context:CallbackContext):
    user_id = update.message.from_user.id

    if not  check_subscription(context.bot,user_id):
        update.message.reply_text("botdan foydalanish uchun kanlallarga obuna bo`ling!",
                                  reply_markup=subscription_keyboard())
        return

    update.message.reply_text("Assalomu alaykum\n"
                              "Kino kodini kiriting: ")


def get_movies(update:Update,context:CallbackContext):
    user_id = update.message.from_user.id

    if not check_subscription(context.bot, user_id):
        update.message.reply_text("botdan foydalanish uchun kanlallarga obuna bo`ling!",
                                  reply_markup=subscription_keyboard())
        return

    code=update.message.text
    cursor.execute("SELECT file_id, captions FROM movies WHERE code=?",(code,))
    result=cursor.fetchone()

    if result:
        file_id,captions=result
        update.message.reply_video(video=file_id,caption=captions)
    else:
        update.message.reply_text("kechirasiz! bu kod bo`yicha kino topilmadi!!!")

def check_subscription_callback(update:Update,context:CallbackContext):
    query = update.callback_query
    user_id = query.from_user.id


    if check_subscription(context.bot,user_id):
        query.message.edit_text(
            "obuna tasdiqlandi✅\n\n"
            "Endi kino kodini kiritishingiz mumkin !"
        )
        return
    else:
        query.answer(
            "Hali kanallarga obuna bolmagansiz",
            show_alert=True
        )


def add_channels(update:Update,context:CallbackContext):
    if update.message.from_user.id != ADMIN_ID:
        return

    if not context.args:
        update.message.reply_text("Misol: /addchannel @kanal ")

    channels = context.args[0]#bu kommandadan keyingi yozilgan so‘zlar ro‘yxati (list).
    cursor.execute("INSERT OR IGNORE INTO channels VALUES (?)",(channels,))
    db.commit()

    update.message.reply_text(f"Kanal qoshildi: {channels}✅")

def delete_channels(update:Update,context:CallbackContext):
    if update.message.from_user.id != ADMIN_ID:
        return

    if not context.args:
        update.message.reply_text("Misol: /delchannel @kanal ")

    channels = context.args[0]#bu kommandadan keyingi yozilgan so‘zlar ro‘yxati (list).
    cursor.execute("DELETE FROM channels WHERE channel=?",(channels,))
    db.commit()

    update.message.reply_text(f"Kanal o`chirildi: {channels}⛔️")

def list_channels(update:Update,context:CallbackContext):
    if update.message.from_user.id != ADMIN_ID:
        return

    channels = get_channels()
    if not channels:
        update.message.reply_text("Kanallar yo'q 🚫 ")

    text="Kanallar ro`yxati\n\n"
    for ch in channels:
        text += f"{ch}\n"

    update.message.reply_text(text)


def admin_start(update:Update,context:CallbackContext):
    if update.message.from_user.id != ADMIN_ID:
        update.message.reply_text("Afsuski siz adminlar ro`yxatida emassiz!!!🚫")
        return ConversationHandler.END

    update.message.reply_text("Iltimos kino kodini kiriting  ✍️: ")
    return MOVIE_CODE


def admin_code(update:Update,context:CallbackContext):
    context.user_data['code'] = update.message.text.strip()
    update.message.reply_text("🎬Endi kino voki vidoeni yuboring")
    return MOVIE_FILE

def admin_file(update:Update,context:CallbackContext):
    if not update.message.video:
        update.message.reply_text("Iltimos faqat video yuboring!!")
        return MOVIE_CODE

    context.user_data['file_id'] = update.message.video.file_id
    update.message.reply_text("Endi video tagidagi matnni yuboring...")
    return MOVIE_CAPTION

def admin_caption(update:Update,context:CallbackContext):
    cursor.execute("""
    INSERT OR REPLACE INTO MOVIES  VALUES (?,?,?)
    """,(
    context.user_data['code'],
    context.user_data['file_id'],
    update.message.text
    ))
    db.commit()

    update.message.reply_text("Kino saqlandi ☑️")
    return ConversationHandler.END

def cancel(update:Update,context:CallbackContext):
    update.message.reply_text("Bekor qilindi🚫")

def main():
    updater=Updater(TOKEN)
    dp=updater.dispatcher

    admin_conv_handler = ConversationHandler(
        entry_points=[CommandHandler('admin', admin_start)],
        states={
            MOVIE_CODE: [MessageHandler(Filters.text & ~Filters.command,admin_code)],
            MOVIE_FILE: [MessageHandler(Filters.video & ~Filters.command,admin_file)],
            MOVIE_CAPTION: [MessageHandler(Filters.text, admin_caption)]
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )

    dp.add_handler(CommandHandler('start', start))
    dp.add_handler(CommandHandler('addchannel', add_channels))
    dp.add_handler(CommandHandler('delchannel', delete_channels))
    dp.add_handler(CommandHandler('channel', list_channels))

    dp.add_handler(admin_conv_handler)
    dp.add_handler(CallbackQueryHandler(check_subscription_callback,pattern="check_sub"))
    dp.add_handler(MessageHandler(Filters.text & ~ Filters.command, get_movies))

    updater.start_polling()
    updater.idle()

print("zor")
if __name__ == '__main__':
    main()



































































