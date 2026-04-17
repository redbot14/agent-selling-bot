import os
import uuid
import logging

from telegram import Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ConversationHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from database import (
    get_or_create_user,
    get_user,
    update_user_email,
    get_all_categories,
    get_agents_by_category,
    get_agent,
    create_order,
    get_order,
    get_user_orders,
    get_stats,
    create_withdrawal,
    deduct_user_balance,
)
from keyboards import (
    get_home_keyboard,
    get_profile_keyboard,
    get_wallet_keyboard,
    get_categories_keyboard,
    get_agents_keyboard,
    get_agent_detail_keyboard,
    get_payment_method_keyboard,
    get_orders_keyboard,
    get_order_detail_keyboard,
    get_back_to_home_keyboard,
    get_stats_keyboard,
)

logger = logging.getLogger(__name__)

EMAIL_INPUT = 0
TXN_ID_INPUT = 1
WITHDRAW_WALLET = 2
WITHDRAW_AMOUNT = 3

ADMIN_TELEGRAM_ID = os.environ.get("ADMIN_TELEGRAM_ID", "")
REFERRAL_BONUS_AMOUNT = os.environ.get("REFERRAL_BONUS_AMOUNT", "2.0")
MIN_WITHDRAW_AMOUNT = float(os.environ.get("MIN_WITHDRAW_AMOUNT", "5.0"))


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        user = update.effective_user
        args = context.args
        referred_by = args[0] if args else None

        db_user = get_or_create_user(
            str(user.id),
            user.full_name,
            user.username or "",
            referred_by,
        )

        name = db_user.get("name", user.full_name)
        welcome_text = (
            f"🎉 Welcome to AgentBD Marketplace, {name}!\n\n"
            f"💰 Signup Bonus: $1.00 added!\n\n"
            f"Choose an option below 👇"
        )
        await update.message.reply_text(
            welcome_text,
            reply_markup=get_home_keyboard(),
        )
        print(f"✅ /start handled for user {user.id} ({user.full_name})")
    except Exception as e:
        logger.error(f"❌ start_command error: {e}")
        await update.message.reply_text("❌ Something went wrong. Please try again.")


async def home_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        query = update.callback_query
        await query.answer()
        user = update.effective_user
        db_user = get_user(str(user.id))
        name = db_user.get("name", user.full_name) if db_user else user.full_name
        text = (
            f"🏠 Welcome back, {name}!\n\n"
            f"Choose an option below 👇"
        )
        await query.edit_message_text(text, reply_markup=get_home_keyboard())
        print(f"✅ home_callback for user {user.id}")
    except Exception as e:
        logger.error(f"❌ home_callback error: {e}")


async def profile_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        query = update.callback_query
        await query.answer()
        user = update.effective_user
        db_user = get_user(str(user.id))
        if not db_user:
            await query.edit_message_text("❌ User not found. Please /start again.")
            return
        text = (
            f"👤 YOUR PROFILE\n"
            f"━━━━━━━━━━━━━━\n"
            f"📛 Name: {db_user.get('name', 'N/A')}\n"
            f"🆔 ID: {db_user.get('telegram_id', 'N/A')}\n"
            f"✉️ Email: {db_user.get('email') or 'Not set'}\n"
            f"📦 Total Orders: {db_user.get('total_orders', 0)}\n"
            f"🔗 Referral Code: {db_user.get('referral_code', 'N/A')}\n"
            f"💰 Balance: ${db_user.get('balance', 0.0):.2f}\n"
            f"🎁 Bonus Earned: ${db_user.get('bonus', 0.0):.2f}"
        )
        await query.edit_message_text(text, reply_markup=get_profile_keyboard())
        print(f"✅ profile_callback for user {user.id}")
    except Exception as e:
        logger.error(f"❌ profile_callback error: {e}")


async def wallet_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        query = update.callback_query
        await query.answer()
        user = update.effective_user
        db_user = get_user(str(user.id))
        if not db_user:
            await query.edit_message_text("❌ User not found. Please /start again.")
            return
        text = (
            f"💼 YOUR WALLET\n"
            f"━━━━━━━━━━━━━━\n"
            f"💵 Balance: ${db_user.get('balance', 0.0):.2f}\n"
            f"🎁 Bonus: ${db_user.get('bonus', 0.0):.2f}\n"
            f"📦 Total Orders: {db_user.get('total_orders', 0)}"
        )
        await query.edit_message_text(text, reply_markup=get_wallet_keyboard())
        print(f"✅ wallet_callback for user {user.id}")
    except Exception as e:
        logger.error(f"❌ wallet_callback error: {e}")


async def update_email_entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        query = update.callback_query
        await query.answer()
        await query.edit_message_text(
            "✉️ Please type your email address:",
            reply_markup=get_back_to_home_keyboard(),
        )
        print(f"✅ update_email_entry for user {update.effective_user.id}")
        return EMAIL_INPUT
    except Exception as e:
        logger.error(f"❌ update_email_entry error: {e}")
        return ConversationHandler.END


async def email_input_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        user = update.effective_user
        email = update.message.text.strip()
        if "@" not in email or "." not in email:
            await update.message.reply_text(
                "❌ Invalid email. Try again.",
                reply_markup=get_back_to_home_keyboard(),
            )
            return EMAIL_INPUT
        success = update_user_email(str(user.id), email)
        if success:
            db_user = get_user(str(user.id))
            if db_user:
                profile_text = (
                    f"👤 YOUR PROFILE\n"
                    f"━━━━━━━━━━━━━━\n"
                    f"📛 Name: {db_user.get('name', 'N/A')}\n"
                    f"🆔 ID: {db_user.get('telegram_id', 'N/A')}\n"
                    f"✉️ Email: {db_user.get('email') or 'Not set'}\n"
                    f"📦 Total Orders: {db_user.get('total_orders', 0)}\n"
                    f"🔗 Referral Code: {db_user.get('referral_code', 'N/A')}\n"
                    f"💰 Balance: ${db_user.get('balance', 0.0):.2f}\n"
                    f"🎁 Bonus Earned: ${db_user.get('bonus', 0.0):.2f}"
                )
                await update.message.reply_text(
                    f"✅ Email updated!\n\n{profile_text}",
                    reply_markup=get_profile_keyboard(),
                )
            else:
                await update.message.reply_text(
                    "✅ Email updated!",
                    reply_markup=get_back_to_home_keyboard(),
                )
        else:
            await update.message.reply_text(
                "❌ Failed to update email. Try again.",
                reply_markup=get_back_to_home_keyboard(),
            )
        print(f"✅ email_input_received for user {user.id}: {email}")
        return ConversationHandler.END
    except Exception as e:
        logger.error(f"❌ email_input_received error: {e}")
        return ConversationHandler.END


async def buy_agent_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        query = update.callback_query
        await query.answer()
        categories = get_all_categories()
        if not categories:
            await query.edit_message_text(
                "No categories available yet.",
                reply_markup=get_back_to_home_keyboard(),
            )
            return
        text = (
            "🛒 SELECT CATEGORY\n"
            "━━━━━━━━━━\n"
            "Choose what type of agent you want:"
        )
        await query.edit_message_text(text, reply_markup=get_categories_keyboard(categories))
        print(f"✅ buy_agent_callback for user {update.effective_user.id}")
    except Exception as e:
        logger.error(f"❌ buy_agent_callback error: {e}")


async def category_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        query = update.callback_query
        await query.answer()
        category_id = int(query.data.split("_")[1])
        agents = get_agents_by_category(category_id)
        if not agents:
            await query.edit_message_text(
                "No agents in this category yet.",
                reply_markup=get_back_to_home_keyboard(),
            )
            return
        text = (
            "🤖 AVAILABLE AGENTS\n"
            "━━━━━━━━━━\n"
            "Select an agent to view details:"
        )
        await query.edit_message_text(text, reply_markup=get_agents_keyboard(agents))
        print(f"✅ category_callback: cat_id={category_id} for user {update.effective_user.id}")
    except Exception as e:
        logger.error(f"❌ category_callback error: {e}")


async def agent_detail_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        query = update.callback_query
        await query.answer()
        agent_id = int(query.data.split("_")[1])
        agent = get_agent(agent_id)
        if not agent:
            await query.edit_message_text(
                "❌ Agent not found.",
                reply_markup=get_back_to_home_keyboard(),
            )
            return
        text = (
            f"🤖 {agent['name']}\n"
            f"━━━━━━━━━━\n"
            f"📝 {agent['description']}\n"
            f"💵 Price: ${agent['price']:.2f}\n\n"
            f"✅ Ready to buy? Click Buy Now!"
        )
        await query.edit_message_text(
            text,
            reply_markup=get_agent_detail_keyboard(agent_id, agent["category_id"]),
        )
        print(f"✅ agent_detail_callback: agent_id={agent_id} for user {update.effective_user.id}")
    except Exception as e:
        logger.error(f"❌ agent_detail_callback error: {e}")


async def buy_now_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        query = update.callback_query
        await query.answer()
        agent_id = int(query.data.split("_")[1])
        agent = get_agent(agent_id)
        if not agent:
            await query.edit_message_text(
                "❌ Agent not found.",
                reply_markup=get_back_to_home_keyboard(),
            )
            return
        context.user_data["pending_agent_id"] = agent_id
        text = (
            f"💳 SELECT PAYMENT METHOD\n"
            f"━━━━━━━━━━\n"
            f"Agent: {agent['name']}\n"
            f"Price: ${agent['price']:.2f}\n\n"
            f"Choose payment method:"
        )
        await query.edit_message_text(
            text,
            reply_markup=get_payment_method_keyboard(agent_id),
        )
        print(f"✅ buy_now_callback: agent_id={agent_id} for user {update.effective_user.id}")
    except Exception as e:
        logger.error(f"❌ buy_now_callback error: {e}")


async def payment_method_entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        query = update.callback_query
        await query.answer()
        parts = query.data.split("_")
        payment_method = parts[1]
        agent_id = int(parts[2])
        agent = get_agent(agent_id)
        if not agent:
            await query.edit_message_text(
                "❌ Agent not found.",
                reply_markup=get_back_to_home_keyboard(),
            )
            return ConversationHandler.END

        context.user_data["payment_method"] = payment_method
        context.user_data["payment_agent_id"] = agent_id
        context.user_data["payment_agent_name"] = agent["name"]
        context.user_data["payment_agent_price"] = agent["price"]

        price = agent["price"]
        if payment_method == "bKash":
            instructions = (
                f"💚 BKASH PAYMENT\n"
                f"━━━━━━━━━━\n"
                f"Send ${price:.2f} to: 01XXXXXXXXXX (bKash)\n\n"
                f"Then enter your Transaction ID below:"
            )
        elif payment_method == "Nagad":
            instructions = (
                f"🔴 NAGAD PAYMENT\n"
                f"━━━━━━━━━━\n"
                f"Send ${price:.2f} to: 01XXXXXXXXXX (Nagad)\n\n"
                f"Then enter your Transaction ID below:"
            )
        else:
            instructions = (
                f"💛 USDT TRC20 PAYMENT\n"
                f"━━━━━━━━━━\n"
                f"Send ${price:.2f} USDT TRC20 to:\n"
                f"TXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX\n\n"
                f"Then enter your Transaction ID below:"
            )

        await query.edit_message_text(instructions)
        print(
            f"✅ payment_method_entry: method={payment_method} agent_id={agent_id} "
            f"for user {update.effective_user.id}"
        )
        return TXN_ID_INPUT
    except Exception as e:
        logger.error(f"❌ payment_method_entry error: {e}")
        return ConversationHandler.END


async def txn_id_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        user = update.effective_user
        txn_id = update.message.text.strip()
        agent_id = context.user_data.get("payment_agent_id")
        agent_name = context.user_data.get("payment_agent_name")
        price = context.user_data.get("payment_agent_price")
        payment_method = context.user_data.get("payment_method")

        if not all([agent_id, agent_name, price, payment_method]):
            await update.message.reply_text(
                "❌ Session expired. Please start over.",
                reply_markup=get_back_to_home_keyboard(),
            )
            return ConversationHandler.END

        order_id = str(uuid.uuid4()).replace("-", "")[:12].upper()
        success = create_order(
            order_id,
            str(user.id),
            agent_id,
            agent_name,
            price,
            payment_method,
            txn_id,
        )

        if not success:
            await update.message.reply_text(
                "❌ Failed to create order. Please contact support.",
                reply_markup=get_back_to_home_keyboard(),
            )
            return ConversationHandler.END

        if ADMIN_TELEGRAM_ID:
            try:
                await context.bot.send_message(
                    chat_id=ADMIN_TELEGRAM_ID,
                    text=(
                        f"🔔 NEW ORDER!\n"
                        f"Order: #{order_id}\n"
                        f"User: {user.full_name} ({user.id})\n"
                        f"Agent: {agent_name}\n"
                        f"Amount: ${price:.2f}\n"
                        f"Payment: {payment_method}\n"
                        f"Txn ID: {txn_id}"
                    ),
                )
            except Exception as notify_err:
                logger.error(f"❌ Failed to notify admin: {notify_err}")

        await update.message.reply_text(
            f"✅ ORDER PLACED!\n"
            f"━━━━━━━━━━\n"
            f"📌 Order ID: #{order_id}\n"
            f"🤖 Agent: {agent_name}\n"
            f"💵 Amount: ${price:.2f}\n"
            f"📊 Status: ⏳ PENDING\n\n"
            f"Admin will verify your payment soon!",
            reply_markup=get_back_to_home_keyboard(),
        )

        context.user_data.clear()
        print(f"✅ txn_id_received: order={order_id} for user {user.id}")
        return ConversationHandler.END
    except Exception as e:
        logger.error(f"❌ txn_id_received error: {e}")
        return ConversationHandler.END


async def my_orders_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        query = update.callback_query
        await query.answer()
        user = update.effective_user
        orders = get_user_orders(str(user.id))
        if not orders:
            await query.edit_message_text(
                "📦 You have no orders yet.",
                reply_markup=get_back_to_home_keyboard(),
            )
            return
        text = (
            f"📦 YOUR ORDERS\n"
            f"━━━━━━━━━━\n"
            f"You have {len(orders)} order(s):"
        )
        await query.edit_message_text(text, reply_markup=get_orders_keyboard(orders))
        print(f"✅ my_orders_callback for user {user.id}")
    except Exception as e:
        logger.error(f"❌ my_orders_callback error: {e}")


async def order_detail_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        query = update.callback_query
        await query.answer()
        order_id = query.data.split("_", 1)[1]
        order = get_order(order_id)
        if not order:
            await query.edit_message_text(
                "❌ Order not found.",
                reply_markup=get_back_to_home_keyboard(),
            )
            return

        status_emojis = {
            "pending": "⏳",
            "verified": "✅",
            "setup": "⚙️",
            "delivered": "🚀",
            "cancelled": "❌",
        }
        status = order.get("status", "pending")
        emoji = status_emojis.get(status, "❓")

        created_at = order.get("created_at", "N/A")
        created_date = created_at[:10] if created_at and len(created_at) >= 10 else created_at

        text = (
            f"📦 ORDER DETAILS\n"
            f"━━━━━━━━━━\n"
            f"🆔 Order: #{order.get('id', 'N/A')}\n"
            f"🤖 Agent: {order.get('agent_name', 'N/A')}\n"
            f"💵 Amount: ${order.get('amount', 0.0):.2f}\n"
            f"💳 Payment: {order.get('payment_method', 'N/A')}\n"
            f"📊 Status: {emoji} {status.upper()}\n"
            f"📅 Date: {created_date}"
        )

        if status == "delivered" and order.get("delivery_url"):
            text += f"\n\n🚀 DELIVERY:\n{order['delivery_url']}"

        await query.edit_message_text(
            text,
            reply_markup=get_order_detail_keyboard(order_id),
        )
        print(f"✅ order_detail_callback: order_id={order_id} for user {update.effective_user.id}")
    except Exception as e:
        logger.error(f"❌ order_detail_callback error: {e}")


async def statistics_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        query = update.callback_query
        await query.answer()
        user = update.effective_user
        stats = get_stats()
        db_user = get_user(str(user.id))
        user_orders = db_user.get("total_orders", 0) if db_user else 0
        user_balance = db_user.get("balance", 0.0) if db_user else 0.0

        text = (
            f"📊 STATISTICS\n"
            f"━━━━━━━━━━\n"
            f"👥 Total Users: {stats.get('total_users', 0)}\n"
            f"📦 Total Orders: {stats.get('total_orders', 0)}\n"
            f"💰 Total Revenue: ${stats.get('total_revenue', 0.0):.2f}\n"
            f"⏳ Pending Orders: {stats.get('pending_orders', 0)}\n\n"
            f"👤 YOUR STATS\n"
            f"━━━━━━━━━━\n"
            f"📦 Your Orders: {user_orders}\n"
            f"💵 Your Balance: ${user_balance:.2f}"
        )
        await query.edit_message_text(text, reply_markup=get_stats_keyboard())
        print(f"✅ statistics_callback for user {user.id}")
    except Exception as e:
        logger.error(f"❌ statistics_callback error: {e}")


async def referral_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        query = update.callback_query
        await query.answer()
        user = update.effective_user
        db_user = get_user(str(user.id))
        if not db_user:
            await query.edit_message_text(
                "❌ User not found. Please /start again.",
                reply_markup=get_back_to_home_keyboard(),
            )
            return
        bot_username = context.bot.username
        referral_code = db_user.get("referral_code", "N/A")
        referral_link = f"https://t.me/{bot_username}?start={referral_code}"
        text = (
            f"🔗 YOUR REFERRAL LINK\n"
            f"━━━━━━━━━━\n"
            f"{referral_link}\n\n"
            f"💰 Earn ${REFERRAL_BONUS_AMOUNT} for each friend who joins!\n"
            f"👥 Share this link and earn passive income!"
        )
        await query.edit_message_text(text, reply_markup=get_back_to_home_keyboard())
        print(f"✅ referral_callback for user {user.id}")
    except Exception as e:
        logger.error(f"❌ referral_callback error: {e}")


async def withdraw_entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        query = update.callback_query
        await query.answer()
        user = update.effective_user
        db_user = get_user(str(user.id))
        if not db_user:
            await query.edit_message_text(
                "❌ User not found. Please /start again.",
                reply_markup=get_back_to_home_keyboard(),
            )
            return ConversationHandler.END

        balance = db_user.get("balance", 0.0)
        if balance < MIN_WITHDRAW_AMOUNT:
            await query.edit_message_text(
                f"❌ Minimum withdrawal is ${MIN_WITHDRAW_AMOUNT:.2f}. "
                f"Your balance: ${balance:.2f}",
                reply_markup=get_back_to_home_keyboard(),
            )
            return ConversationHandler.END

        context.user_data["withdraw_balance"] = balance
        await query.edit_message_text(
            f"💰 WITHDRAWAL\n"
            f"━━━━━━━━━━\n"
            f"Your balance: ${balance:.2f}\n\n"
            f"Please enter your wallet address (bKash/Nagad/USDT):"
        )
        print(f"✅ withdraw_entry for user {user.id}")
        return WITHDRAW_WALLET
    except Exception as e:
        logger.error(f"❌ withdraw_entry error: {e}")
        return ConversationHandler.END


async def withdraw_wallet_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        wallet = update.message.text.strip()
        if not wallet:
            await update.message.reply_text(
                "❌ Invalid wallet address. Please try again."
            )
            return WITHDRAW_WALLET
        context.user_data["withdraw_wallet"] = wallet
        balance = context.user_data.get("withdraw_balance", 0.0)
        await update.message.reply_text(
            f"💵 Enter amount to withdraw (min ${MIN_WITHDRAW_AMOUNT:.2f}, max ${balance:.2f}):"
        )
        print(f"✅ withdraw_wallet_received for user {update.effective_user.id}: {wallet}")
        return WITHDRAW_AMOUNT
    except Exception as e:
        logger.error(f"❌ withdraw_wallet_received error: {e}")
        return ConversationHandler.END


async def withdraw_amount_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        user = update.effective_user
        amount_text = update.message.text.strip()

        try:
            amount = float(amount_text)
        except ValueError:
            await update.message.reply_text(
                "❌ Invalid amount. Please enter a valid number.",
                reply_markup=get_back_to_home_keyboard(),
            )
            return WITHDRAW_AMOUNT

        if amount < MIN_WITHDRAW_AMOUNT:
            await update.message.reply_text(
                f"❌ Minimum withdrawal is ${MIN_WITHDRAW_AMOUNT:.2f}. "
                f"Please enter a valid amount.",
                reply_markup=get_back_to_home_keyboard(),
            )
            return WITHDRAW_AMOUNT

        db_user = get_user(str(user.id))
        if not db_user:
            await update.message.reply_text(
                "❌ User not found.",
                reply_markup=get_back_to_home_keyboard(),
            )
            return ConversationHandler.END

        balance = db_user.get("balance", 0.0)
        if balance < amount:
            await update.message.reply_text(
                f"❌ Insufficient balance. Your balance: ${balance:.2f}",
                reply_markup=get_back_to_home_keyboard(),
            )
            return WITHDRAW_AMOUNT

        wallet = context.user_data.get("withdraw_wallet", "")
        withdrawal_id = str(uuid.uuid4()).replace("-", "")[:12].upper()

        success = create_withdrawal(withdrawal_id, str(user.id), amount, wallet)
        if not success:
            await update.message.reply_text(
                "❌ Failed to create withdrawal request. Please contact support.",
                reply_markup=get_back_to_home_keyboard(),
            )
            return ConversationHandler.END

        deduct_user_balance(str(user.id), amount)

        if ADMIN_TELEGRAM_ID:
            try:
                await context.bot.send_message(
                    chat_id=ADMIN_TELEGRAM_ID,
                    text=(
                        f"💸 WITHDRAWAL REQUEST!\n"
                        f"User: {user.full_name} ({user.id})\n"
                        f"Amount: ${amount:.2f}\n"
                        f"Wallet: {wallet}"
                    ),
                )
            except Exception as notify_err:
                logger.error(f"❌ Failed to notify admin about withdrawal: {notify_err}")

        await update.message.reply_text(
            f"✅ Withdrawal requested!\n"
            f"Amount: ${amount:.2f}\n"
            f"Admin will process within 24 hours.",
            reply_markup=get_back_to_home_keyboard(),
        )

        context.user_data.clear()
        print(f"✅ withdraw_amount_received: withdrawal_id={withdrawal_id} for user {user.id}")
        return ConversationHandler.END
    except Exception as e:
        logger.error(f"❌ withdraw_amount_received error: {e}")
        return ConversationHandler.END


async def bonus_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        query = update.callback_query
        await query.answer()
        text = (
            f"🎁 BONUS SYSTEM\n"
            f"━━━━━━━━━━\n"
            f"✅ Signup Bonus: $1.00 (received on join)\n"
            f"🔗 Referral Bonus: $2.00 per friend\n\n"
            f"Invite friends to earn more! Use your referral link."
        )
        await query.edit_message_text(text, reply_markup=get_back_to_home_keyboard())
        print(f"✅ bonus_callback for user {update.effective_user.id}")
    except Exception as e:
        logger.error(f"❌ bonus_callback error: {e}")


async def support_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        query = update.callback_query
        await query.answer()
        text = (
            f"📞 SUPPORT\n"
            f"━━━━━━━━━━\n"
            f"For help, contact admin:\n"
            f"@AgentBDSupport\n\n"
            f"Or type your issue and send — admin will reply shortly.\n\n"
            f"⏰ Response time: within 2 hours"
        )
        await query.edit_message_text(text, reply_markup=get_back_to_home_keyboard())
        print(f"✅ support_callback for user {update.effective_user.id}")
    except Exception as e:
        logger.error(f"❌ support_callback error: {e}")


async def cancel_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        if update.callback_query:
            await update.callback_query.answer()
            await update.callback_query.edit_message_text(
                "❌ Operation cancelled.",
                reply_markup=get_back_to_home_keyboard(),
            )
        elif update.message:
            await update.message.reply_text(
                "❌ Operation cancelled.",
                reply_markup=get_back_to_home_keyboard(),
            )
        context.user_data.clear()
        return ConversationHandler.END
    except Exception as e:
        logger.error(f"❌ cancel_conversation error: {e}")
        return ConversationHandler.END


def get_user_handlers() -> list:
    email_conversation = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(update_email_entry, pattern="^update_email$"),
        ],
        states={
            EMAIL_INPUT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, email_input_received),
            ],
        },
        fallbacks=[
            CallbackQueryHandler(cancel_conversation, pattern="^home$"),
            CommandHandler("start", start_command),
        ],
        allow_reentry=True,
    )

    payment_conversation = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(payment_method_entry, pattern=r"^pay_"),
        ],
        states={
            TXN_ID_INPUT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, txn_id_received),
            ],
        },
        fallbacks=[
            CallbackQueryHandler(cancel_conversation, pattern="^home$"),
            CommandHandler("start", start_command),
        ],
        allow_reentry=True,
    )

    withdraw_conversation = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(withdraw_entry, pattern="^withdraw$"),
        ],
        states={
            WITHDRAW_WALLET: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, withdraw_wallet_received),
            ],
            WITHDRAW_AMOUNT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, withdraw_amount_received),
            ],
        },
        fallbacks=[
            CallbackQueryHandler(cancel_conversation, pattern="^home$"),
            CommandHandler("start", start_command),
        ],
        allow_reentry=True,
    )

    handlers = [
        CommandHandler("start", start_command),
        email_conversation,
        payment_conversation,
        withdraw_conversation,
        CallbackQueryHandler(home_callback, pattern="^home$"),
        CallbackQueryHandler(profile_callback, pattern="^profile$"),
        CallbackQueryHandler(wallet_callback, pattern="^wallet$"),
        CallbackQueryHandler(buy_agent_callback, pattern="^buy_agent$"),
        CallbackQueryHandler(category_callback, pattern=r"^cat_\d+$"),
        CallbackQueryHandler(agent_detail_callback, pattern=r"^agent_\d+$"),
        CallbackQueryHandler(buy_now_callback, pattern=r"^buy_\d+$"),
        CallbackQueryHandler(my_orders_callback, pattern="^my_orders$"),
        CallbackQueryHandler(order_detail_callback, pattern=r"^order_.+$"),
        CallbackQueryHandler(statistics_callback, pattern="^statistics$"),
        CallbackQueryHandler(referral_callback, pattern="^referral$"),
        CallbackQueryHandler(bonus_callback, pattern="^bonus$"),
        CallbackQueryHandler(support_callback, pattern="^support$"),
    ]

    return handlers
