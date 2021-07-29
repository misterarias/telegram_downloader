#!/usr/bin/env python3
"""Download files from telegram channels."""
import argparse
import asyncio
import logging
import os
import telethon
import time
import sys

from typing import List
from telethon import TelegramClient


def mb(x):
    return x / (1024 * 1024)


async def _download(message, destination):

    start_time = time.time()

    await message.download_media(file=destination)
    media_size = message.media.document.size
    total_time = time.time() - start_time
    logging.info(
        f'Downloaded "{message.file.name}" in {total_time:.3f}s [{mb(media_size)/total_time:.3f} MB/s].'
    )
    return media_size


async def _get_media_from_group_id(client, group_id):
    messages = []
    async for message in client.iter_messages(group_id):
        if message.file is None or message.file.name is None:
            continue
        messages.append(message)
    return messages


def get_client(api_id, api_hash):
    return TelegramClient("session_name", api_id, api_hash)


def is_already_downloaded(message, destination):
    if os.path.exists(destination):
        local_size = os.stat(destination).st_size
        media_size = message.media.document.size
        if local_size == media_size:
            logging.warning(f"{destination} is already downloaded OK, not resuming.")
            return True

    return False


def configure_logging(verbose: int):
    logging_format = "[%(asctime)s] %(levelname)s - %(name)s - %(message)s"
    logging.basicConfig(
        stream=sys.stderr, format=logging_format, level=logging.WARNING - verbose * 10
    )
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    logging.getLogger("telethon").setLevel(logging.WARNING)


def parse_args():
    parser = argparse.ArgumentParser(
        prog="downloader",
        description="""
Downloads all messages from given Telegram channel IDs or channel name pattern.
It honours already downloaded files, and it should resume partial downloads but it does not.

\n
Telegram API credentials can be read from environment variables or passed in as arguments. Get them from <url/to/place>.
        """,
    )
    parser.add_argument(
        "-p", "--destination-path", default="media", type=str, help="File output path"
    )
    parser.add_argument(
        "-v", "--verbose", action="count", default=0, help="Display verbose outputs"
    )
    parser.add_argument(
        "-b",
        "--batch-size",
        default=3,
        type=int,
        help="Number of download tasks to run simultaneously.",
    )
    parser.add_argument(
        "--api-id", required=True, default=os.environ.get("TELEGRAM_APP_API_ID")
    )
    parser.add_argument(
        "--api-has", required=True, default=os.environ.get("TELEGRAM_APP_API_HASH")
    )
    inputs = parser.add_mutually_exclusive_group(required=True)
    inputs.add_argument(
        "-i", "--group-ids", nargs="+", type=int, help="List of telegram group IDs"
    )
    inputs.add_argument("-g", "--group-pattern", help="Group prefix to look for.")

    args = parser.parse_args()

    os.makedirs(args.destination_path, exist_ok=True)
    return args


async def get_group_info(client, id_list: list, group_pattern: str) -> List:
    group_info = []
    async for dialog in client.iter_dialogs():
        if (id_list and dialog.id in id_list) or (
            group_pattern and group_pattern.lower() in dialog.name.lower()
        ):
            group_info.append({"id": dialog.id, "name": dialog.name})
    return group_info


def should_download(message, destination_path: str) -> bool:
    if message.file is None or message.file.name is None:
        return False

    destination = os.path.join(destination_path, message.file.name)
    if is_already_downloaded(message, destination):
        return False

    return True


async def process_message(message, destination_path: str):
    destination = os.path.join(destination_path, message.file.name)
    logging.info(f'Downloading "{message.file.name}" to "{destination_path}" ...')
    try:
        return await _download(message, destination)
    except telethon.errors.rpcerrorlist.FileReferenceExpiredError as fre:
        logging.error(f"Error while downloading {destination}: {fre}")
        return 0


async def get_messages(client, group_id, destination) -> List:
    return [
        message
        async for message in client.iter_messages(group_id)
        if should_download(message, destination)
    ]


async def get_valid_messages(client, group_ids, group_pattern, destination) -> List:
    groups = await get_group_info(client, group_ids, group_pattern)
    logging.debug(f"Argument(s) correspond to group(s): {groups}")
    valid_messages = []
    for group in groups:
        logging.info(f'Getting messages from group {group["name"]}')
        valid_group_messages = await get_messages(client, group["id"], destination)

        logging.info(f"Found {len(valid_group_messages)} messages eligible to download")
        valid_messages.extend(valid_group_messages)

    return valid_messages


async def process_messages(valid_messages, batch_size, destination):
    if len(valid_messages) == 0:
        logging.warning("No messages to download")
        return

    task_groups = [
        [process_message(m, destination) for m in valid_messages[i : i + batch_size]]
        for i in range(0, len(valid_messages), batch_size)
    ]
    for i, tasks in enumerate(task_groups):
        logging.info(
            f"Downloading {batch_size} messages from batch {i+1}/{len(task_groups)}"
        )
        start_time = time.time()
        results = await asyncio.gather(*tasks)
        batch_time = time.time() - start_time

        speed = mb(sum(results)) / batch_time
        logging.info(
            f"Batch finished in {batch_time:.3f}s @ {speed:.3}MB/s "
            f"(avg {speed / batch_size:.3f}MB/s per file)"
        )


async def main():
    """Async main."""
    args = parse_args()
    configure_logging(args.verbose)
    logging.info(f"Will download/resume files from {args.destination_path}")

    async with get_client(args.api_id, args.api_hash) as client:
        valid_messages = await get_valid_messages(
            client, args.group_ids, args.group_pattern, args.destination_path
        )
        await process_messages(valid_messages, args.batch_size, args.destination_path)


asyncio.run(main())
