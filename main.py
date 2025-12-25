from typing import Any
import uvicorn
import os
from datetime import datetime
from fastapi import FastAPI, Depends, HTTPException
from dotenv import load_dotenv
from sqlalchemy.orm import Session, relationship
from database_models.database import get_db
from database_models.db_models import Base, Product, Order
from models import ProductCreate, ProductUpdate, OrderCreate
from models import ProductCreate, ProductUpdate
from crud_functions import create_product_in_db, get_product_name_from_db, place_order_in_db

load_dotenv()
app = FastAPI(title = "Bookstore API")

@app.get("/")
def read_root():
    return {"hello":"world"}


@app.get("/products/{product_id}")
def get_product(product_id: int, db:Session = Depends(get_db)):

    product = db.query(Product).filter(Product.product_id == product_id).first()

    if not product:
        raise HTTPException(status_code = 404, detail= "Product not found")

    return product

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
    
@app.post("/orders/")
def create_order(order: OrderCreate, db: Session = Depends(get_db)): 
    return place_order_in_db(
        db=db, 
        product_id=Order.product_id, 
        quantity=Order.order_quantity, 
        order_name=Order.order_name
    )


if __name__ == "__main__":  
    uvicorn.run(app, host="0.0.0.0", port=8000)
