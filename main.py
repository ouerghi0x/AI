import threading
import asyncio
from dotenv import load_dotenv
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import time

from load_postgres_data import load_postgres_data_dbs
from services.fastapp import FastApp
from services.ret_insert_docs import ParentRetriever

# Load environment variables early
load_dotenv()

# Fix event loop policy for compatibility
asyncio.set_event_loop_policy(asyncio.DefaultEventLoopPolicy())

retriever = None

async def bootstrap():
     """Initializes the retriever and loads data."""
     global retriever
     print("Running daily bootstrap...")
     retriever = ParentRetriever()
     # Corrected line: removed await if load_postgres_data_dbs is not an async function
     fine =await load_postgres_data_dbs()
     if fine:
          await retriever.add_documents_to_parent_retriever()
     print("Daily bootstrap completed.")

# The new async main function
async def main():
     global retriever
     # Run bootstrap immediately to initialize the application
     await bootstrap()

     # Initialize and configure the scheduler
     scheduler = AsyncIOScheduler()
     # Schedule the bootstrap function to run daily at a specific time (e.g., 2 AM)
     scheduler.add_job(bootstrap, 'cron', hour=2)
     #scheduler.add_job(bootstrap, 'interval', minutes=1)
     # Start the scheduler
     scheduler.start()

     # Start FastAPI server in a separate thread
     app = FastApp(retriever)
     app_thread = threading.Thread(target=app.run, daemon=True)
     app_thread.start()

     # Keep the main async loop running indefinitely
     try:
          while True:
               await asyncio.sleep(1)
     except (KeyboardInterrupt, SystemExit):
          print("Shutting down gracefully...")
          scheduler.shutdown()

if __name__ == "__main__":
     # Run the main async function to start the entire application
     asyncio.run(main())
