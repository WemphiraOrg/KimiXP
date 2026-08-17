# KimiXP - Discord Bot
# Copyright (C) 2026 BrunoDevPe
#
# This file is part of KimiXP.
#
# KimiXP is free software licensed under the GNU General Public License v3.0.
# See the LICENSE file in the root directory for more information.

import json
import os
import logging
from logging.handlers import RotatingFileHandler
from typing import Any, Dict

logger = logging.getLogger("KimiBot")


def setup_logging(debug: bool = False) -> logging.Logger:
    """Configura el sistema de logs con consola y archivo rotativo."""
    level = logging.DEBUG if debug else logging.INFO

    formatter = logging.Formatter(
        "%(asctime)s | %(name)s | %(levelname)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)

    os.makedirs("logs", exist_ok=True)
    file_handler = RotatingFileHandler(
        "logs/bot.log",
        maxBytes=5 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)

    logging.getLogger("discord").setLevel(logging.WARNING)
    logging.getLogger("discord.http").setLevel(logging.WARNING)

    logger.info("Sistema de logs inicializado (debug=%s).", debug)
    return logger