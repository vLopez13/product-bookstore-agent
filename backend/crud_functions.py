from sqlalchemy import select, delete
from sqlalchemy.exc import SQLAlchemyError
from datetime import date
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException

# Assuming these are your local imports
from backend.db_models import Product, Order
from backend.models import OrderCreate, ProductCreate


async def get_product_id_from_db(db: AsyncSession, id):
    """Retrieves a single product by its database ID."""
    if isinstance(id, int):
        stmt = select(Product).where(Product.product_id == id)
    else:
        stmt = select(Product).where(Product.product_id.in_(id))
        
    result = await db.execute(stmt)
    
    # Note: If passing a list of IDs, scalar_one_or_none() will throw an error 
    # if multiple products are found. Use result.scalars().all() if you expect multiple.
    return result.scalar_one_or_none()


async def get_product_name_from_db(db: AsyncSession, name: str):
    """
    Performs a case-insensitive partial match search (%Like%) 
    to serve as a traditional fallback alongside your AI semantic search.
    """
    query_names = select(Product).where(Product.product_name.ilike(f"%{name}%"))
    result = await db.execute(query_names)
    get_product_name = result.scalars().all()
    
    if not get_product_name:
       raise HTTPException(status_code=404, detail="Product name is not found")
       
    print(f"Found {len(get_product_name)} products matching raw keyword patterns") 
    return get_product_name
    

async def create_product_in_db(db: AsyncSession, product: ProductCreate, embedding: list[float] = None):
    """Creates a new product entry in the database."""
    product_data = product.model_dump()
    db_product = Product(**product_data, product_embedding=embedding)
    db.add(db_product)
    
    await db.commit()
    await db.refresh(db_product)
    
    return db_product


async def create_order_in_db(db: AsyncSession, order_data: OrderCreate):
    """
    Creates a new cart checkout order while monitoring 
    strict thread-safe inventory locks.
    """
    # Refactored from db.query() to select() for async with_for_update() support
    stmt = select(Product).where(Product.product_id == order_data.product_id).with_for_update()
    result = await db.execute(stmt)
    product = result.scalar_one_or_none()
    
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
        
    if product.product_stock < order_data.order_quantity:
        raise HTTPException(status_code=400, detail="Insufficient stock to fulfill this order")

    try:
        # Update stock and create order here
        product.product_stock -= order_data.order_quantity
        new_order = Order(
            order_name=order_data.order_name,
            total_amount=order_data.total_amount,
            order_date=order_data.order_date,
            product_id=order_data.product_id,
            order_quantity=order_data.order_quantity,
            order_status="Pending" 
        )  
        db.add(new_order)
        await db.commit()
        await db.refresh(new_order)
        return new_order
        
    except SQLAlchemyError as e:
        await db.rollback()
        print(f"Database error creating order: {e}")
        raise HTTPException(
            status_code=500,
            detail="Error: Could not save order to database"
        )


async def check_existing_product(db: AsyncSession, name: str, author: str):
    """Checks if a product with the same name and author already exists in the database."""
    # Refactored from db.query() to select()
    stmt = select(Product).where(
        Product.product_name == name,
        Product.product_author == author
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_order_status_db(db: AsyncSession, id):
    """ 
    Retrieves the specific status tracking string of the order by its unique ID. 
    """
    stmt = select(Order.order_status).where(Order.order_id == id)
    result = await db.execute(stmt)
    return result.first()


async def drop_order_in_db(db: AsyncSession, order_id):
    """Deletes an entire order record tracking history out of the persistence store."""
    delete_o = delete(Order).where(Order.order_id == order_id)
    await db.execute(delete_o)
    await db.commit()
    return True
    

async def place_order_in_db(db: AsyncSession, product_id: int, quantity: int, order_name: str):
    """Alternate quick shortcut order entry point with internal cost calculations."""
    stmt = select(Product).where(Product.product_id == product_id)
    result = await db.execute(stmt)
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
        product_id=product_id,
        order_name=order_name,
        order_quantity=quantity,
        total_amount=total_price,
        order_status="Confirmed",
        order_date=date.today()
    )

    try:
        db.add(new_order)
        await db.commit()
        await db.refresh(new_order)
        return new_order
    except Exception as e:
        await db.rollback() 
        raise e