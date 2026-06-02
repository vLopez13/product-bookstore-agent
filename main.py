from typing import Any
import uvicorn
import os
import json
import asyncio
from datetime import datetime
from fastapi import FastAPI, Depends, HTTPException, Body
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from dotenv import load_dotenv
from sqlalchemy.orm import Session
from database import get_db, Base, engine
from database_models.db_models import Product, Order
from models import ProductCreate, ProductUpdate, OrderCreate, AgentQuery
from crud_functions import create_product_in_db, get_product_name_from_db, create_order_in_db, drop_order_in_db, get_order_status_db
from httpx import AsyncClient
from startAgentStream import start_agent_stream

load_dotenv()
app = FastAPI(title = "Bookstore")
# open ai we will have helper function to build to ground up 
async def get_embedding(text: str)-> list[float]:
    # this is where we will call open ai embedding function to get the vector representation of the text
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        raise HTTPException(status_code=500, detail="OpenAI API key is not configured")

    url = "https://api.openai.com/v1/embeddings"
    headers = {
        "Authorization": f"Bearer {openai_api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "input": text,
        "model": "text-embedding-3-small"
    }
    async with AsyncClient() as client:
        try:
            response = await client.post(url, headers=headers, json=payload, timeout=10.0)
            if response.status_code != 200:
                raise HTTPException(status_code=500, detail=f"OpenAI API error: {response.status_code} - {response.text}")

            return response.json()["data"][0]["embedding"]
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to reach embedding provider: {str(e)}")
        
# --- New AI Power Feature: Semantic Search ---
@app.post("/products/ai-search")
async def semantic_search_products(
    query: str = Body(..., embed=True), 
    limit: int = 5, 
    db: Session = Depends(get_db)
):
    """
    Searches bookstore items based on concepts/meaning instead of raw keywords.
    E.g., "A dark thriller about cyber warfare"
    """
    query_vector = await get_embedding(query)
    raw_query = """
        SELECT product_id, product_name, description, price, (embedding <=> :vector::vector) AS distance
        FROM products
        ORDER BY distance ASC
        LIMIT :limit;
    """
    result = db.execute(
        raw_query, 
        {"vector": str(query_vector), "limit": limit}
    ).fetchall()
    ai_matches = [
        {
            "product_id": row[0],
            "product_name": row[1],
            "description": row[2],
            "price": float(row[3]),
            "match_confidence": round(1 - row[4], 4)
        }
        for row in result
    ]
    return {"query": query, "results": ai_matches}

@app.get("/")
def read_root():
    return {"hello":"world"}

# this is AI Stream for visibility into the agent's thought process and tool usage as it handles requests
@app.post("/products/ai-search-stream")
async def ai_search_stream(payload: AgentQuery):
    async def agent_thought_generator():
        try:
            # Step 1: Agent receives the intent
            yield f"data: {json.dumps({'status': 'thinking', 'message': 'Analyzing bookstore inventory for: ' + payload.query})}\n\n"
            await asyncio.sleep(1) # Simulating agent thinking/LLM latency

            # Step 2: Agent decides to use a database tool
            yield f"data: {json.dumps({'status': 'tool_call', 'tool': 'database.py -> search_books', 'message': 'Querying vector database for semantic matches...'})}\n\n"
            await asyncio.sleep(1.5)

            # Step 3: Agent processes tool output and builds final answer
            yield f"data: {json.dumps({'status': 'generating', 'message': 'Formulating personal recommendations...'})}\n\n"
            await asyncio.sleep(1)

            # Step 4: Stream the actual text blocks (like OpenAI stream=True chunks)
            chunks = ["Here are ", "the best books ", "matching your request: ", "1. AI Foundations ", "2. Python Agents."]
            for chunk in chunks:
                yield f"data: {json.dumps({'status': 'text', 'chunk': chunk})}\n\n"
                await asyncio.sleep(0.3)

            # Step 5: Close stream
            yield "data: [DONE]\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'status': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(agent_thought_generator(), media_type="text/event-stream")
#search names in products list (GET)
@app.get("/products/search/{product_name}")
def search_products_by_name(product_name: str, db: Session = Depends(get_db)):
    all_possible_names = get_product_name_from_db(db=db, product_name=product_name)
    if not all_possible_names:
         raise HTTPException(status_code=404, detail="No products found in database matching that name")

    return all_possible_names

#grab GET product id from products list
@app.get("/products/{product_id}")
def get_product(product_id: int, db:Session = Depends(get_db)):

    product = db.query(Product).filter(Product.product_id == product_id).first()

    if not product:
        raise HTTPException(status_code = 404, detail= "Product not found")

    return product

@app.post("/products/")
async def create_product(product: ProductCreate, db: Session = Depends(get_db)) -> Any:
    print(f"Checking wallet guardrails for product: {product.product_name}")

    # 1. Look up if this book is already in PostgreSQL
    existing_entry = check_existing_product(db, name=product.product_name, author=product.product_author)

    if existing_entry:
        # If it exists and already has its vector, stop right here! Cost = $0.00
        if existing_entry.product_embedding is not None:
            return { 
                "status": "cached",
                "action": "skipped_openai_api_call",
                "message": "Product and vector already exist. Wallet protected!",
                "data": {
                    "id": existing_entry.product_id, 
                    "name": existing_entry.product_name
                }
            }
        
        # If the book text is there but missing a vector, generate it once
        print("Product exists but lacks an AI vector. Generating embedding...")
        ai_context = f"Title: {product.product_name}. Author: {product.product_author}."
        embedding_vector = await get_embedding(ai_context)
        
        existing_entry.product_embedding = embedding_vector
        db.commit()
        db.refresh(existing_entry)
        
        return {
            "status": "updated",
            "action": "added_missing_embedding",
            "data": {"id": existing_entry.product_id, "name": existing_entry.product_name}
        }
    print("Brand new product detected. Requesting token embedding...")
    ai_context = f"Title: {product.product_name}. Author: {product.product_author}."
    embedding_vector = await get_embedding(ai_context)

    created_product = create_product_in_db(db=db, product=product, embedding=embedding_vector)
    
    return { 
        "status": "success",
        "action": "create_product_with_embedding",
        "message": "OK",
        "data": {
            "id": created_product.product_id, 
            "name": created_product.product_name
        }
    }

#order GET retrieval see all status 
@app.get("/orders/{order_id}/status")
def get_order_status(order_id: int, db: Session = Depends(get_db)):
    db_order = get_order_status_db(db, order_id=order_id)

    if db_order is None:
        raise HTTPException(status_code=404, detail="Order not found")
    return {"order_id": db_order.order_id, "status": db_order.order_status}

#deletes all order under that ID (delete)
@app.delete("/orders/{order_id}")
def delete_the_order(order_id:int, db:Session=Depends(get_db)):
    delete_order = drop_order_in_db(db=db, order_id=order_id)
    if not delete_order:
        raise HTTPException(status_code=404, detail=f"Order {order_id} not found")
        
    return {"message": f"Order {order_id} deleted successfully"}

@app.put("/products/{product_id}")
def put_product(product_id: int, product: ProductUpdate, db: Session = Depends(get_db)):
    product_stmt = db.query(Product).filter(Product.product_id == product_id).first()
    if not product_stmt:
        raise HTTPException(status_code=404, detail="Product not found")
    
    update_data = product.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(product_stmt, key, value)
    
    db.add(product_stmt)
    db.commit()
    db.refresh(product_stmt)


@app.post("/createorder/")
def create_order(order_data: OrderCreate, db: Session = Depends(get_db)):
    return create_order_in_db(db=db, order_data=order_data)

if __name__ == "__main__":  
    uvicorn.run(app, host="0.0.0.0", port=8000)
