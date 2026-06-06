#!/usr/bin/env python3
"""
Example Telegram bot for testing BotPanel.
Replace BOT_TOKEN with your actual token.
Install: pip install pyTelegramBotAPI
"""
import os
import time
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")

if not BOT_TOKEN:
    logger.warning("BOT_TOKEN not set! Running in demo mode.")
    logger.info("Bot started in demo mode - set BOT_TOKEN env variable")
    count = 0
    while True:
        count += 1
        logger.info(f"[Demo] Bot heartbeat #{count}")
        time.sleep(10)
else:
    try:
        import telebot
        bot = telebot.TeleBot(BOT_TOKEN)

        @bot.message_handler(commands=['start', 'help'])
        def send_welcome(message):
            bot.reply_to(message, "🤖 Hello! I'm managed by BotPanel.")

        @bot.message_handler(func=lambda m: True)
        def echo_all(message):
            bot.reply_to(message, message.text)

        logger.info("Bot polling started...")
        bot.infinity_polling()
    except ImportError:
        logger.error("pyTelegramBotAPI not installed. Run: pip install pyTelegramBotAPI")
