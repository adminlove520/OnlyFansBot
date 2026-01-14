# Walkthrough - Migrate Bot To OF-Scraper Integration

We have successfully refactored the OnlyFans Bot to use **OF-Scraper** as its core data fetching engine. This eliminates the need to maintain complex, constantly changing request signature logic within the bot itself.

## Architecture Change

- **Before**: Bot tried to manually replicate OnlyFans' complex browser fingerprinting and signing logic. This was fragile.
- **After**: Bot uses a **Subprocess Adapter Pattern**.
    - The Main Bot (Python 3.10) calls a lightweight adapter script (`scripts/of_adapter.py`).
    - The Adapter runs in a separate, isolated Python 3.11 environment (`OF-Scraper/venv`).
    - The Adapter imports `OF-Scraper` as a library, reusing its battle-tested API handling.

## Changes Made

### 1. Adapter Script
Created `scripts/of_adapter.py`:
- Bridges the gap between the Bot and OF-Scraper.
- Mocks necessary command-line arguments for OF-Scraper.
- Exposes simple JSON commands: `profile` and `timeline`.

### 2. Bot Crawler Refactor
Modified `OnlyFans-Bot/crawlers/onlyfans.py`:
- **Removed** legacy signing logic.
- **Added** `fetch_via_adapter` method to execute the subprocess.
- **Updated** `fetch_creator_info` and `crawl_posts` to use the adapter.
- **Added** `_update_auth_file` to sync credentials with OF-Scraper.

## Verification

Ran `test_adapter_integration.py` which confirmed successful data fetching for profile and posts using the new adapter.

## Next Steps

1. **Restart the Bot**: The currently running bot process is using the old code. Restart it to switch to the new Adapter logic.
2. **Enjoy Stability**: The bot should now be as stable as OF-Scraper itself!
