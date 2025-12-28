from datetime import date, datetime
from decimal import Decimal
from pydantic import BaseModel, Field
from typing import Optional


class Product(BaseModel):
    
    product_id: int
    product_name: str
    product_author: str
    product_stock: int
    product_price:Decimal = Field(..., max_digits=10, decimal_places=2)


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
    order_name: str
    order_date: date
    customer_id :int
    product_id: int

class OrderCreate(Order):
    order_quantity: int
    order_status: str
    customer_id: int

class OrderResponse(OrderCreate):
    order_date: date
    order_price: Decimal = Field(..., max_digits=10, decimal_places=2)

    class Config:
        from_attributes = True
        orm_mode = True
