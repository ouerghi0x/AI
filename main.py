import threading
import asyncio
from dotenv import load_dotenv

from services.fastapp import FastApp
from services.ret_insert_docs import ParentRetriever

# Load environment variables early
load_dotenv()

# Fix event loop policy for compatibility
asyncio.set_event_loop_policy(asyncio.DefaultEventLoopPolicy())
retriever=None

async def bootstrap():
     global retriever
     retriever = ParentRetriever()
     await retriever.add_documents_to_parent_retriever()

if __name__ == "__main__":
     # Run async bootstrap before starting the app
     asyncio.run(bootstrap())

     # Start FastAPI server in a background thread
     app = FastApp(retriever)
     app_thread = threading.Thread(target=app.run, daemon=True)
     app_thread.start()

     # Optional: Keep main thread alive if needed
     try:
          while True:
               pass  # or use time.sleep(1)
     except KeyboardInterrupt:
          print("Shutting down...")



 





