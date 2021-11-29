#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = 'ipetrash'


import os
import time
import re

from typing import Optional
from random import randint
from io import BytesIO

# pip install python-telegram-bot
from telegram import Update, ChatAction
from telegram.ext import Updater, MessageHandler, CommandHandler, Filters, CallbackContext, Defaults

import config
from common import get_logger, log_func, catch_error

from third_party.draw_frame_with_color_info import get_frame_with_color_info, QColor


pattern_rgb = re.compile(r'rgb (\d+),? (\d+),? (\d+)', flags=re.IGNORECASE)
pattern_hex = re.compile(r'hex ([\da-f]+),? ([\da-f]+),? ([\da-f]+)', flags=re.IGNORECASE)
pattern_hex_2 = re.compile(r'hex ([\da-f]{2})([\da-f]{2})([\da-f]{2})', flags=re.IGNORECASE)
pattern_hsv = re.compile(r'hsv (\d+),? (\d+),? (\d+)', flags=re.IGNORECASE)
pattern_hsl = re.compile(r'hsl (\d+),? (\d+),? (\d+)', flags=re.IGNORECASE)
pattern_cmyk = re.compile(r'cmyk (\d+),? (\d+),? (\d+),? (\d+)', flags=re.IGNORECASE)

PATTERNS = [
    (pattern_rgb, int, QColor.fromRgb),
    (pattern_hex, lambda x: int(x, 16), QColor.fromRgb),
    (pattern_hex_2, lambda x: int(x, 16), QColor.fromRgb),
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


def reply_color(color: QColor, update: Update, context: CallbackContext):
    message = update.effective_message

    if not color:
        message.reply_text('Not valid color!')
        return

    data = get_frame_with_color_info(color, rounded=False, as_bytes=True)
    bytes_io = BytesIO(data)

    r, g, b, _ = color.getRgb()
    log.debug(f'Reply color (RGB): {r} {g} {b}')

    context.bot.send_chat_action(
        chat_id=message.chat_id, action=ChatAction.UPLOAD_PHOTO
    )

    message.reply_photo(bytes_io, quote=True)


def reply_help(update: Update):
    update.effective_message.reply_text('''\
Write the color, for examples: 
    - darkCyan
    - #007396
    - rgb 255 100 200 
    - hex ff a0 ff
    - hsv 359 50 100
    - hsl 0 100 50
    - cmyk 79 40 0 66

Supported commands:
    - /help
    - /random
    ''')


@catch_error(log)
@log_func(log)
def on_start(update: Update, context: CallbackContext):
    reply_help(update)


@catch_error(log)
@log_func(log)
def on_help(update: Update, context: CallbackContext):
    reply_help(update)


@catch_error(log)
@log_func(log)
def on_request(update: Update, context: CallbackContext):
    color = parse_color(update.effective_message.text)
    reply_color(color, update, context)


@catch_error(log)
@log_func(log)
def on_random(update: Update, context: CallbackContext):
    r, g, b = (randint(0, 255) for _ in range(3))
    color = QColor.fromRgb(r, g, b)
    reply_color(color, update, context)


@catch_error(log)
def on_error(update: Update, context: CallbackContext):
    log.error('Error: %s\nUpdate: %s', context.error, update, exc_info=context.error)
    if update:
        update.effective_message.reply_text(config.ERROR_TEXT)


def main():
    log.debug('Start')

    cpu_count = os.cpu_count()
    workers = cpu_count
    log.debug(f'System: CPU_COUNT={cpu_count}, WORKERS={workers}')

    updater = Updater(
        config.TOKEN,
        workers=workers,
        defaults=Defaults(run_async=True),
    )
    bot = updater.bot
    log.debug(f'Bot name {bot.first_name!r} ({bot.name})')

    dp = updater.dispatcher

    dp.add_handler(CommandHandler('start', on_start))
    dp.add_handler(CommandHandler('help', on_help))
    dp.add_handler(CommandHandler('random', on_random))
    dp.add_handler(MessageHandler(Filters.text, on_request))

    dp.add_error_handler(on_error)

    updater.start_polling()
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
