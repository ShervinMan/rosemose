import html
from typing import Optional, List

import telegram.ext as tg
from telegram import Message, Chat, Update, Bot, ParseMode, User, MessageEntity
from telegram import TelegramError
from telegram.error import BadRequest
from telegram.ext import CommandHandler, MessageHandler, Filters
from telegram.ext.dispatcher import run_async
from telegram.utils.helpers import mention_html

import tg_bot.modules.sql.locks_sql as sql
from tg_bot import dispatcher, SUDO_USERS, LOGGER
from tg_bot.modules.disable import DisableAbleCommandHandler
from tg_bot.modules.helper_funcs.chat_status import can_delete, is_user_admin, user_not_admin, user_admin, \
    bot_can_delete, is_bot_admin
from tg_bot.modules.helper_funcs.filters import CustomFilters
from tg_bot.modules.log_channel import loggable
from tg_bot.modules.sql import users_sql

LOCK_TYPES = {'استیکر': Filters.sticker,
              'موزیک': Filters.audio,
              'ویس': Filters.voice,
              'اسناد': Filters.document,
              'ویدیو': Filters.video,
              'مخاطب': Filters.contact,
              'عکس': Filters.photo,
              'گیف': Filters.document & CustomFilters.mime_type("video/mp4"),
              'لینک': Filters.entity(MessageEntity.URL) | Filters.caption_entity(MessageEntity.URL),
              'ربات': Filters.status_update.new_chat_members,
              'فوروارد': Filters.forwarded,
              'بازی': Filters.game,
              'لوکیشن': Filters.location,
              '🎭': Filters.sticker,
              '🎧': Filters.audio,
              '🗣': Filters.voice,
              '📑': Filters.document,
              '📹': Filters.video,
              '☎️': Filters.contact,
              '📷': Filters.photo,
              '🎞': Filters.document & CustomFilters.mime_type("video/mp4"),
              '🌐': Filters.entity(MessageEntity.URL) | Filters.caption_entity(MessageEntity.URL),
              '🤖': Filters.status_update.new_chat_members,
              '⏩': Filters.forwarded,
              '🎮': Filters.game,
              '📍': Filters.location,
             }

GIF = Filters.document & CustomFilters.mime_type("video/mp4")
OTHER = Filters.game | Filters.sticker | GIF
MEDIA = Filters.audio | Filters.document | Filters.video | Filters.voice | Filters.photo
MESSAGES = Filters.text | Filters.contact | Filters.location | Filters.venue | Filters.command | MEDIA | OTHER
PREVIEWS = Filters.entity("url")

RESTRICTION_TYPES = {'پیام': MESSAGES,
                     'رسانه': MEDIA,
                     'دیگر': OTHER,
                     'گپ': Filters.all,
                     '✉️': MESSAGES,
                     '📺': MEDIA,
                     '⛓': OTHER,
                     '💬': Filters.all}
PERM_GROUP = 1
REST_GROUP = 2


class CustomCommandHandler(tg.CommandHandler):
    def __init__(self, command, callback, **kwargs):
        super().__init__(command, callback, **kwargs)

    def check_update(self, update):
        return super().check_update(update) and not (
                sql.is_restr_locked(update.effective_chat.id, 'messages') and not is_user_admin(update.effective_chat,
                                                                                                update.effective_user.id))


tg.CommandHandler = CustomCommandHandler


# NOT ASYNC
def restr_members(bot, chat_id, members, messages=False, media=False, other=False, previews=False):
    for mem in members:
        if mem.user in SUDO_USERS:
            pass
        try:
            bot.restrict_chat_member(chat_id, mem.user,
                                     can_send_messages=messages,
                                     can_send_media_messages=media,
                                     can_send_other_messages=other,
                                     can_add_web_page_previews=previews)
        except TelegramError:
            pass


# NOT ASYNC
def unrestr_members(bot, chat_id, members, messages=True, media=True, other=True, previews=True):
    for mem in members:
        try:
            bot.restrict_chat_member(chat_id, mem.user,
                                     can_send_messages=messages,
                                     can_send_media_messages=media,
                                     can_send_other_messages=other,
                                     can_add_web_page_previews=previews)
        except TelegramError:
            pass


@run_async
def locktypes(bot: Bot, update: Update):
    update.effective_message.reply_text("\n ★ ".join(["لیست قفلها🔒 "] + list(LOCK_TYPES) + list(RESTRICTION_TYPES)))


@user_admin
@bot_can_delete
@loggable
def lock(bot: Bot, update: Update, args: List[str]) -> str:
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    message = update.effective_message  # type: Optional[Message]
    if can_delete(chat, bot.id):
        if len(args) >= 1:
            if args[0] in LOCK_TYPES:
                sql.update_lock(chat.id, args[0], locked=True)
                message.reply_text("`{}` برای همه به جز ادمین ها قفل شد".format(args[0]))

                return "<b>{}:</b>" \
                       "\n#LOCK" \
                       "\n<b>Admin:</b> {}" \
                       "\nLocked <code>{}</code>.".format(html.escape(chat.title),
                                                          mention_html(user.id, user.first_name), args[0])

            elif args[0] in RESTRICTION_TYPES:
                sql.update_restriction(chat.id, args[0], locked=True)
                if args[0] == "previews":
                    members = users_sql.get_chat_members(str(chat.id))
                    restr_members(bot, chat.id, members, messages=True, media=True, other=True)

                message.reply_text("{} برای همه به جز ادمین ها قفل شد".format(args[0]))
                return "<b>{}:</b>" \
                       "\n#LOCK" \
                       "\n<b>Admin:</b> {}" \
                       "\nLocked <code>{}</code>.".format(html.escape(chat.title),
                                                          mention_html(user.id, user.first_name), args[0])

            else:
                message.reply_text("چی رو میخوای قفل کنی؟🤔\nاز `.قفلیست` پیداش کن")

    else:
        message.reply_text("یا مدیر نیستم یا اجازه حذف ندارم")

    return ""


@run_async
@user_admin
@loggable
def unlock(bot: Bot, update: Update, args: List[str]) -> str:
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    message = update.effective_message  # type: Optional[Message]
    if is_user_admin(chat, message.from_user.id):
        if len(args) >= 1:
            if args[0] in LOCK_TYPES:
                sql.update_lock(chat.id, args[0], locked=False)
                message.reply_text(" قفل `{}` برای همه باز شد".format(args[0]))
                return "<b>{}:</b>" \
                       "\n#UNLOCK" \
                       "\n<b>Admin:</b> {}" \
                       "\nUnlocked <code>{}</code>.".format(html.escape(chat.title),
                                                            mention_html(user.id, user.first_name), args[0])

            elif args[0] in RESTRICTION_TYPES:
                sql.update_restriction(chat.id, args[0], locked=False)
                """
                members = users_sql.get_chat_members(chat.id)
                if args[0] == "messages":
                    unrestr_members(bot, chat.id, members, media=False, other=False, previews=False)

                elif args[0] == "media":
                    unrestr_members(bot, chat.id, members, other=False, previews=False)

                elif args[0] == "other":
                    unrestr_members(bot, chat.id, members, previews=False)

                elif args[0] == "previews":
                    unrestr_members(bot, chat.id, members)

                elif args[0] == "all":
                    unrestr_members(bot, chat.id, members, True, True, True, True)
                """
                message.reply_text(" {} برای همه باز شد".format(args[0]))

                return "<b>{}:</b>" \
                       "\n#UNLOCK" \
                       "\n<b>Admin:</b> {}" \
                       "\nUnlocked <code>{}</code>.".format(html.escape(chat.title),
                                                            mention_html(user.id, user.first_name), args[0])
            else:
                message.reply_text("چه قفلی رو میخوای باز کنی؟🤔\n از `.قفلیست` پیداش کن")

        else:
            bot.sendMessage(chat.id, "چه قفلی رو میخوای باز کنی؟🤔")

    return ""


@run_async
@user_not_admin
def del_lockables(bot: Bot, update: Update):
    chat = update.effective_chat  # type: Optional[Chat]
    message = update.effective_message  # type: Optional[Message]

    for lockable, filter in LOCK_TYPES.items():
        if filter(message) and sql.is_locked(chat.id, lockable) and can_delete(chat, bot.id):
            if lockable == "bots":
                new_members = update.effective_message.new_chat_members
                for new_mem in new_members:
                    if new_mem.is_bot:
                        if not is_bot_admin(chat, bot.id):
                            message.reply_text("بنظر یک ربات اینجاس و به منم گفته شده از ورودشون جلوگیری کنم"
                                               "ولی من ادمین نیستم🤦")
                            return

                        chat.kick_member(new_mem.id)
                        message.reply_text("فقط ادمین ها مجاز به اضافه کردن ربات در این گپ هستن،خدافظی👋")
            else:
                try:
                    message.delete()
                except BadRequest as excp:
                    if excp.message == "پیامی برای حذف پیدا نشد":
                        pass
                    else:
                        LOGGER.exception("ERROR in lockables")

            break


@run_async
@user_not_admin
def rest_handler(bot: Bot, update: Update):
    msg = update.effective_message  # type: Optional[Message]
    chat = update.effective_chat  # type: Optional[Chat]
    for restriction, filter in RESTRICTION_TYPES.items():
        if filter(msg) and sql.is_restr_locked(chat.id, restriction) and can_delete(chat, bot.id):
            try:
                msg.delete()
            except BadRequest as excp:
                if excp.message == "پیامی برای حذف پیدا نشد":
                    pass
                else:
                    LOGGER.exception("ERROR in restrictions")
            break


def build_lock_message(chat_id):
    locks = sql.get_locks(chat_id)
    restr = sql.get_restr(chat_id)
    if not (locks or restr):
        res = "هیچ قفلی در حال حاضر فعال نیست"
    else:
        res = "وضعیت قفلهای این گروه"
        if locks:
            res += "\n ➊ 🎭استیکر = `{}`" \
                   "\n ➋ 🎧موزیک = `{}`" \
                   "\n ➌ 🗣ویس = `{}`" \
                   "\n ➍ 📑اسناد = `{}`" \
                   "\n ➎ 📹ویدیو = `{}`" \
                   "\n ➏ ☎️مخاطب = `{}`" \
                   "\n ➐ 📷عکس = `{}`" \
                   "\n ➑ 🎞گیف = `{}`" \
                   "\n ➒ 🌐لینک = `{}`" \
                   "\n ➓ 🤖ربات = `{}`" \
                   "\n ⓫ ⏩فوروارد = `{}`" \
                   "\n ⓬ 🎮بازی = `{}`" \
                   "\n ⓭ 📍لوکیشن = `{}`".format(locks.sticker, locks.audio, locks.voice, locks.document,
                                                 locks.video, locks.contact, locks.photo, locks.gif, locks.url,
                                                 locks.bots, locks.forward, locks.game, locks.location)
        if restr:
            res += "\n ⓮ ✉️پیام = `{}`" \
                   "\n ⓯ 📺رسانه = `{}`" \
                   "\n ⓰ ⛓دیگر = `{}`" \
                   "\n ⓱ 💬گپ = `{}`".format(restr.messages, restr.media, restr.other, restr.preview,
                                            all([restr.messages, restr.media, restr.other, restr.preview]))
    return res


@run_async
@user_admin
def list_locks(bot: Bot, update: Update):
    chat = update.effective_chat  # type: Optional[Chat]

    res = build_lock_message(chat.id)

    update.effective_message.reply_text(res, parse_mode=ParseMode.MARKDOWN)


def __migrate__(old_chat_id, new_chat_id):
    sql.migrate_chat(old_chat_id, new_chat_id)


def __chat_settings__(chat_id, user_id):
    return build_lock_message(chat_id)


__help__ = """
✵ `.قفلیست` یا `.🔏`
اسامی قفلها

✵ `.قفل` یا `.🔒`
با ترکیب یکی از اسامی قفلها برای قفل کردن استفاده میشه

✵ `.بازکردن` یا `.🔓`
با ترکیب یکی از اسامی قفلها برای باز کردن استفاده میشه

✵ `.قفلها` یا `.🔐`
وضعیت کلیه ی قفل های فعال و غیر فعاله گپ
"""

__mod_name__ = "قفل"

LOCKTYPES_HANDLER = DisableAbleCommandHandler(["🔏", "قفلیست"], locktypes)
LOCK_HANDLER = CommandHandler(["🔒", "قفل"], lock, pass_args=True, filters=Filters.group)
UNLOCK_HANDLER = CommandHandler(["🔓", "بازکردن"], unlock, pass_args=True, filters=Filters.group)
LOCKED_HANDLER = CommandHandler(["🔐", "قفلها"], list_locks, filters=Filters.group)

dispatcher.add_handler(LOCK_HANDLER)
dispatcher.add_handler(UNLOCK_HANDLER)
dispatcher.add_handler(LOCKTYPES_HANDLER)
dispatcher.add_handler(LOCKED_HANDLER)

dispatcher.add_handler(MessageHandler(Filters.all & Filters.group, del_lockables), PERM_GROUP)
dispatcher.add_handler(MessageHandler(Filters.all & Filters.group, rest_handler), REST_GROUP)
