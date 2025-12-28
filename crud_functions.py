from sqlalchemy import select
from datetime import date
from database_models.db_models import Product, Order
from models import OrderCreate
from sqlalchemy.orm import Session
from fastapi import HTTPException

def get_product_id_from_db(db, id):

    stmt = select(Product).where(Product.product_id.in_([id] if isinstance(id, int) else id))
    result = db.execute(stmt)
    return result.scalar().first()


def get_product_name_from_db(db, name):
 #to ==tomato or the shin or the shining %like%
    query_names = select(Product).where(Product.product_name==name)
    result = db.execute(query_names)
    products = result.scalars().all()
    if not products:
       raise HTTPException(status_code=404, detail="Product name is not found")
    print(f"Found {len(products)} products") 
    return products
    

def create_product_in_db(db, id, name, author, stock, price):
  
    new_product = Product(product_id = id,
            product_name = name,
            product_author = author,
            product_stock = stock,
            product_price = price)
    
    db.add(new_product)
    db.commit()
    #Im creating a order in for API to call the function create_order_in_db
def create_order_in_db(db: Session, order_data: OrderCreate):
        new_order = Order(order_name=order_data.order_name,
        total_amount=order_data.order_price,
        order_date=order_data.order_date,
        customer_id=order_data.customer_id,
        product_id=order_data.product_id,
        order_quantity=order_data.order_quantity
        )
        db.add(new_order)
        db.commit()
        db.refresh(new_order)
        return new_order

def get_order_status_db(db, id):
    
    stmt = select(Order.order_status).where(Order.order_id == id).first()
    result = db.execute(stmt)
    return (result)
#we want to delete the order once the user confirms yes lets delete. then this function is brought.
def drop_order_in_db(db:Session, order_id: int):
    stmt = select(Order.order_id).where(Order.order_id==id).first()
    result = drop(stmt)
    return (result)

def place_order_in_db(db: Session, product_id: int, quantity: int, order_name: str):
    
    stmt = select(Product).where(Product.product_id == product_id)
    result = db.execute(stmt)
    product = result.scalar_one_or_none()

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    if product.product_stock < quantity:
        raise HTTPException(
            status_code=400, 
            detail=f"Out of stock. Only {product.product_stock} available.")
    
    product.product_stock -= quantity

    total_price = product.product_price * quantity
    
    new_order = Order(
        product_id = product_id,
        order_name = order_name,
        order_quantity = quantity,
        total_amount = total_price,
        order_status = "Confirmed",
        order_date = date.today()
    )

    db_order = db.add(new_order)
    
    try:
        # This saves BOTH the new order AND the updated product stock at the exact same time
        db.commit()
        db.refresh(db_order)
        return new_order
    except Exception as e:
        db.rollback() 
        raise e