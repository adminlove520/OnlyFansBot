# Update Notes

## [2026-01-14] OF-Scraper Integration & Refactor

### Major Changes
- **OF-Scraper Adapter**: Replaced custom signature generation logic with a subprocess adapter that calls `OF-Scraper` as a library. This ensures long-term stability by relying on OF-Scraper's maintained authentication mechanism.
- **Python 3.11 Requirement**: The adapter requires a Python 3.11 virtual environment (`OF-Scraper/venv`), while the main bot remains on Python 3.10.
- **Directory Restructure**:
  - Moved tests to `tests/`.
  - Archived utility scripts to `scripts/utils/`.
  - Moved main bot code to `OnlyFans-Bot/`.

### Removed Features
- **Legacy Signing**: Removed `reverse_sign.py`, `manual_sign.py`, and related `OnlyFansCrawler` methods.
- **Tests**: Deleted obsolete tests (`test_auto_sign.py`, `test_api.py`).

### New Files
- `scripts/of_adapter.py`: Core logic for bridging Bot and OF-Scraper.
- `tests/test_adapter_integration.py`: Integration test for the adapter.
- `README.md`: New project root documentation.

### How to Upgrade
1. Ensure `OF-Scraper` submodule is initialized and its venv is set up.
2. Restart the bot (`python OnlyFans-Bot/bot.py`).
