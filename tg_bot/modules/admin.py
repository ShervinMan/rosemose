import html
from typing import Optional, List

from telegram import Message, Chat, Update, Bot, User
from telegram import ParseMode
from telegram.error import BadRequest
from telegram.ext import CommandHandler, Filters, RegexHandler
from telegram.ext.dispatcher import run_async
from telegram.utils.helpers import escape_markdown, mention_html

from tg_bot import dispatcher
import tg_bot.modules.sql.setlink_sql as sql
from tg_bot.modules.disable import DisableAbleCommandHandler
from tg_bot.modules.helper_funcs.chat_status import bot_admin, can_promote, user_admin, can_pin
from tg_bot.modules.helper_funcs.extraction import extract_user
from tg_bot.modules.helper_funcs.string_handling import markdown_parser
from tg_bot.modules.log_channel import loggable


@run_async
@bot_admin
@can_promote
@user_admin
@loggable
def promote(bot: Bot, update: Update, args: List[str]) -> str:
    chat_id = update.effective_chat.id
    message = update.effective_message  # type: Optional[Message]
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]

    user_id = extract_user(message, args)
    if not user_id:
        message.reply_text("دقت کن،فکر نکنم ایشون ممبر باشه")
        return ""

    user_member = chat.get_member(user_id)
    if user_member.status == 'administrator' or user_member.status == 'creator':
        message.reply_text("خودش از قبل ادمینه😐")
        return ""

    if user_id == bot.id:
        message.reply_text("من نمیتونم خودم رو ادمین کنم😂به یک ادمین رده بالا بگو این کار رو انجام بده")
        return ""

    # set same perms as bot - bot can't assign higher perms than itself!
    bot_member = chat.get_member(bot.id)

    bot.promoteChatMember(chat_id, user_id,
                          can_change_info=bot_member.can_change_info,
                          can_post_messages=bot_member.can_post_messages,
                          can_edit_messages=bot_member.can_edit_messages,
                          can_delete_messages=bot_member.can_delete_messages,
                          # can_invite_users=bot_member.can_invite_users,
                          can_restrict_members=bot_member.can_restrict_members,
                          can_pin_messages=bot_member.can_pin_messages)
                          #can_promote_members=bot_member.can_promote_members

    message.reply_text("⚜️تبریک⚜️\nبا موفقیت به کاربر ویژه ترفیع پیدا کرد♥️\n\n *دسترسی ها:* \n\n ➊مدیریت گروه\n ➋دسترسی به کلیه ی قفل ها\n ➌دسترسی به منوی بن و اخطار و سکوت\n ➍حذف پیام کاربران\n ➎سنجاق کردن پیام")
    return "<b>{}:</b>" \
           "\n#PROMOTED" \
           "\n<b>Admin:</b> {}" \
           "\n<b>User:</b> {}".format(html.escape(chat.title),
                                      mention_html(user.id, user.first_name),
                                      mention_html(user_member.user.id, user_member.user.first_name))


@run_async
@bot_admin
@can_promote
@user_admin
@loggable
def demote(bot: Bot, update: Update, args: List[str]) -> str:
    chat = update.effective_chat  # type: Optional[Chat]
    message = update.effective_message  # type: Optional[Message]
    user = update.effective_user  # type: Optional[User]

    user_id = extract_user(message, args)
    if not user_id:
        message.reply_text("دقت کن،فکر نکنم ایشون ممبر باشه")
        return ""

    user_member = chat.get_member(user_id)
    if user_member.status == 'creator':
        message.reply_text("بابا بیا پایین🤌\nاین مالک گپه توقع چه حرکتی از من داری?😂")
        return ""

    if not user_member.status == 'administrator':
        message.reply_text("ایشون اصلا ادمین نیست که قرار باشه من برکنارش کنم🤌")
        return ""

    if user_id == bot.id:
        message.reply_text("داداش ساقیتو عوض کن🤌توقع داری من خودزنی کنم؟😂")
        return ""

    try:
        bot.promoteChatMember(int(chat.id), int(user_id),
                              can_change_info=False,
                              can_post_messages=False,
                              can_edit_messages=False,
                              can_delete_messages=False,
                              can_invite_users=False,
                              can_restrict_members=False,
                              can_pin_messages=False,
                              can_promote_members=False)
        message.reply_text("هعععی،چرااا؟!💔 ولی خب با موفقیت از لیست ادمین ها حذف شد👍")
        return "<b>{}:</b>" \
               "\n#DEMOTED" \
               "\n<b>Admin:</b> {}" \
               "\n<b>User:</b> {}".format(html.escape(chat.title),
                                          mention_html(user.id, user.first_name),
                                          mention_html(user_member.user.id, user_member.user.first_name))

    except BadRequest:
        message.reply_text("برکناری انجام نشد،ممکنه من ادمین نباشم یا این کاربر توسط من ادمین نشده باشه"
                           "اگر کس دیگه ای ادمینش کرده باشه من نمیتونم برکنارش کنم")
        return ""


@run_async
@bot_admin
@can_pin
@user_admin
@loggable
def pin(bot: Bot, update: Update, args: List[str]) -> str:
    user = update.effective_user  # type: Optional[User]
    chat = update.effective_chat  # type: Optional[Chat]

    is_group = chat.type != "private" and chat.type != "channel"

    prev_message = update.effective_message.reply_to_message

    is_silent = True
    if len(args) >= 1:
        is_silent = not (args[0].lower() == 'نوتیف' or args[0].lower() == 'اعلان' or args[0].lower() == 'violent')

    if prev_message and is_group:
        try:
            bot.pinChatMessage(chat.id, prev_message.message_id, disable_notification=is_silent)
        except BadRequest as excp:
            if excp.message == "Chat_not_modified":
                pass
            else:
                raise
        return "<b>{}:</b>" \
               "\n#PINNED" \
               "\n<b>Admin:</b> {}".format(html.escape(chat.title), mention_html(user.id, user.first_name))

    return ""


@run_async
@bot_admin
@can_pin
@user_admin
@loggable
def unpin(bot: Bot, update: Update) -> str:
    chat = update.effective_chat
    user = update.effective_user  # type: Optional[User]

    try:
        bot.unpinChatMessage(chat.id)
    except BadRequest as excp:
        if excp.message == "Chat_not_modified":
            pass
        else:
            raise

    return "<b>{}:</b>" \
           "\n#UNPINNED" \
           "\n<b>Admin:</b> {}".format(html.escape(chat.title),
                                       mention_html(user.id, user.first_name))

@run_async
@bot_admin
@user_admin
def invite(bot: Bot, update: Update):
    chat = update.effective_chat  # type: Optional[Chat]
    message = update.effective_message #type: Optional[Messages]
    
    if chat.username:
        update.effective_message.reply_text("@{}".format(chat.username))
    elif chat.type == chat.SUPERGROUP or chat.type == chat.CHANNEL:
        bot_member = chat.get_member(bot.id)
        if bot_member.can_invite_users:
            invitelink = bot.exportChatInviteLink(chat.id)
            linktext = "لینک جدید با موفقیت برای *{}:* ساخته شد".format(chat.title)
            link = "`{}`".format(invitelink)
            message.reply_text(linktext, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)
            message.reply_text(link, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)
        else:
            message.reply_text("من به لینک دعوت دسترسی ندارم،مجوزش رو بهم بده")
    else:
        message.reply_text("من فقط میتونم لینک دعوت سوپر گروهها و کانال ها رو بهت بدم")

@run_async
def link_public(bot: Bot, update: Update):
    chat = update.effective_chat  # type: Optional[Chat]
    message = update.effective_message #type: Optional[Messages]
    chat_id = update.effective_chat.id
    invitelink = sql.get_link(chat_id)
    
    if chat.type == chat.SUPERGROUP or chat.type == chat.CHANNEL:
        if invitelink:
            message.reply_text("لینک *{}*:\n`{}`".format(chat.title, invitelink), parse_mode=ParseMode.MARKDOWN)
        else:
            message.reply_text("ادمین های *{}* لینکی رو تنظیم نکردن"
                               " \nلینک رو میتونی با دستور `.ستلینک` ست کنی "
                               "با استفاده از دستور `.لینک` هم دریافتش کنی".format(chat.title), parse_mode=ParseMode.MARKDOWN)
    else:
        message.reply_text("من فقط میتونم لینک سوپر گروهها یا کانال ها رو ذخیره کنم")

@run_async
@user_admin
def set_link(bot: Bot, update: Update):
    chat_id = update.effective_chat.id
    msg = update.effective_message  # type: Optional[Message]
    chat = update.effective_chat  # type: Optional[Chat]
    raw_text = msg.text
    args = raw_text.split(None, 1)  # use python's maxsplit to separate cmd and args
    
    if len(args) == 2:
        links_text = args[1]

        sql.set_link(chat_id, links_text)
        msg.reply_text("لینک برای {} ست شد،دریافت لینک بادستور `.لینک` در دسترسه".format((chat.title)))


@run_async
@user_admin
def clear_link(bot: Bot, update: Update):
    chat_id = update.effective_chat.id
    sql.set_link(chat_id, "")
    update.effective_message.reply_text("لینک با موفقیت حذف شد")


@run_async
def adminlist(bot: Bot, update: Update):
    administrators = update.effective_chat.get_administrators()
    text = "ادمین های *{}*:".format(update.effective_chat.title or "این گپ")
    for admin in administrators:
        user = admin.user
        name = "[{}](tg://user?id={})".format(user.first_name + (user.last_name or ""), user.id)
        if user.username:
            name = escape_markdown("@" + user.username)
        text += "\n ✪ {}".format(name)

    update.effective_message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

def __stats__():
    return "{} این گپ برای لینک ست شده".format(sql.num_chats())

def __chat_settings__(chat_id, user_id):
    return "شما *ادمین* هستی: `{}`".format(
        dispatcher.bot.get_chat_member(chat_id, user_id).status in ("administrator", "creator"))


__help__ = """
__همه ی موارد مربوط به مدیریت گپ مثل ترفیع کاربر،برکناری کاربر،سنجاق پیام و غیره رو میتونی از طریق من راحت انجام بدی__


 *دستورات:*

 ✵ `.مدیرها` یا `.👥`
 لیست مدیرهای گپ

 ✵ `.لینک` یا `.📮`
 دریافت لینگ گپ
 
 ✵ `.پین` یا `.📌`
 پین کردن پیام
 برای نوتیف هم در کنار پین از `اعلان` یا `نوتیف` استفاده کنید

 ✵ `.لغوپین` یا `.🖇`
 حذف کردن پین

 ✵ `.آیدیگپ` یا `.🗯`
 آیدی گپ

 ✵ `.ستلینک` یا `.🔗`
 تنظیم کردن لینک شخصی

 ✵ `.لغولینک` یا `.🗑`
 حذف کردن لینک

 ✵ `.کاربرویژه` یا `.😍` و `.🤝`
 ترفیع کاربر

 ✵ `.برکناری` یا `.😑`
 برکناری ادمین

 ▬▬▬▬▬▬

 ۞ *آموزش ستلینک*
`.ستلینک https://t.me/joinchat/HjksyIKjn6i`

 ۞ *آموزش ترفیع و برکناری*
 ریپلای کردن پیام کاربر و ارسال دستور مورد نظر یا ارسال دستور+یوزرنیم 
 برای مثال:`.🤝 @username`
"""

__mod_name__ = "ادمین"

PIN_HANDLER = CommandHandler(["پین", "📌"], pin, pass_args=True, filters=Filters.group)
UNPIN_HANDLER = CommandHandler(["لغوپین", "🖇"], unpin, filters=Filters.group)
LINK_HANDLER = DisableAbleCommandHandler(["لینک", "📮"], link_public)
SET_LINK_HANDLER = CommandHandler(["ستلینک", "🔗"], set_link, filters=Filters.group)
RESET_LINK_HANDLER = CommandHandler(["لغولینک", "🗑"], clear_link, filters=Filters.group)
HASH_LINK_HANDLER = RegexHandler("#link", link_public)
INVITE_HANDLER = CommandHandler(["آیدیگپ", "🗯"], invite, filters=Filters.group)
PROMOTE_HANDLER = CommandHandler(["کاربرویژه", "🤝", "😍"], promote, pass_args=True, filters=Filters.group)
DEMOTE_HANDLER = CommandHandler(["برکناری", "😑"], demote, pass_args=True, filters=Filters.group)
ADMINLIST_HANDLER = DisableAbleCommandHandler(["مدیرها", "👥"], adminlist, filters=Filters.group)

dispatcher.add_handler(PIN_HANDLER)
dispatcher.add_handler(UNPIN_HANDLER)
dispatcher.add_handler(INVITE_HANDLER)
dispatcher.add_handler(LINK_HANDLER)
dispatcher.add_handler(SET_LINK_HANDLER)
dispatcher.add_handler(RESET_LINK_HANDLER)
dispatcher.add_handler(HASH_LINK_HANDLER)
dispatcher.add_handler(PROMOTE_HANDLER)
dispatcher.add_handler(DEMOTE_HANDLER)
dispatcher.add_handler(ADMINLIST_HANDLER)
