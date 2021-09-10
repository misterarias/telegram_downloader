# Telegram-Downloader

Downloads all messages from given Telegram channel IDs or channel name
pattern. It honours already downloaded files, and it should resume partial
downloads but it does not.

Telegram API credentials can be read from environment variables or passed in as arguments.

## usage

```bash
downloader [-h] [-p DESTINATION_PATH] [-v] [-b BATCH_SIZE] [--api-id API_ID]
                  [--api-hash API_HASH] (-i GROUP_IDS [GROUP_IDS ...] | -g GROUP_PATTERN)

```


## optional arguments

*  -h, --help            show this help message and exit
*  -p DESTINATION_PATH, --destination-path DESTINATION_PATH File output path
*  -v, --verbose         Display verbose outputs
*  -b BATCH_SIZE, --batch-size BATCH_SIZE  Number of download tasks to run simultaneously.
*  --api-id API_ID
*  --api-hash API_HASH
*  -i GROUP_IDS [GROUP_IDS ...], --group-ids GROUP_IDS [GROUP_IDS ...]   List of telegram group IDs
*  -g GROUP_PATTERN, --group-pattern GROUP_PATTERN  Group prefix to look for.
