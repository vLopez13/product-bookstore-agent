from sqlalchemy import select
from datetime import date
from database_models.db_models import Product, Order 
from sqlalchemy.orm import Session
from fastapi import HTTPException

def get_product_id_from_db(db, id):

    stmt = select(Product).where(Product.product_id.in_([id] if isinstance(id, int) else id))
    result = db.execute(stmt)
    return result.scalar().first()


def get_product_name_from_db(db, name):

    stmt = select(Product).where(Product.product_name.in_(name))
    result = db.execute(stmt)
    get_product = result.one_or_none()
    if not get_product:
      raise HTTPException(status_code=404, detail="get.Product is not found in db")
    
    return get_product
    

def create_product_in_db(db, id, name, author, stock, price):
  
    new_product = Product(product_id = id,
            product_name = name,
            product_author = author,
            product_stock = stock,
            product_price = price)
    
    db.add(new_product)
    db.commit()

def get_order_status_db(db, id):
    
    stmt = select(Order.order_status).where(Order.order_id == id).first()
    result = db.execute(stmt)
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

    # 5. COMMIT (The Transaction)
    # We add the order to the session
    db_order = db.add(new_order)
    
    try:
        # This saves BOTH the new order AND the updated product stock at the exact same time
        db.commit()
        db.refresh(db_order)
        return new_order
    except Exception as e:
        db.rollback() # If anything fails, undo changes to both tables
        raise e