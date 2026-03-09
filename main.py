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
from crud_functions import create_product_in_db, get_product_name_from_db, create_order_in_db, drop_order_in_db, get_order_status_db

load_dotenv()
app = FastAPI(title = "Bookstore")
#app will load and run
@app.get("/")
def read_root():
    return {"hello":"world"}


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




@app.post("/products/")
def create_product(product: ProductCreate, db:Session = Depends(get_db)) -> Any:
    print(f"My agent Bookstore is creating the product:{product.product_name}")

    created_product = create_product_in_db(db = db, product =product)
    return { 
        "status": "success",
        "action": "create_product_in_db",
        "message": "OK",
        "data": {
            "id": created_product.product_id, 
            "name": created_product.product_name
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


@app.post("/createorder/")
def create_order(order_data: OrderCreate, db: Session = Depends(get_db)):
    return create_order_in_db(db=db, order_data=order_data)

if __name__ == "__main__":  
    uvicorn.run(app, host="0.0.0.0", port=8000)
