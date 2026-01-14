# Walkthrough - OnlyFans Bot with OF-Scraper Integration

This project has been refactored to use **OF-Scraper** as its core engine via a Git Submodule. All components are self-contained within the `OnlyFans-Bot` repository.

## 📂 Project Structure

```
OnlyFans-Bot/              # Git Root Directory
├── bot.py                 # Entry point (Python 3.10)
├── crawlers/
│   └── onlyfans.py        # Modified to use OF-Adapter
├── OF-Scraper/            # Git Submodule
│   └── venv/              # (Ignored by Git)
├── scripts/               # Helper Scripts
│   ├── of_adapter.py      # The Bridge Script
│   ├── diagnose.py        # Diagnosis Tool
│   └── utils/             # Archived Scripts
├── .gitmodules            # Submodule Config
└── docs/                  # Documentation
```

## 🚀 Architecture

1. **Main Bot (Python 3.10)**: Runs `bot.py`. Handles Discord interaction and logic.
2. **Adapter (Python 3.11)**: `scripts/of_adapter.py`. A standalone script that imports `OF-Scraper` as a library.
3. **Integration**: When the Bot needs data, it spawns a subprocess:
   `[OF-Scraper/venv/python] scripts/of_adapter.py [command] [args]`

## 📦 Managing the Submodule

- **First Time Setup** (if cloning fresh):
  ```bash
  git submodule update --init --recursive
  ```
- **Updating OF-Scraper**:
  ```bash
  git submodule update --remote --merge
  ```

## ✅ Verification status

- **Profile Fetching**: Working (Verified with Sky Bri)
- **Timeline Fetching**: Working
- **Auth Sync**: Working

## 🛠️ How to Run
```powershell
python bot.py
```

### Self-Check
If you suspect issues, run the diagnosis script:
```powershell
python scripts/diagnose.py
```
