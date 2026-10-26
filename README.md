# 🎰 Telegram Casino Bot

Бот-казино с Telegram Stars. Апгрейд, профиль, промокоды, админ-панель.

## 🚀 Деплой на Render

1. **Создай бота** у [@BotFather](https://t.me/BotFather), получи токен

2. **Залей код на GitHub**:
   ```bash
   git init
   git add .
   git commit -m "Casino bot"
   git remote add origin https://github.com/ТВОЙ_НИК/ТВОЙ_РЕПО.git
   git push -u origin main
   ```

3. **На Render.com**:
   - New → Background Worker
   - Connect GitHub repo
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `python main.py`
   - Add Environment Variable: `BOT_TOKEN` = твой токен
   - Deploy!

## ⚙️ Локальный запуск

```bash
pip install -r requirements.txt
export BOT_TOKEN="твой_токен"
python main.py
```

## 👑 Админ-панель

Главный админ ID: `1780243264` (автоматически)

Команды в боте: `/admin`

## 🎮 Функции

- 🎰 Апгрейд звезд (шанс победы ~35%)
- 💰 Профиль со статистикой
- 💳 Пополнение через @v1nk_molik
- 💸 Вывод звезд (мин. сумма настраивается)
- 🎁 Промокоды
- 👑 Админ-панель (выдача/забор звезд, бан, рассылка)
