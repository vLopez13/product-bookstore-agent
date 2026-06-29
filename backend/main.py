from typing import Any
import uvicorn
import os
import json
import asyncio
from datetime import datetime, timedelta
from fastapi import FastAPI, Depends, HTTPException, Body, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from dotenv import load_dotenv
from sqlalchemy import text
from sqlalchemy.orm import Session
from backend.database import get_db, Base, engine
from backend.db_models import Product, Order
from backend.models import ProductCreate, ProductUpdate, OrderCreate, AgentQuery, ProductResponse, OrderResponse
from backend.crud_functions import create_product_in_db, get_product_name_from_db, create_order_in_db, drop_order_in_db, get_order_status_db, check_existing_product
from httpx import AsyncClient
from supabase import create_client, Client
import random

load_dotenv()
app = FastAPI(title="Bookstore")

async def get_embedding(text: str) -> list[float]:
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    if not gemini_api_key:
        print("⚠️ GEMINI_API_KEY not configured. Falling back to mock embedding for local testing.")
        import hashlib
        h = hashlib.sha256(text.encode('utf-8')).hexdigest()
        seed = int(h, 16) % (2**32)
        rng = random.Random(seed)
        return [rng.uniform(-0.1, 0.1) for _ in range(768)]

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-embedding-001:embedContent?key={gemini_api_key}"
    payload = {
        "model": "models/gemini-embedding-001",
        "content": {
            "parts": [{
                "text": text
            }]
        },
        "outputDimensionality": 768
    }
    async with AsyncClient() as client:
        try:
            response = await client.post(url, json=payload, timeout=10.0)
            if response.status_code != 200:
                raise HTTPException(status_code=500, detail=f"Gemini API error: {response.status_code} - {response.text}")

            return response.json()["embedding"]["values"]
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to reach Gemini embedding provider: {str(e)}")
        
@app.post("/orders/", response_model=OrderResponse)
def create_order_endpoint(order: OrderCreate, db: Session = Depends(get_db)):
    try:
        # Save the initial order to your database
        db_order = create_order_in_db(db=db, order_data=order)
        db_order.order_status = "ORDER_CREATED"
        db.commit()
        db.refresh(db_order)
        return db_order
    except Exception as e:
        print(f"Internal Database Error: {e}")
        raise HTTPException(
            status_code=400, 
            detail="We could not process your order at this time."
        )

# --- Semantic Search ---
@app.post("/products/ai-search")
async def semantic_search_products_endpoint(
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
        SELECT product_id, product_name, description, product_price, (embedding <=> CAST(:vector AS vector)) AS distance
        FROM products
        ORDER BY distance ASC
        LIMIT :limit;
    """
    result = db.execute(
        text(raw_query), 
        {"vector": str(query_vector), "limit": limit}
    ).fetchall()
    ai_matches = [
        {
            "product_id": row[0],
            "product_name": row[1],
            "description": row[2],
            "price": float(row[3]),
            "match_confidence": round(1 - row[4], 4) if row[4] is not None else 0.0
        }
        for row in result
    ]
    return {"query": query, "results": ai_matches}

@app.get("/")
def read_root():
    return {"hello": "world"}

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
@app.get("/products/search/{product_name}", response_model=list[ProductResponse])
def search_products_by_name(product_name: str, db: Session = Depends(get_db)):
    all_possible_names = get_product_name_from_db(db=db, product_name=product_name)
    if not all_possible_names:
         raise HTTPException(status_code=404, detail="No products found in database matching that name")

    return all_possible_names

#grab GET product id from products list
@app.get("/products/{product_id}", response_model=ProductResponse)
def get_product(product_id: int, db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.product_id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

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
def delete_the_order(order_id: int, db: Session=Depends(get_db)):
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
def create_order_duplicate(order_data: OrderCreate, db: Session = Depends(get_db)):
    return create_order_in_db(db=db, order_data=order_data)

# --- Vapi Webhook Integration ---
@app.post("/vapi/webhook")
async def vapi_webhook(request: Request, db: Session = Depends(get_db)):
    """
    This endpoint handles incoming tool calls from a Vapi voice agent.
    """
    payload = await request.json()
    message = payload.get("message", {})

    # Vapi sends different types of messages; we only care about tool calls here.
    if message.get("type") == "tool-calls":
        tool_calls = message.get("toolCalls", [])
        tool_results = []

        for tool_call in tool_calls:
            function_name = tool_call.get("function", {}).get("name")
            arguments = tool_call.get("function", {}).get("arguments", {})
            call_id = tool_call.get("id")

            # Route 1: Checking Order Status
            if function_name == "get_order_status":
                order_id = arguments.get("order_id")
                try:
                    db_order = get_order_status_db(db, order_id=order_id)
                    if db_order:
                        result = {"order_id": order_id, "status": db_order.order_status}
                    else:
                        result = {"error": "Order not found. Please double-check the ID."}
                except Exception as e:
                    result = {"error": str(e)}

                tool_results.append({
                    "toolCallId": call_id,
                    "result": result
                })

            # Route 2: Semantic Book Search
            elif function_name == "semantic_search_products":
                query = arguments.get("query")
                limit = arguments.get("limit", 3)
                try:
                    # Re-using your existing embedding logic
                    query_vector = await get_embedding(query)
                    raw_query = """
                        SELECT product_name, description, product_price 
                        FROM products
                        ORDER BY (embedding <=> CAST(:vector AS vector)) ASC
                        LIMIT :limit;
                    """
                    result = db.execute(
                        text(raw_query), 
                        {"vector": str(query_vector), "limit": limit}
                    ).fetchall()
                    
                    matches = [{"title": row[0], "price": float(row[2])} for row in result]
                    result_data = {"matches": matches}
                except Exception as e:
                    result_data = {"error": "Search failed"}

                tool_results.append({
                    "toolCallId": call_id,
                    "result": result_data
                })

            # Fallback for unmapped tools
            else:
                tool_results.append({
                    "toolCallId": call_id,
                    "result": {"error": f"Tool '{function_name}' not implemented on backend."}
                })

        # Return the results back to the Vapi agent so it can speak them
        return {"results": tool_results}

    return {"message": "Event received, but not a tool call."}

if __name__ == "__main__":  
    uvicorn.run(app, host="0.0.0.0", port=8000)