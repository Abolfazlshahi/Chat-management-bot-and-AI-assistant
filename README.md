# pythash bot  -------> [راهنمای فارسی ربات](https://github.com/Abolfazlshahi/Chat-management-bot-and-AI-assistant/blob/main/README_FA.md)

A full-featured Telegram group management bot with AI Q&A, a credit system,
fully configurable AI providers, and a built-in donation section. Almost everything
is configured at runtime via bot commands — only BOT_TOKEN and OWNER_ID live in .env.

## Features
- AI answers (mention in groups, or DM). FAQ has priority and costs no credit.
- Pluggable AI provider (default: FreeModel / freemodel.dev, OpenAI-compatible).
- Credit system: per-message or per-token cost, all adjustable from the bot.
- Moderation: warn/ban/kick/mute, locks, word filters, link policy + whitelist.
- Anti-spam and join verification (OFF by default, toggleable per group).
- Donations: crypto wallets and/or rial (IRR), configured from the bot.
- Tools: polls, reminders, stats, broadcast, audit-log channel.
- # 🚀 English deployment guide (VPS, step-by-step for absolute beginners)

- 💸 Financial Support
Financial support is optional. If you want to support ongoing development, use one of these wallet addresses:

|💰 Network	|🔐 Address|
| --- | --- |
|TON	|UQDfjVk2UdpiMg-bsxqoLa0O_icuaF20D-wWJgIJwK1Ha2Ul|
|USDT Tron (TRC20)|	TR8ibZGKutPKoDm5nMbHFwGPFBuMKwjG6j|
|USDT BNB Smart Chain (BEP20)	|0x8c45d6bae8a5a572b2a776779fe0bcae3d3f9107|

<aside>
📘

This guide assumes you have **never used a server before**. Follow it line by line and copy/paste exactly. Words in `code style` must be typed as-is.

</aside>

## 0. What you need before starting

- **Bot token** — open Telegram, search **@BotFather**, send `/newbot`, follow the steps, and copy the token (looks like `123456:ABC-DEF...`).
- **Your numeric ID** (the owner) — open **@userinfobot** in Telegram and press Start; it replies with your `Id` (a number). That is your `OWNER_ID`.
- **A FreeModel API key** — sign up at https://freemodel.dev/ and copy your API key (optional; you can also set any other provider later with `/set_api`).
- **A VPS** — a small cloud server. Buy the cheapest plan and choose **Ubuntu 22.04** as the operating system. After purchase you receive an **IP address**, a **username** (usually `root`), and a **password**.

## 1. Connect to your server (SSH)

**Windows:** Open the **PowerShell** app (Start menu → type "PowerShell"). Then type, replacing the IP with yours:

```bash
ssh root@YOUR_SERVER_IP
```

**Mac:** Open the **Terminal** app (Cmd+Space → type "Terminal") and run the same command.

Type `yes` if asked, then enter the password (the screen stays blank while typing the password — that is normal). You are now “inside” the server.

## 2. Install the required software

Copy and paste these lines one by one (press Enter after each):

```bash
apt update && apt upgrade -y
apt install -y python3 python3-pip python3-venv git
```

## 3. Download the bot

If you have the project on GitHub:

```bash
git clone https://github.com/your-username/pythash-bot.git
cd pythash-bot
```

If you do NOT have GitHub, create the folder and files by hand:

```bash
mkdir pythash-bot && cd pythash-bot
```

Then create each file with `nano filename` (e.g. `nano app/main.py`), paste the code, press **Ctrl+O** then **Enter** to save, and **Ctrl+X** to exit. Recreate the same folder/file structure shown at the top of this page.

## 4. Create the Python environment and install dependencies

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## 5. Create the .env file

```bash
nano .env
```

Paste the following (replace the two values with yours), then Ctrl+O, Enter, Ctrl+X:

```bash
BOT_TOKEN=PASTE_YOUR_TOKEN_HERE
OWNER_ID=PASTE_YOUR_NUMERIC_ID
```

That is all you need. Everything else (AI key, credits, donations, moderation) is set later **inside the bot** with commands.

## 6. Test run

```bash
python -m app.main
```

Open Telegram, send `/start` to your bot. If it replies, it works! Press **Ctrl+C** to stop the test.

Then, inside the bot, set your AI key, e.g. with `/set_api` (FreeModel example is on this page), and try `/activate_api` and `/test_api`.

## 7. Keep it running forever (systemd service)

So the bot stays online even after you close the terminal or reboot the server:

```bash
nano /etc/systemd/system/pythash.service
```

Paste this (fix the path if your folder differs):

```
[Unit]
Description=pythash bot
After=network.target

[Service]
WorkingDirectory=/root/pythash-bot
ExecStart=/root/pythash-bot/venv/bin/python -m app.main
Restart=always

[Install]
WantedBy=multi-user.target
```

Save (Ctrl+O, Enter, Ctrl+X), then enable and start it:

```bash
systemctl daemon-reload
systemctl enable pythash
systemctl start pythash
```

## 8. Useful commands

```bash
systemctl status pythash      # is it running?
systemctl restart pythash     # restart after changes
systemctl stop pythash        # stop the bot
journalctl -u pythash -f      # live logs (Ctrl+C to exit)
```

## 9. Updating the bot later

```bash
cd /root/pythash-bot
git pull                      # if you used git
source venv/bin/activate
pip install -r requirements.txt
systemctl restart pythash
```

## 10. Common problems

| Symptom | Fix |
| --- | --- |
| Bot doesn't reply | `systemctl status pythash` and `journalctl -u pythash -f` to read the error |
| `ModuleNotFoundError` | Activate venv and re-run `pip install -r requirements.txt` |
| `Unauthorized` | Wrong `BOT_TOKEN` in `.env` |
| Owner commands rejected | Wrong `OWNER_ID` (must be your numeric ID from @userinfobot) |
| AI returns an error | Set/activate an API: `/set_api`, `/activate_api`, then `/test_api` |

<aside>
✅

Done! Your pythash bot now runs 24/7 on your server. Configure the rest (AI, credits, donations, moderation) directly in Telegram with the commands listed in the README. 🎉

</aside>
