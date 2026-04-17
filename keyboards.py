from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def get_home_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton("⚡ Referral Link", callback_data="referral"),
            InlineKeyboardButton("👤 Profile", callback_data="profile"),
            InlineKeyboardButton("💼 Wallet", callback_data="wallet"),
        ],
        [
            InlineKeyboardButton("🛒 Buy Agent", callback_data="buy_agent"),
            InlineKeyboardButton("📦 My Orders", callback_data="my_orders"),
            InlineKeyboardButton("📊 Statistics", callback_data="statistics"),
        ],
        [
            InlineKeyboardButton("💰 Withdraw", callback_data="withdraw"),
            InlineKeyboardButton("🎁 Bonus Info", callback_data="bonus"),
            InlineKeyboardButton("📞 Support", callback_data="support"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_profile_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton("✉️ Update Email", callback_data="update_email"),
            InlineKeyboardButton("🔙 Back to Home", callback_data="home"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_wallet_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton("📊 Statistics", callback_data="statistics"),
            InlineKeyboardButton("🔙 Back", callback_data="home"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_categories_keyboard(categories: list) -> InlineKeyboardMarkup:
    keyboard = []
    row = []
    for index, category in enumerate(categories):
        button = InlineKeyboardButton(
            text=f"{category['emoji']} {category['name']}",
            callback_data=f"cat_{category['id']}",
        )
        row.append(button)
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    keyboard.append(
        [InlineKeyboardButton("🔙 Back to Home", callback_data="home")]
    )
    return InlineKeyboardMarkup(keyboard)


def get_agents_keyboard(agents: list) -> InlineKeyboardMarkup:
    keyboard = []
    for agent in agents:
        keyboard.append(
            [
                InlineKeyboardButton(
                    text=f"{agent['name']} — ${agent['price']}",
                    callback_data=f"agent_{agent['id']}",
                )
            ]
        )
    keyboard.append(
        [InlineKeyboardButton("🔙 Back to Categories", callback_data="buy_agent")]
    )
    return InlineKeyboardMarkup(keyboard)


def get_agent_detail_keyboard(agent_id: int, category_id: int) -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton("✅ Buy Now", callback_data=f"buy_{agent_id}"),
        ],
        [
            InlineKeyboardButton("🔙 Back", callback_data=f"cat_{category_id}"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_payment_method_keyboard(agent_id: int) -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton(
                "💚 bKash", callback_data=f"pay_bKash_{agent_id}"
            ),
            InlineKeyboardButton(
                "🔴 Nagad", callback_data=f"pay_Nagad_{agent_id}"
            ),
        ],
        [
            InlineKeyboardButton(
                "💛 USDT TRC20", callback_data=f"pay_USDT_{agent_id}"
            ),
        ],
        [
            InlineKeyboardButton("🔙 Back", callback_data=f"agent_{agent_id}"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_orders_keyboard(orders: list) -> InlineKeyboardMarkup:
    keyboard = []
    for order in orders[:10]:
        label = (
            f"#{order['id'][:8]} | {order['agent_name']} | {order['status'].upper()}"
        )
        keyboard.append(
            [
                InlineKeyboardButton(
                    text=label,
                    callback_data=f"order_{order['id']}",
                )
            ]
        )
    keyboard.append(
        [InlineKeyboardButton("🔙 Home", callback_data="home")]
    )
    return InlineKeyboardMarkup(keyboard)


def get_order_detail_keyboard(order_id: str) -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton(
                "🔄 Refresh Status", callback_data=f"order_{order_id}"
            ),
        ],
        [
            InlineKeyboardButton("🔙 My Orders", callback_data="my_orders"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_admin_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton("📦 Pending Orders", callback_data="admin_orders"),
            InlineKeyboardButton(
                "💰 Pending Withdrawals", callback_data="admin_withdrawals"
            ),
        ],
        [
            InlineKeyboardButton("➕ Add Category", callback_data="admin_add_cat"),
            InlineKeyboardButton("➕ Add Agent", callback_data="admin_add_agent"),
        ],
        [
            InlineKeyboardButton("📊 Stats", callback_data="admin_stats"),
            InlineKeyboardButton("📢 Broadcast", callback_data="admin_broadcast"),
        ],
        [
            InlineKeyboardButton("🗑️ Delete Agent", callback_data="admin_delete_agent"),
            InlineKeyboardButton("👥 All Users Count", callback_data="admin_user_count"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_admin_order_keyboard(order_id: str) -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton(
                "✅ Verify", callback_data=f"aord_verified_{order_id}"
            ),
            InlineKeyboardButton(
                "⚙️ Mark Setup", callback_data=f"aord_setup_{order_id}"
            ),
        ],
        [
            InlineKeyboardButton(
                "🚀 Deliver", callback_data=f"aord_deliver_{order_id}"
            ),
            InlineKeyboardButton(
                "❌ Cancel", callback_data=f"aord_cancel_{order_id}"
            ),
        ],
        [
            InlineKeyboardButton("🔙 Back", callback_data="admin_orders"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_admin_withdraw_keyboard(withdrawal_id: str) -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton(
                "✅ Approve & Pay", callback_data=f"awit_approve_{withdrawal_id}"
            ),
            InlineKeyboardButton(
                "❌ Reject", callback_data=f"awit_reject_{withdrawal_id}"
            ),
        ],
        [
            InlineKeyboardButton("🔙 Back", callback_data="admin_withdrawals"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_back_to_home_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton("🏠 Home", callback_data="home"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_stats_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton("🔄 Refresh", callback_data="statistics"),
            InlineKeyboardButton("🏠 Home", callback_data="home"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)
