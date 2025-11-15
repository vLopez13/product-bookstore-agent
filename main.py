import psycopg
import os
from fastapi import FastAPI
from dotenv import load_dotenv
import pandas as pd
from collections import defaultdict
from typing import List, Dict, Any
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from surprise import Dataset, Reader
from surprise import SVD 

load_dotenv()

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")
try:
    # Ensure the connection string is loaded
    conn_str = os.environ["DB_CONN_STR"]
except KeyError:
    # This is a critical error for a database app
    print("FATAL ERROR: DB_CONN_STR environment variable not set. Application cannot run.")

# Define a single function for database connection and error handling
def execute_db_query(sql_query: str, fetch_all: bool = True) -> List[Any] | Dict[str, str]:
    """Helper function to execute SQL queries."""
    if not conn_str:
         return {"error": "Database configuration missing."}
         
    try:
        with psycopg.connect(conn_str) as conn:
            with conn.cursor() as cur:
                cur.execute(sql_query)
                if fetch_all:
                    return cur.fetchall()
                # Use conn.commit() here if it were an INSERT/UPDATE
                return []
    except psycopg.Error as e:
        # Log the specific error for debugging
        print(f"Database Error: {e}")
        return {"error": f"Database error: {e}"}

# 2. Define a URL (an "endpoint")
@app.get("/products-under-5")
def get_products_under_5():
    """Fetches all products with a price less than $5.00."""
    products_list = []
    
    # Using a list comprehension for a cleaner query construction is often safer.
    result = execute_db_query("SELECT product_id, title, price, stock_quantity FROM products WHERE price < 5.00")

    if isinstance(result, dict) and "error" in result:
        return result

    for record in result:
        products_list.append({
            "product_id": record[0],
            "title": record[1],
            "price": record[2],
            "stock_quantity": record[3]
        })

    # 4. Return the data
    return {"products": products_list}

@app.get("/", response_class=HTMLResponse)
def read_html_front_page():
    try:
        with open("index.html", "r") as f:
            return f.read()
    except FileNotFoundError:
        return "<html><body><h1>Error</h1><p>index.html not found.</p></body></html>"

@app.get("/api/recommendations/{user_id}")
def get_recommendations(user_id: int):
    ratings_data = []
    all_product_ids = set()
    products_rated_by_user = set()

    try:
        with psycopg.connect(conn_str) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT user_id, product_id, rating FROM user_ratings")
                for record in cur.fetchall():
                    ratings_data.append(record)
                    if record[0] == user_id:
                        products_rated_by_user.add(record[1])

            with conn.cursor() as cur:
                cur.execute("SELECT product_id FROM products")
                for record in cur.fetchall():
                    all_product_ids.add(record[0])

    except psycopg.Error as e:
        return {"error": f"Database error: {e}"}

    if not ratings_data:
        return {"message": "No ratings data available to build recommendations."}

    ratings_df = pd.DataFrame(ratings_data, columns=['userID', 'itemID', 'rating'])
    reader = Reader(rating_scale=(1, 5))
    data = Dataset.load_from_df(ratings_df, reader)

    trainset = data.build_full_trainset()
    algo = SVD()
    algo.fit(trainset)

    products_to_predict = all_product_ids - products_rated_by_user
    predictions = []
    for product_id in products_to_predict:
        est_rating = algo.predict(uid=user_id, iid=product_id).est
        predictions.append( (product_id, est_rating) )

    predictions.sort(key=lambda x: x[1], reverse=True)
    top_3_product_ids = [prod_id for (prod_id, rating) in predictions[:3]]
    
    return {
        "user_id": user_id,
        "recommendations": top_3_product_ids
    }