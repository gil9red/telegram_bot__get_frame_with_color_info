#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = 'ipetrash'


from io import BytesIO
import os
import time
from typing import Optional
import re

# pip install python-telegram-bot
from telegram import Update, ChatAction
from telegram.ext import Updater, MessageHandler, CommandHandler, Filters, CallbackContext
from telegram.ext.dispatcher import run_async

import config
from common import get_logger, log_func, catch_error

from third_party.draw_frame_with_color_info import get_frame_with_color_info, QColor


pattern_rgb = re.compile(r'rgb (\d+),? (\d+),? (\d+)', flags=re.IGNORECASE)
pattern_hex = re.compile(r'hex ([\da-f]+),? ([\da-f]+),? ([\da-f]+)', flags=re.IGNORECASE)
pattern_hsv = re.compile(r'hsv (\d+),? (\d+),? (\d+)', flags=re.IGNORECASE)
pattern_hsl = re.compile(r'hsl (\d+),? (\d+),? (\d+)', flags=re.IGNORECASE)
pattern_cmyk = re.compile(r'cmyk (\d+),? (\d+),? (\d+),? (\d+)', flags=re.IGNORECASE)

PATTERNS = [
    (pattern_rgb, int, QColor.fromRgb),
    (pattern_hex, lambda x: int(x, 16), QColor.fromRgb),
    (pattern_hsv, int, QColor.fromHsv),
    (pattern_hsl, int, QColor.fromHsl),
    (pattern_cmyk, int, QColor.fromCmyk),
]


def parse_color(color_name: str) -> Optional[QColor]:
    if QColor.isValidColor(color_name):
        return QColor(color_name)

    for pattern, params_func, from_func in PATTERNS:
        m = pattern.search(color_name)
        if not m:
            continue

        color = from_func(*map(params_func, m.groups()))
        return color if color.isValid() else None

    return


log = get_logger(__file__)


@run_async
@catch_error(log)
@log_func(log)
def on_start(update: Update, context: CallbackContext):
    message = update.message or update.edited_message
    message.reply_text('''\
    Write the color, for examples: 
    - darkCyan
    - #007396
    - rgb 255 100 200 
    - hex ff a0 ff
    - hsv 359 50 100
    - hsl 0 100 50
    - cmyk 79 40 0 66
    ''')


@run_async
@catch_error(log)
@log_func(log)
def on_request(update: Update, context: CallbackContext):
    message = update.message or update.edited_message

    color = parse_color(message.text)
    if not color:
        message.reply_text('Not valid color!')
        return

    data = get_frame_with_color_info(color, rounded=False, as_bytes=True)

    context.bot.send_chat_action(
        chat_id=message.chat_id, action=ChatAction.UPLOAD_PHOTO
    )

    message.reply_photo(
        BytesIO(data), reply_to_message_id=message.message_id
    )


@catch_error(log)
def on_error(update: Update, context: CallbackContext):
    log.exception('Error: %s\nUpdate: %s', context.error, update)
    if update:
        message = update.message or update.edited_message
        message.reply_text(config.ERROR_TEXT)


def main():
    cpu_count = os.cpu_count()
    workers = cpu_count
    log.debug('System: CPU_COUNT=%s, WORKERS=%s', cpu_count, workers)

    log.debug('Start')

    # Create the EventHandler and pass it your bot's token.
    updater = Updater(
        config.TOKEN,
        workers=workers,
        use_context=True
    )

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    dp.add_handler(CommandHandler('start', on_start))
    dp.add_handler(MessageHandler(Filters.text, on_request))

    # Handle all errors
    dp.add_error_handler(on_error)

    # Start the Bot
    updater.start_polling()

    # Run the bot until the you presses Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()

    log.debug('Finish')


if __name__ == '__main__':
    while True:
        try:
            main()
        except:
            log.exception('')

            timeout = 15
            log.info(f'Restarting the bot after {timeout} seconds')
            time.sleep(timeout)
