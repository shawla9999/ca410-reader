#!/usr/bin/env python3
import logging
import os
import sys

from app import Application


def _app_data_dir() -> str:
    if sys.platform == 'win32':
        base = os.environ.get('APPDATA', os.path.expanduser('~'))
        return os.path.join(base, 'ca410_reader')
    return os.path.expanduser('~/.ca410_reader')


def setup_logging() -> None:
    log_dir = _app_data_dir()
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, 'ca410_reader.log')

    formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(name)s: %(message)s')

    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)


def main() -> None:
    setup_logging()
    logger = logging.getLogger(__name__)
    try:
        app = Application()
        app.run()
    except Exception:
        logger.exception('Unhandled exception')
        sys.exit(1)


if __name__ == '__main__':
    main()
