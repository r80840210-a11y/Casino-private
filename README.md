# StarPlay Telegram Bot

Python + aiogram 3 bot with SQLite storage, designed to run as a Render Background Worker.

## Included
- User profile with Telegram ID, points balance, wins and losses
- Upgrade game using **non-purchasable, non-withdrawable game points**
- Promo codes with a limited number of activations
- Admin panel: add/remove admins, ban/unban, issue/remove points, promo creation, broadcast and basic stats
- Owner admin ID is `1780243264`
- Custom Telegram Bot API base URL setting

## Important
This project intentionally uses **game points only**. It does not process payments, accept deposits, or enable real-value withdrawals. Do not use it to take Telegram Stars or money as gambling stakes.

## Setup
1. Create a bot token with BotFather on the Telegram network your server supports.
2. Upload this project to a GitHub repository.
3. In Render, create a **Background Worker** from the repository.
4. Set environment variable `BOT_TOKEN` to your bot token.
5. `TELEGRAM_API_BASE` is prefilled in `render.yaml`; change it if your custom API server uses a different base URL.
6. Deploy. The bot starts with zero points; the owner can use `/admin` and issue points to users.

## Custom API server note
`TELEGRAM_API_BASE` must point to a compatible Telegram Bot API server base URL. If your endpoint is not a standard Bot API-compatible endpoint, bot requests will fail. Render's worker does not need an inbound web port, so no `PORT` setting is required.

## Admin commands
- `/admin` — open the admin panel
- Admin prompts guide you through each action.
- Admins can issue points only to users who have started the bot.

## Persistence
The included SQLite database is suitable for a simple test deployment. Render's local filesystem can be ephemeral; for persistent production data, attach a persistent disk or switch to PostgreSQL.
