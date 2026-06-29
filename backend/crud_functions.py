from sqlalchemy import select, delete
from sqlalchemy.exc import SQLAlchemyError
from datetime import date
from backend.db_models import Product, Order
from backend.models import OrderCreate, ProductCreate
from sqlalchemy.orm import Session
from fastapi import HTTPException

def get_product_id_from_db(db: Session, id):
    """Retrieves a single product by its database ID."""
    if isinstance(id, int):
        stmt = select(Product).where(Product.product_id == id)
    else:
        stmt = select(Product).where(Product.product_id.in_(id))
    result = db.execute(stmt)
    # Using scalar_one_or_none matches the newer SQLAlchemy 2.0 execution standard
    return result.scalar_one_or_none()


def get_product_name_from_db(db: Session, name: str):
    """
    Performs a case-insensitive partial match search (%Like%) 
    to serve as a traditional fallback alongside your AI semantic search.
    """
    query_names = select(Product).where(Product.product_name.ilike(f"%{name}%"))
    result = db.execute(query_names)
    get_product_name = result.scalars().all()
    
    if not get_product_name:
       raise HTTPException(status_code=404, detail="Product name is not found")
       
    print(f"Found {len(get_product_name)} products matching raw keyword patterns") 
    return get_product_name
    
def create_product_in_db(db: Session, product: ProductCreate, embedding: list[float] = None):
    """Creates a new product entry in the database."""
    product_data = product.model_dump()
    db_product = Product(**product_data, product_embedding=embedding)
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    return db_product

def create_order_in_db(db: Session, order_data: OrderCreate):
    """
    Creates a new cart checkout order while monitoring 
    strict thread-safe inventory locks.
    """
    product = db.query(Product).filter(Product.product_id == order_data.product_id).with_for_update().first()
    #placing guardrails over Product quantity has to be greater than the orders items ordered enough in stock
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
        
    if product.product_stock < order_data.order_quantity:
        raise HTTPException(status_code=400, detail="Insufficient stock to fulfill this order")

    try:
        #Update stock and the create order here
        product.product_stock -= order_data.order_quantity
        new_order = Order(
            order_name=order_data.order_name,
            total_amount=order_data.total_amount,
            order_date=order_data.order_date,
            product_id=order_data.product_id,
            order_quantity=order_data.order_quantity,
            order_status="Pending" # Provided a fallback status string matching your model rules
        )  
        db.add(new_order)
        db.commit()
        db.refresh(new_order)
        return new_order
        
    except SQLAlchemyError as e:
        db.rollback()
        print(f"Database error creating order: {e}")
        raise HTTPException(
            status_code=500,
            detail="Error: Could not save order to database"
        )

def check_existing_product(db: Session, name: str, author: str):
    """Checks if a product with the same name and author already exists in the database."""
    return db.query(Product).filter(
        Product.product_name == name,
        Product.product_author == author
    ).first()

def get_order_status_db(db, id):
    """ 
    Retrieves the specific status tracking string of the order by its unique ID. 
    """
    stmt = select(Order.order_status).where(Order.order_id == id)
    result = db.execute(stmt)
    return result.first()

def drop_order_in_db(db, order_id):
    """Deletes an entire order record tracking history out of the persistence store."""
    delete_o = delete(Order).where(Order.order_id==order_id)
    db.execute(delete_o)
    db.commit()
    return True
    

def place_order_in_db(db: Session, product_id: int, quantity: int, order_name: str):
    """Alternate quick shortcut order entry point with internal cost calculations."""
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

    try:
        db.add(new_order)
        db.commit()
        db.refresh(new_order)
        return new_order
    except Exception as e:
        db.rollback() 
        raise e