from datetime import date
from pydantic import BaseModel
from typing import Optional


class Product(BaseModel):
    
    product_id: int
    product_name: str
    product_author: str
    product_stock: int
    product_price: float


class ProductCreate(Product):
    pass

class ProductResponse(ProductCreate):
    product_id: int
    
    class Config:
        from_attributes = True
        orm_mode = True

class ProductUpdate(BaseModel):
    product_name: Optional[str] = None
    product_author: Optional[str] = None
    product_stock: Optional[int] = None
    product_price: Optional[float] = None

class Order(BaseModel):
    
    order_id: int
    customer_id: int
    order_name: str
    order_quantity: int
    product_id: int
    order_datetime: datetime
    order_date: date
    total_amount: float
    order_status: str

class OrderCreate(Order):
    product_id: int
    order_quantity: int 
    customer_id: int

class OrderResponse(OrderCreate):
    order_id: int
    total_amount: float
    order_date: datetime
    product_author: str  # We will add 

    class Config:
        from_attributes = True
        orm_mode = True
