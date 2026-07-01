import os
import time
import requests
import random
from datetime import datetime, timedelta
from dotenv import load_dotenv
from supabase import create_client, Client

# Load Environment Variables
load_dotenv()
SUPABASE_DATABASE = os.getenv("SUPABASE_DATABASE")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
NYT_API_KEY = os.getenv("NYT_API_KEY")

# Initialize Supabase
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Configuration
TARGET_GENRES = {"Horror", "Romance", "Historical Fiction", "Fiction", "Non-Fiction", "Autobiography"}
LISTS_TO_FETCH = ["hardcover-fiction", "trade-fiction-paperback", "hardcover-nonfiction"]

current_date = datetime.now()
weeks_to_go_back = 520 # Be aware: 520 weeks will take a long time to run! 

# Track ISBNs so we don't process the same book twice
seen_isbns = set() 
total_inserted = 0

print(f"Starting Historical Data Fetch: Going back {weeks_to_go_back} weeks...")

for week in range(weeks_to_go_back):
    date_str = current_date.strftime("%Y-%m-%d")
    print(f"\n--- Fetching data for week: {date_str} ---")

    for list_name in LISTS_TO_FETCH:
        nyt_url = f"https://api.nytimes.com/svc/books/v3/lists/{date_str}/{list_name}.json"
        nyt_response = requests.get(nyt_url, params={"api-key": NYT_API_KEY})
        
        if nyt_response.status_code != 200:
            print(f"Failed to fetch NYT list {list_name}. Status: {nyt_response.status_code}")
            continue
            
        nyt_data = nyt_response.json()
        books = nyt_data.get("results", {}).get("books", [])

        for book in books:
            isbn13 = book.get('primary_isbn13')

            # Skip if no ISBN or if we already processed this book
            if not isbn13 or isbn13 in seen_isbns:
                continue

            seen_isbns.add(isbn13) # Mark as seen

            # ------------------------------------------
            # STEP 2: Fetch Metadata from Open Library API
            # ------------------------------------------
            ol_url = f"https://openlibrary.org/api/books?bibkeys=ISBN:{isbn13}&jscmd=data&format=json"
            ol_response = requests.get(ol_url)
            
            if ol_response.status_code != 200:
                continue
                
            ol_data = ol_response.json()
            book_key = f"ISBN:{isbn13}"
            
            if book_key not in ol_data:
                continue
                
            book_metadata = ol_data[book_key]
            subjects_list = book_metadata.get("subjects", [])
            subject_names = [sub["name"] for sub in subjects_list]
            
            # ------------------------------------------
            # STEP 3: The Genre Filter
            # ------------------------------------------
            matched_genres = list(set(subject_names).intersection(TARGET_GENRES))
            if not matched_genres:
                continue 

            # Get the best description available (from NYT first, fallback to generic)
            description = book.get("description", "")
            final_desc = description if description else "A great read waiting to be discovered."
            
            # ------------------------------------------
            # STEP 4: The Merged Data Structure (From Script 2)
            # ------------------------------------------
            # Here we apply the exact naming convention and randomizers you requested
            final_book_data = {
                "product_name": book.get("title", "").title(),
                "product_author": book.get("author", ""),
                "description": final_desc,
                "product_price": round(random.uniform(9.99, 34.99), 2), # Random price between $10 and $35
                "product_stock": random.randint(10, 100) # Random stock between 10 and 100
            }
            
            # ------------------------------------------
            # STEP 5: Push to Supabase
            # ------------------------------------------
            try:
                # IMPORTANT: Ensure your Supabase table is named 'products' 
                # (matching your React and db_models.py setup)
                supabase.table("products").insert(final_book_data).execute()
                total_inserted += 1
                print(f"✅ Saved: {final_book_data['product_name']} (${final_book_data['product_price']})")
            except Exception as e:
                print(f"❌ Error saving {final_book_data['product_name']}: {e}")

        # Sleep to respect NYT rate limits
        time.sleep(12) 
        
    # Move back one week in time
    current_date -= timedelta(weeks=1)

print(f"\n🎉 Finished! Successfully curated and inserted {total_inserted} books into Supabase.")

