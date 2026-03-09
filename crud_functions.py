from sqlalchemy import select, delete
from sqlalchemy.exc import SQLAlchemyError
from datetime import date
from database_models.db_models import Product, Order
from models import OrderCreate, ProductCreate
from sqlalchemy.orm import Session
from fastapi import HTTPException

def get_product_id_from_db(db, id):
#this is to retrieve the id from the database to use very soon
    stmt = select(Product).where(Product.product_id.in_([id] if isinstance(id, int) else id))
    result = db.execute(stmt)
    get_product = result.scalar().first()
    return get_product


def get_product_name_from_db(db, name):
 #this is for funsies and I want to try product name from db and any more or like %sLike
    query_names = select(Product).where(Product.product_name==name)
    result = db.execute(query_names)
    get_product_name = result.scalars().all()
    if not get_product_name:
       raise HTTPException(status_code=404, detail="Product name is not found")
    print(f"Found {len(get_product_name)} products") 
    return get_product_name
    

def create_product_in_db(db: Session, product: ProductCreate):
    db_product = Product(**product.model_dump())
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    return db_product


def create_order_in_db(db, order_data: OrderCreate):
    #This is to create and update the product and prevent new bugs 
    product = db.query(Product).filter(Product.product_id == order_data.product_id).with_for_update().first()
    #placing guardrails over Product quantity has to be greater than the orders items ordered enough in stock
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
        
    if product.product_stock < order_data.order_quantity:
        raise HTTPException(status_code=400, detail="Insufficient stock to fulfill this order")

    
    
    try:#Update stock and the create order here
        product.product_stock-=order_data.order_quantity
        new_order = Order(
            order_name=order_data.order_name,
            total_amount=order_data.total_amount,
            order_date=order_data.order_date,
            customer_id=order_data.customer_id,
            product_id=order_data.product_id,
            order_quantity=order_data.order_quantity
        )
        
        db.add(new_order)
        db.commit()
        db.refresh(new_order)
        return new_order
        
    except SQLAlchemyError as e:
        db.rollback()  # Undo any changes
        print(f"Database error creating order: {e}")
        raise HTTPException(
            status_code=500,
            detail="Error: Could not save order to database"
        )

def get_order_status_db(db, id):
    
    stmt = select(Order.order_status).where(Order.order_id == id).first()
    result = db.execute(stmt)
    return result

def drop_order_in_db(db, order_id):
         delete_o = delete(Order).where(Order.order_id==order_id)
         db.execute(delete_o)
         db.commit()
    

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
     db.commit()
     db.refresh(db_order)
    
     return new_order
    except Exception as e:
      db.rollback() 
      raise e