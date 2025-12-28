from typing import Any
import uvicorn
import os
from datetime import datetime
from fastapi import FastAPI, Depends, HTTPException
from dotenv import load_dotenv
from sqlalchemy.orm import Session
from database import get_db, Base, engine
from database_models.db_models import Product, Order
from models import ProductCreate, ProductUpdate, OrderCreate
from models import ProductCreate, ProductUpdate
from crud_functions import create_product_in_db, drop_order_in_db, get_product_name_from_db, create_order_in_db, place_order_in_db

load_dotenv()
app = FastAPI(title = "Bookstore")

@app.get("/")
def read_root():
    return {"hello":"world"}

@app.get("/allproducts/{product_name}")
def get_name_of_product(product_name: str, db:Session = Depends(get_db)):

    all_possible_names = get_product_name_from_db(db, product_name)

    return all_possible_names

@app.get("/products/{product_id}")
def get_product(product_id: int, db:Session = Depends(get_db)):

    product = db.query(Product).filter(Product.product_id == product_id).first()

    if not product:
        raise HTTPException(status_code = 404, detail= "Product not found")

    return product
@app.delete("/deleteorder/{order_id}")
def delete_the_order(order_id:int, db:Session=Depends(get_db)):
    drop_the_order = drop_order_in_db(db=db, id=order_id)
    return drop_the_order

@app.post("/products/")
def create_product(product: ProductCreate, db:Session = Depends(get_db)) -> Any:
    print(f"My agent Baby Bookstore is creating the product:{product.product_name}")

    created_product = create_product_in_db(db=db,
                         id= product.product_id, 
                         name = product.product_name, 
                         author=product.product_author,
                         stock = product.product_stock,
                         price = product.product_price
                         )
    return { "status": "success",
        "action": "create_product_in_db",
        "message": "OK",
        "data": {
            "name": created_product.name,
            "id": created_product.id
        }
    }
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
#we can create an order POST here creates a ORDER and we can see it. 
@app.post("/createorder/")
def create_order_receipt(order: OrderCreate, db: Session = Depends(get_db)):
    new_order = create_order_in_db(db=db, order_data=order)
    try:
        return {
            "order status": "successful order",
            "order id": new_order.order_id,
            "order price": float(order.order_price),
            "order date": str(order.order_date)
        }
    except (AttributeError, ValueError, TypeError) as e:
        return {
            "order status": "error",
            "error message": str(e),
            "order data": order.model_dump() if hasattr(order, 'model_dump') else str(order)
        }
     
@app.post("/orders/")
def create_order(order: OrderCreate, db: Session = Depends(get_db)): 
    return place_order_in_db(
        db=db, 
        product_id=order.product_id, 
        quantity=order.order_quantity, 
        order_name=order.order_name
    )


if __name__ == "__main__":  
    uvicorn.run(app, host="0.0.0.0", port=8000)
