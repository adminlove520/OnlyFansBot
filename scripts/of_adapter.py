import sys
import os
import json
import logging
import asyncio
import traceback
import argparse

# --- Configuration ---
OF_SCRAPER_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'OF-Scraper'))
# ---------------------

# Ensure we can import ofscraper
if OF_SCRAPER_PATH not in sys.path:
    sys.path.append(OF_SCRAPER_PATH)

# Setup logging - suppress stdout to keep JSON output clean
logging.basicConfig(level=logging.ERROR, stream=sys.stderr)

# Mock args needed by OF-Scraper
class MockArgs:
    def __init__(self):
        # Basic args
        self.config = None
        self.profile = "main_profile"
        self.log = "INFO"
        self.output = "LOW"
        self.username = "skybrixo" # Default, will be overridden
        self.action = "download"
        self.command = "download"
        
        # Filters
        self.filter = None
        self.neg_filter = None
        self.download_date = None
        self.download_sort = None
        self.text_filter = None
        self.text_type_filter = None
        self.before = None
        self.after = None
        
        # Binary options
        self.ffmpeg = None
        
        # Advanced options
        self.dynamic_rules = "digital"
        self.no_cache = False
        self.no_api_cache = False
        self.key_mode = "cdrm"
        self.backend = "aio"
        self.download_sems = 1
        self.download_limit = 0
        self.sd = None
        self.no_auto_resume = False
        self.metadata = None
        self.discord = None
        self.mediatype = None
        self.downloadbars = False
        self.infinite_loop_action_mode = False
        self.disable_auto_after = False
        self.discord_level = None
        self.console_output_level = "LOW"
        self.users_first = False

    def __getattr__(self, name):
        if name.startswith("__"):
            raise AttributeError(name)
        return None

# Initialize OF-Scraper environment
def setup_ofscraper():
    # Monkey patch logging trace
    def trace(self, message, *args, **kws):
        pass
    logging.Logger.trace = trace
    logging.Logger.traceback_ = trace

    try:
        import ofscraper.utils.args.globals as args_globals
        args_globals.args = MockArgs()
        
        from ofscraper.managers.manager import mainManager
        import ofscraper.managers.manager as manager
        manager.Manager = mainManager()
        
        return True
    except Exception as e:
        sys.stderr.write(f"Setup Error: {e}\n")
        traceback.print_exc(file=sys.stderr)
        return False

async def fetch_profile(username):
    from ofscraper.data.api.profile import scrape_profile
    # scrape_profile is synchronous wrapper
    return scrape_profile(username)

async def fetch_timeline(username, limit=10):
    from ofscraper.data.api.timeline import get_timeline_posts
    from ofscraper.data.api.profile import get_id
    from ofscraper.managers.manager import Manager
    
    # We need model_id for timeline
    model_id = get_id(username)
    if not model_id:
         raise Exception(f"Could not find model ID for {username}")
         
    # get_timeline_posts signature: (model_id, username, c=None, post_id=None)
    # It needs a session. Manager.session.get_ofsession() provides context manager
    
    posts = []
    async with Manager.session.aget_ofsession() as c:
        # Note: OF-Scraper's get_timeline_posts is a complex async generator/task runner.
        # It's designed to download ALL posts or based on filters.
        # We want just the latest ones.
        
        # We might need to tap into a lower level function if possible, 
        # but get_timeline_posts is the main entry.
        # It calls scrape_timeline_posts internally.
        
        # Let's try calling scrape_timeline_posts directly if possible for finer control,
        # OR just use get_timeline_posts and let it run (might be slow if it tries to get everything).
        
        # Actually, let's try the high level one first, it respects 'after' args if we set them,
        # but we didn't set 'after'.
        
        # For simplicity in this adapter, let's try to get just the first page using the lower level function
        # referenced in timeline.py: scrape_timeline_posts
        
        from ofscraper.data.api.timeline import scrape_timeline_posts
        
        # timestamp=None means latest
        result_posts, _ = await scrape_timeline_posts(c, model_id, timestamp=None, offset=False)
        posts = result_posts
        
    return posts[:limit]

async def run_adapter(command, username, limit=10):
    if not setup_ofscraper():
        return {"error": "Setup failed"}
        
    try:
        if command == "profile":
            data = await fetch_profile(username)
            return {"success": True, "data": data}
        
        elif command == "timeline":
            data = await fetch_timeline(username, limit)
            return {"success": True, "data": data}
            
        else:
            return {"error": f"Unknown command: {command}"}
            
    except Exception as e:
        traceback.print_exc(file=sys.stderr)
        return {"error": str(e)}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["profile", "timeline"])
    parser.add_argument("username")
    parser.add_argument("--limit", type=int, default=10)
    args = parser.parse_args()
    
    # Update global args username mock
    import ofscraper.utils.args.globals as args_globals
    if args_globals.args:
        args_globals.args.username = args.username

    # Run async loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    result = loop.run_until_complete(run_adapter(args.command, args.username, args.limit))
    
    # Print JSON result to stdout
    print(json.dumps(result))

if __name__ == "__main__":
    main()
