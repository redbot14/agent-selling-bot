import os
import sqlite3
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    CommandHandler,
    CallbackQueryHandler,
    ConversationHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

from database import (
    get_user,
    get_order,
    update_order_status,
    get_stats,
    add_category,
    get_all_categories,
    add_agent,
    get_all_user_ids,
    get_pending_withdrawals,
    update_withdrawal_status,
    update_user_balance,
    delete_agent,
)
from keyboards import (
    get_admin_keyboard,
    get_admin_order_keyboard,
    get_admin_withdraw_keyboard,
    get_back_to_home_keyboard,
)

logger = logging.getLogger(__name__)

DB_NAME = os.environ.get('DB_NAME', 'agentbd.db')

# Conversation states
ADD_CAT_NAME = 10
ADD_CAT_EMOJI = 11
ADD_AGENT_NAME = 20
ADD_AGENT_DESC = 21
ADD_AGENT_PRICE = 22
ADD_AGENT_CAT = 23
ADD_AGENT_URL = 24
BROADCAST_TEXT = 30
DELIVER_URL = 40
DELETE_AGENT_ID = 50


def is_admin(user_id: str) -> bool:
    admin_id = os.environ.get('ADMIN_TELEGRAM_ID', '')
    return str(user_id) == str(admin_id)


def get_pending_orders_from_db() -> list:
    try:
        conn = sqlite3.connect(DB_NAME)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM orders WHERE status='pending' ORDER BY created_at DESC"
        )
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
    except Exception as e:
        logger.error(f"Error fetching pending orders: {e}")
        return []


# ─── FEATURE 1: /admin command ────────────────────────────────────────────────

async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not is_admin(str(user.id)):
        await update.message.reply_text("⛔ Access denied.")
        return

    print(f"[ADMIN] Admin {user.id} opened admin panel.")
    try:
        await update.message.reply_text(
            "🔐 ADMIN PANEL\n━━━━━━━━━━\nWelcome, Admin! Choose an action:",
            reply_markup=get_admin_keyboard()
        )
    except Exception as e:
        logger.error(f"Error in admin_command: {e}")


# ─── FEATURE 2: admin_orders callback ────────────────────────────────────────

async def admin_orders_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not is_admin(str(query.from_user.id)):
        await query.answer("⛔ Access denied.", show_alert=True)
        return
    await query.answer()

    try:
        pending = get_pending_orders_from_db()
        if not pending:
            await query.edit_message_text(
                "No pending orders.",
                reply_markup=get_admin_keyboard()
            )
            return

        text = "📦 PENDING ORDERS\n━━━━━━━━━━\n"
        buttons = []
        for order in pending:
            oid = order.get('order_id', '')
            agent_name = order.get('agent_name', 'N/A')
            amount = float(order.get('amount', 0))
            user_id = order.get('user_id', 'N/A')
            label = f"📦 #{oid[:8]} | {agent_name[:15]} | ${amount:.2f} | {user_id}"
            buttons.append([InlineKeyboardButton(label, callback_data=f"admin_ord_{oid}")])

        buttons.append([InlineKeyboardButton("🔙 Back", callback_data="admin_back")])
        keyboard = InlineKeyboardMarkup(buttons)
        await query.edit_message_text(text + f"Found {len(pending)} pending order(s):", reply_markup=keyboard)
        print(f"[ADMIN] Admin viewed pending orders ({len(pending)}).")
    except Exception as e:
        logger.error(f"Error in admin_orders_callback: {e}")
        await query.edit_message_text("⚠️ Could not load orders.")


# ─── FEATURE 3: admin_ord_{order_id} callback ────────────────────────────────

async def admin_order_detail_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not is_admin(str(query.from_user.id)):
        await query.answer("⛔ Access denied.", show_alert=True)
        return
    await query.answer()

    try:
        order_id = query.data.split('_', 2)[2]
        order = get_order(order_id)

        if not order:
            await query.edit_message_text("⚠️ Order not found.")
            return

        status = order.get('status', 'pending')
        text = (
            f"📦 ORDER DETAILS\n"
            f"━━━━━━━━━━\n"
            f"🆔 Order: #{order['order_id']}\n"
            f"👤 User ID: {order['user_id']}\n"
            f"🤖 Agent: {order['agent_name']}\n"
            f"💵 Amount: ${float(order['amount']):.2f}\n"
            f"💳 Payment: {order['payment_method']}\n"
            f"🔑 Txn ID: {order.get('txn_id', 'N/A')}\n"
            f"📊 Status: {status.upper()}\n"
            f"📅 Date: {str(order.get('created_at', ''))[:19]}"
        )
        await query.edit_message_text(text, reply_markup=get_admin_order_keyboard(order_id))
        print(f"[ADMIN] Admin viewing order {order_id}.")
    except Exception as e:
        logger.error(f"Error in admin_order_detail_callback: {e}")
        await query.edit_message_text("⚠️ Could not load order details.")


# ─── FEATURE 4: aord_verified_{order_id} callback ────────────────────────────

async def aord_verified_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not is_admin(str(query.from_user.id)):
        await query.answer("⛔ Access denied.", show_alert=True)
        return
    await query.answer("✅ Order marked as verified")

    try:
        order_id = query.data.split('_', 2)[2]
        order = get_order(order_id)
        if not order:
            await query.edit_message_text("⚠️ Order not found.")
            return

        update_order_status(order_id, 'verified')
        print(f"[ADMIN] Order {order_id} marked as verified.")

        try:
            await context.bot.send_message(
                chat_id=int(order['user_id']),
                text=(
                    f"✅ Your order #{order_id} has been VERIFIED!\n"
                    f"We're setting it up now..."
                )
            )
        except Exception as e:
            logger.error(f"Error notifying user for verified order: {e}")

        await query.edit_message_text(
            f"✅ Order #{order_id} marked as VERIFIED.",
            reply_markup=get_admin_order_keyboard(order_id)
        )
    except Exception as e:
        logger.error(f"Error in aord_verified_callback: {e}")
        await query.edit_message_text("⚠️ Could not update order status.")


# ─── FEATURE 5: aord_setup_{order_id} callback ───────────────────────────────

async def aord_setup_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not is_admin(str(query.from_user.id)):
        await query.answer("⛔ Access denied.", show_alert=True)
        return
    await query.answer("⚙️ Order marked as setup")

    try:
        order_id = query.data.split('_', 2)[2]
        order = get_order(order_id)
        if not order:
            await query.edit_message_text("⚠️ Order not found.")
            return

        update_order_status(order_id, 'setup')
        print(f"[ADMIN] Order {order_id} marked as setup.")

        try:
            await context.bot.send_message(
                chat_id=int(order['user_id']),
                text=f"⚙️ Your order #{order_id} is being set up! Almost ready..."
            )
        except Exception as e:
            logger.error(f"Error notifying user for setup order: {e}")

        await query.edit_message_text(
            f"⚙️ Order #{order_id} marked as SETUP.",
            reply_markup=get_admin_order_keyboard(order_id)
        )
    except Exception as e:
        logger.error(f"Error in aord_setup_callback: {e}")
        await query.edit_message_text("⚠️ Could not update order status.")


# ─── FEATURE 6: aord_deliver_{order_id} ConversationHandler ──────────────────

async def aord_deliver_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not is_admin(str(query.from_user.id)):
        await query.answer("⛔ Access denied.", show_alert=True)
        return ConversationHandler.END
    await query.answer()

    try:
        order_id = query.data.split('_', 2)[2]
        context.user_data['deliver_order_id'] = order_id
        await query.edit_message_text(
            f"📥 Enter delivery URL or content for order #{order_id}:"
        )
        print(f"[ADMIN] Admin initiating delivery for order {order_id}.")
        return DELIVER_URL
    except Exception as e:
        logger.error(f"Error in aord_deliver_entry: {e}")
        return ConversationHandler.END


async def deliver_url_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(str(update.effective_user.id)):
        await update.message.reply_text("⛔ Access denied.")
        return ConversationHandler.END

    delivery_url = update.message.text.strip()
    order_id = context.user_data.get('deliver_order_id')

    if not order_id:
        await update.message.reply_text("⚠️ Session expired. Try again.")
        return ConversationHandler.END

    try:
        order = get_order(order_id)
        if not order:
            await update.message.reply_text("⚠️ Order not found.")
            return ConversationHandler.END

        update_order_status(order_id, 'delivered', delivery_url=delivery_url)
        print(f"[ADMIN] Order {order_id} delivered with URL: {delivery_url}.")

        try:
            await context.bot.send_message(
                chat_id=int(order['user_id']),
                text=(
                    f"🚀 YOUR ORDER IS DELIVERED!\n"
                    f"━━━━━━━━━━\n"
                    f"Order: #{order_id}\n"
                    f"Agent: {order['agent_name']}\n\n"
                    f"📥 Access here:\n{delivery_url}\n\n"
                    f"Thank you for using AgentBD! 🎉"
                )
            )
        except Exception as e:
            logger.error(f"Error notifying user of delivery: {e}")

        await update.message.reply_text(
            f"✅ Order #{order_id} delivered successfully!",
            reply_markup=get_admin_keyboard()
        )
        context.user_data.pop('deliver_order_id', None)

    except Exception as e:
        logger.error(f"Error in deliver_url_received: {e}")
        await update.message.reply_text("⚠️ Could not deliver order. Try again.")

    return ConversationHandler.END


# ─── FEATURE 7: aord_cancel_{order_id} callback ──────────────────────────────

async def aord_cancel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not is_admin(str(query.from_user.id)):
        await query.answer("⛔ Access denied.", show_alert=True)
        return
    await query.answer("❌ Order cancelled")

    try:
        order_id = query.data.split('_', 2)[2]
        order = get_order(order_id)
        if not order:
            await query.edit_message_text("⚠️ Order not found.")
            return

        update_order_status(order_id, 'cancelled')
        amount = float(order.get('amount', 0))
        user_id = order['user_id']

        try:
            update_user_balance(user_id, amount)
            print(f"[ADMIN] Refunded ${amount:.2f} to user {user_id} for cancelled order {order_id}.")
        except Exception as e:
            logger.error(f"Error refunding user balance: {e}")

        try:
            await context.bot.send_message(
                chat_id=int(user_id),
                text=(
                    f"❌ Order #{order_id} has been cancelled. "
                    f"${amount:.2f} refunded to your wallet."
                )
            )
        except Exception as e:
            logger.error(f"Error notifying user of cancellation: {e}")

        await query.edit_message_text(
            f"❌ Order #{order_id} cancelled and ${amount:.2f} refunded to user.",
            reply_markup=get_admin_keyboard()
        )
        print(f"[ADMIN] Order {order_id} cancelled.")
    except Exception as e:
        logger.error(f"Error in aord_cancel_callback: {e}")
        await query.edit_message_text("⚠️ Could not cancel order.")


# ─── FEATURE 8: admin_withdrawals callback ────────────────────────────────────

async def admin_withdrawals_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not is_admin(str(query.from_user.id)):
        await query.answer("⛔ Access denied.", show_alert=True)
        return
    await query.answer()

    try:
        withdrawals = get_pending_withdrawals()
        if not withdrawals:
            await query.edit_message_text(
                "No pending withdrawals.",
                reply_markup=get_admin_keyboard()
            )
            return

        text = "💸 PENDING WITHDRAWALS\n━━━━━━━━━━\n"
        buttons = []
        for w in withdrawals:
            wid = w.get('withdrawal_id', '')
            amount = float(w.get('amount', 0))
            wallet = str(w.get('wallet', ''))
            user_id = w.get('user_id', 'N/A')
            wallet_short = wallet[:20] + '...' if len(wallet) > 20 else wallet
            label = f"💸 #{wid[:8]} | ${amount:.2f} | {wallet_short} | {user_id}"
            buttons.append([InlineKeyboardButton(label, callback_data=f"admin_wit_{wid}")])

        buttons.append([InlineKeyboardButton("🔙 Back", callback_data="admin_back")])
        keyboard = InlineKeyboardMarkup(buttons)
        await query.edit_message_text(
            text + f"Found {len(withdrawals)} pending withdrawal(s):",
            reply_markup=keyboard
        )
        print(f"[ADMIN] Admin viewed pending withdrawals ({len(withdrawals)}).")
    except Exception as e:
        logger.error(f"Error in admin_withdrawals_callback: {e}")
        await query.edit_message_text("⚠️ Could not load withdrawals.")


# ─── FEATURE 9: admin_wit_{withdrawal_id} callback ───────────────────────────

async def admin_withdrawal_detail_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not is_admin(str(query.from_user.id)):
        await query.answer("⛔ Access denied.", show_alert=True)
        return
    await query.answer()

    try:
        withdrawal_id = query.data.split('_', 2)[2]

        conn = sqlite3.connect(DB_NAME)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM withdrawals WHERE withdrawal_id = ?", (withdrawal_id,))
        row = cursor.fetchone()
        conn.close()

        if not row:
            await query.edit_message_text("⚠️ Withdrawal not found.")
            return

        w = dict(row)
        amount = float(w.get('amount', 0))
        text = (
            f"💸 WITHDRAWAL DETAILS\n"
            f"━━━━━━━━━━\n"
            f"🆔 ID: #{w['withdrawal_id']}\n"
            f"👤 User ID: {w['user_id']}\n"
            f"💵 Amount: ${amount:.2f}\n"
            f"💳 Wallet: {w.get('wallet', 'N/A')}\n"
            f"📊 Status: {w.get('status', 'pending').upper()}\n"
            f"📅 Date: {str(w.get('created_at', ''))[:19]}"
        )
        await query.edit_message_text(text, reply_markup=get_admin_withdraw_keyboard(withdrawal_id))
        print(f"[ADMIN] Admin viewing withdrawal {withdrawal_id}.")
    except Exception as e:
        logger.error(f"Error in admin_withdrawal_detail_callback: {e}")
        await query.edit_message_text("⚠️ Could not load withdrawal details.")


# ─── FEATURE 10: awit_approve_{withdrawal_id} callback ───────────────────────

async def awit_approve_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not is_admin(str(query.from_user.id)):
        await query.answer("⛔ Access denied.", show_alert=True)
        return
    await query.answer("✅ Withdrawal approved")

    try:
        withdrawal_id = query.data.split('_', 2)[2]

        conn = sqlite3.connect(DB_NAME)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM withdrawals WHERE withdrawal_id = ?", (withdrawal_id,))
        row = cursor.fetchone()
        conn.close()

        if not row:
            await query.edit_message_text("⚠️ Withdrawal not found.")
            return

        w = dict(row)
        update_withdrawal_status(withdrawal_id, 'approved')
        print(f"[ADMIN] Withdrawal {withdrawal_id} approved.")

        try:
            await context.bot.send_message(
                chat_id=int(w['user_id']),
                text=(
                    f"✅ Your withdrawal of ${float(w['amount']):.2f} has been "
                    f"APPROVED and sent to {w.get('wallet', 'N/A')}!"
                )
            )
        except Exception as e:
            logger.error(f"Error notifying user of withdrawal approval: {e}")

        await query.edit_message_text(
            f"✅ Withdrawal #{withdrawal_id} approved.",
            reply_markup=get_admin_keyboard()
        )
    except Exception as e:
        logger.error(f"Error in awit_approve_callback: {e}")
        await query.edit_message_text("⚠️ Could not approve withdrawal.")


# ─── FEATURE 11: awit_reject_{withdrawal_id} callback ────────────────────────

async def awit_reject_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not is_admin(str(query.from_user.id)):
        await query.answer("⛔ Access denied.", show_alert=True)
        return
    await query.answer("❌ Withdrawal rejected")

    try:
        withdrawal_id = query.data.split('_', 2)[2]

        conn = sqlite3.connect(DB_NAME)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM withdrawals WHERE withdrawal_id = ?", (withdrawal_id,))
        row = cursor.fetchone()
        conn.close()

        if not row:
            await query.edit_message_text("⚠️ Withdrawal not found.")
            return

        w = dict(row)
        amount = float(w.get('amount', 0))
        user_id = w['user_id']

        update_withdrawal_status(withdrawal_id, 'rejected')
        print(f"[ADMIN] Withdrawal {withdrawal_id} rejected.")

        try:
            update_user_balance(user_id, amount)
            print(f"[ADMIN] Refunded ${amount:.2f} to user {user_id} for rejected withdrawal.")
        except Exception as e:
            logger.error(f"Error refunding user for rejected withdrawal: {e}")

        try:
            await context.bot.send_message(
                chat_id=int(user_id),
                text=(
                    f"❌ Your withdrawal request was rejected. "
                    f"${amount:.2f} has been refunded to your wallet."
                )
            )
        except Exception as e:
            logger.error(f"Error notifying user of rejection: {e}")

        await query.edit_message_text(
            f"❌ Withdrawal #{withdrawal_id} rejected and ${amount:.2f} refunded.",
            reply_markup=get_admin_keyboard()
        )
    except Exception as e:
        logger.error(f"Error in awit_reject_callback: {e}")
        await query.edit_message_text("⚠️ Could not reject withdrawal.")


# ─── FEATURE 12: admin_add_cat ConversationHandler ───────────────────────────

async def admin_add_cat_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not is_admin(str(query.from_user.id)):
        await query.answer("⛔ Access denied.", show_alert=True)
        return ConversationHandler.END
    await query.answer()

    try:
        await query.edit_message_text("📁 Enter category name:")
        return ADD_CAT_NAME
    except Exception as e:
        logger.error(f"Error in admin_add_cat_entry: {e}")
        return ConversationHandler.END


async def add_cat_name_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(str(update.effective_user.id)):
        await update.message.reply_text("⛔ Access denied.")
        return ConversationHandler.END

    name = update.message.text.strip()
    context.user_data['new_cat_name'] = name

    try:
        await update.message.reply_text("🎨 Enter emoji for this category:")
        return ADD_CAT_EMOJI
    except Exception as e:
        logger.error(f"Error in add_cat_name_received: {e}")
        return ConversationHandler.END


async def add_cat_emoji_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(str(update.effective_user.id)):
        await update.message.reply_text("⛔ Access denied.")
        return ConversationHandler.END

    emoji = update.message.text.strip()
    name = context.user_data.get('new_cat_name', 'Unknown')

    try:
        add_category(name, emoji)
        print(f"[ADMIN] Added category: {emoji} {name}")
        await update.message.reply_text(
            f"✅ Category added: {emoji} {name}",
            reply_markup=get_admin_keyboard()
        )
        context.user_data.pop('new_cat_name', None)
    except Exception as e:
        logger.error(f"Error adding category: {e}")
        await update.message.reply_text("⚠️ Could not add category. Try again.")

    return ConversationHandler.END


# ─── FEATURE 13: admin_add_agent ConversationHandler ─────────────────────────

async def admin_add_agent_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not is_admin(str(query.from_user.id)):
        await query.answer("⛔ Access denied.", show_alert=True)
        return ConversationHandler.END
    await query.answer()

    try:
        await query.edit_message_text("🤖 Enter agent name:")
        return ADD_AGENT_NAME
    except Exception as e:
        logger.error(f"Error in admin_add_agent_entry: {e}")
        return ConversationHandler.END


async def add_agent_name_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(str(update.effective_user.id)):
        await update.message.reply_text("⛔ Access denied.")
        return ConversationHandler.END

    context.user_data['new_agent_name'] = update.message.text.strip()
    await update.message.reply_text("📝 Enter agent description:")
    return ADD_AGENT_DESC


async def add_agent_desc_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(str(update.effective_user.id)):
        await update.message.reply_text("⛔ Access denied.")
        return ConversationHandler.END

    context.user_data['new_agent_desc'] = update.message.text.strip()
    await update.message.reply_text("💵 Enter price (number only, e.g. 10.00):")
    return ADD_AGENT_PRICE


async def add_agent_price_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(str(update.effective_user.id)):
        await update.message.reply_text("⛔ Access denied.")
        return ConversationHandler.END

    try:
        price = float(update.message.text.strip())
        context.user_data['new_agent_price'] = price
    except ValueError:
        await update.message.reply_text("❌ Invalid price. Enter a number (e.g. 10.00):")
        return ADD_AGENT_PRICE

    try:
        categories = get_all_categories()
        if not categories:
            await update.message.reply_text("⚠️ No categories found. Add a category first.")
            return ConversationHandler.END

        cat_list = "\n".join([f"ID: {c['id']} — {c['emoji']} {c['name']}" for c in categories])
        await update.message.reply_text(f"📁 Available categories:\n{cat_list}\n\nEnter category ID:")
        return ADD_AGENT_CAT
    except Exception as e:
        logger.error(f"Error fetching categories for agent: {e}")
        await update.message.reply_text("⚠️ Could not load categories.")
        return ConversationHandler.END


async def add_agent_cat_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(str(update.effective_user.id)):
        await update.message.reply_text("⛔ Access denied.")
        return ConversationHandler.END

    try:
        cat_id = int(update.message.text.strip())
        context.user_data['new_agent_cat'] = cat_id
    except ValueError:
        await update.message.reply_text("❌ Invalid ID. Enter a valid category ID:")
        return ADD_AGENT_CAT

    await update.message.reply_text("🔗 Enter file/delivery URL (or type 'none'):")
    return ADD_AGENT_URL


async def add_agent_url_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(str(update.effective_user.id)):
        await update.message.reply_text("⛔ Access denied.")
        return ConversationHandler.END

    url_text = update.message.text.strip()
    delivery_url = None if url_text.lower() == 'none' else url_text

    name = context.user_data.get('new_agent_name')
    description = context.user_data.get('new_agent_desc')
    price = context.user_data.get('new_agent_price')
    category_id = context.user_data.get('new_agent_cat')

    try:
        agent_id = add_agent(name, description, price, category_id, delivery_url)
        print(f"[ADMIN] Added agent: {name} (ID: {agent_id})")
        await update.message.reply_text(
            f"✅ Agent added! ID: {agent_id}\n"
            f"Name: {name}\n"
            f"Price: ${price:.2f}\n"
            f"Category ID: {category_id}",
            reply_markup=get_admin_keyboard()
        )
        for key in ['new_agent_name', 'new_agent_desc', 'new_agent_price', 'new_agent_cat']:
            context.user_data.pop(key, None)
    except Exception as e:
        logger.error(f"Error adding agent: {e}")
        await update.message.reply_text("⚠️ Could not add agent. Try again.")

    return ConversationHandler.END


# ─── FEATURE 14: admin_broadcast ConversationHandler ─────────────────────────

async def admin_broadcast_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not is_admin(str(query.from_user.id)):
        await query.answer("⛔ Access denied.", show_alert=True)
        return ConversationHandler.END
    await query.answer()

    try:
        await query.edit_message_text(
            "📢 Enter broadcast message (supports emojis and formatting):"
        )
        return BROADCAST_TEXT
    except Exception as e:
        logger.error(f"Error in admin_broadcast_entry: {e}")
        return ConversationHandler.END


async def broadcast_text_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(str(update.effective_user.id)):
        await update.message.reply_text("⛔ Access denied.")
        return ConversationHandler.END

    broadcast_message = update.message.text.strip()

    try:
        user_ids = get_all_user_ids()
        print(f"[ADMIN] Broadcasting to {len(user_ids)} users.")

        success = 0
        fail = 0
        for uid in user_ids:
            try:
                await context.bot.send_message(chat_id=int(uid), text=broadcast_message)
                success += 1
            except Exception as e:
                logger.error(f"Broadcast failed for user {uid}: {e}")
                fail += 1

        await update.message.reply_text(
            f"📢 Broadcast complete!\n✅ Sent: {success}\n❌ Failed: {fail}",
            reply_markup=get_admin_keyboard()
        )
        print(f"[ADMIN] Broadcast done. Sent: {success}, Failed: {fail}.")
    except Exception as e:
        logger.error(f"Error in broadcast_text_received: {e}")
        await update.message.reply_text("⚠️ Broadcast failed.")

    return ConversationHandler.END


# ─── FEATURE 15: admin_stats callback ────────────────────────────────────────

async def admin_stats_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not is_admin(str(query.from_user.id)):
        await query.answer("⛔ Access denied.", show_alert=True)
        return
    await query.answer()

    try:
        stats = get_stats()
        text = (
            f"📊 SYSTEM STATISTICS\n"
            f"━━━━━━━━━━\n"
            f"👥 Users: {stats.get('total_users', 0)}\n"
            f"📦 Orders: {stats.get('total_orders', 0)}\n"
            f"⏳ Pending: {stats.get('pending_orders', 0)}\n"
            f"💰 Revenue: ${float(stats.get('total_revenue', 0)):.2f}\n"
            f"💸 Withdrawals: {stats.get('total_withdrawals', 0)}"
        )
        await query.edit_message_text(text, reply_markup=get_admin_keyboard())
        print(f"[ADMIN] Admin viewed system stats.")
    except Exception as e:
        logger.error(f"Error in admin_stats_callback: {e}")
        await query.edit_message_text("⚠️ Could not load stats.")


# ─── FEATURE 16: admin_delete_agent ConversationHandler ──────────────────────

async def admin_delete_agent_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not is_admin(str(query.from_user.id)):
        await query.answer("⛔ Access denied.", show_alert=True)
        return ConversationHandler.END
    await query.answer()

    try:
        await query.edit_message_text("🗑️ Enter Agent ID to delete:")
        return DELETE_AGENT_ID
    except Exception as e:
        logger.error(f"Error in admin_delete_agent_entry: {e}")
        return ConversationHandler.END


async def delete_agent_id_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(str(update.effective_user.id)):
        await update.message.reply_text("⛔ Access denied.")
        return ConversationHandler.END

    try:
        agent_id = int(update.message.text.strip())
        delete_agent(agent_id)
        print(f"[ADMIN] Deleted agent ID: {agent_id}")
        await update.message.reply_text(
            f"✅ Agent {agent_id} deleted.",
            reply_markup=get_admin_keyboard()
        )
    except ValueError:
        await update.message.reply_text("❌ Invalid ID. Enter a valid integer Agent ID:")
        return DELETE_AGENT_ID
    except Exception as e:
        logger.error(f"Error deleting agent: {e}")
        await update.message.reply_text("⚠️ Could not delete agent.")

    return ConversationHandler.END


# ─── FEATURE 17: admin_user_count callback ───────────────────────────────────

async def admin_user_count_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not is_admin(str(query.from_user.id)):
        await query.answer("⛔ Access denied.", show_alert=True)
        return
    await query.answer()

    try:
        stats = get_stats()
        count = stats.get('total_users', 0)
        await query.edit_message_text(
            f"👥 Total registered users: {count}",
            reply_markup=get_admin_keyboard()
        )
        print(f"[ADMIN] Admin checked user count: {count}.")
    except Exception as e:
        logger.error(f"Error in admin_user_count_callback: {e}")
        await query.edit_message_text("⚠️ Could not load user count.")


# ─── admin_back callback ──────────────────────────────────────────────────────

async def admin_back_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not is_admin(str(query.from_user.id)):
        await query.answer("⛔ Access denied.", show_alert=True)
        return
    await query.answer()

    try:
        await query.edit_message_text(
            "🔐 ADMIN PANEL\n━━━━━━━━━━\nWelcome, Admin! Choose an action:",
            reply_markup=get_admin_keyboard()
        )
    except Exception as e:
        logger.error(f"Error in admin_back_callback: {e}")


# ─── Cancel conversation ──────────────────────────────────────────────────────

async def cancel_admin_conv(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not is_admin(str(user.id)):
        await update.message.reply_text("⛔ Access denied.")
        return ConversationHandler.END

    await update.message.reply_text(
        "❌ Operation cancelled.",
        reply_markup=get_admin_keyboard()
    )
    context.user_data.clear()
    return ConversationHandler.END


# ─── REGISTER ALL ADMIN HANDLERS ─────────────────────────────────────────────

def get_admin_handlers():
    deliver_conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(aord_deliver_entry, pattern="^aord_deliver_")
        ],
        states={
            DELIVER_URL: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, deliver_url_received)
            ],
        },
        fallbacks=[
            CommandHandler("cancel", cancel_admin_conv)
        ],
        per_message=False,
    )

    add_cat_conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(admin_add_cat_entry, pattern="^admin_add_cat$")
        ],
        states={
            ADD_CAT_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_cat_name_received)
            ],
            ADD_CAT_EMOJI: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_cat_emoji_received)
            ],
        },
        fallbacks=[
            CommandHandler("cancel", cancel_admin_conv)
        ],
        per_message=False,
    )

    add_agent_conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(admin_add_agent_entry, pattern="^admin_add_agent$")
        ],
        states={
            ADD_AGENT_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_agent_name_received)
            ],
            ADD_AGENT_DESC: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_agent_desc_received)
            ],
            ADD_AGENT_PRICE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_agent_price_received)
            ],
            ADD_AGENT_CAT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_agent_cat_received)
            ],
            ADD_AGENT_URL: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_agent_url_received)
            ],
        },
        fallbacks=[
            CommandHandler("cancel", cancel_admin_conv)
        ],
        per_message=False,
    )

    broadcast_conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(admin_broadcast_entry, pattern="^admin_broadcast$")
        ],
        states={
            BROADCAST_TEXT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, broadcast_text_received)
            ],
        },
        fallbacks=[
            CommandHandler("cancel", cancel_admin_conv)
        ],
        per_message=False,
    )

    delete_agent_conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(admin_delete_agent_entry, pattern="^admin_delete_agent$")
        ],
        states={
            DELETE_AGENT_ID: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, delete_agent_id_received)
            ],
        },
        fallbacks=[
            CommandHandler("cancel", cancel_admin_conv)
        ],
        per_message=False,
    )

    handlers = [
        CommandHandler("admin", admin_command),
        deliver_conv,
        add_cat_conv,
        add_agent_conv,
        broadcast_conv,
        delete_agent_conv,
        CallbackQueryHandler(admin_orders_callback, pattern="^admin_orders$"),
        CallbackQueryHandler(admin_order_detail_callback, pattern="^admin_ord_"),
        CallbackQueryHandler(aord_verified_callback, pattern="^aord_verified_"),
        CallbackQueryHandler(aord_setup_callback, pattern="^aord_setup_"),
        CallbackQueryHandler(aord_cancel_callback, pattern="^aord_cancel_"),
        CallbackQueryHandler(admin_withdrawals_callback, pattern="^admin_withdrawals$"),
        CallbackQueryHandler(admin_withdrawal_detail_callback, pattern="^admin_wit_"),
        CallbackQueryHandler(awit_approve_callback, pattern="^awit_approve_"),
        CallbackQueryHandler(awit_reject_callback, pattern="^awit_reject_"),
        CallbackQueryHandler(admin_stats_callback, pattern="^admin_stats$"),
        CallbackQueryHandler(admin_user_count_callback, pattern="^admin_user_count$"),
        CallbackQueryHandler(admin_back_callback, pattern="^admin_back$"),
    ]

    return handlers
