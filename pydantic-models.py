from pydantic import BaseModel, ConfigDict, Field, EmailStr
from datetime import datetime
from typing import List, Optional

# this the author for each product=book
class AuthorBase(BaseModel):
    author_name: str = Field(..., min_length=1, max_length=100)

# Create model: Fields required when creating a new author
class AuthorCreate(AuthorBase):
    pass

# Read model: Fields returned when reading through and see an author name 
class Author(AuthorBase):
    author_id: int
    
    model_config = ConfigDict(from_attributes=True)


# --- Product Models ---
# Base model: Common product fields
class ProductBase(BaseModel):
    product_title: str = Field(..., min_length=1, max_length=255)
    product_price: float = Field(..., gt=0, description="Price must be greater than zero")
    product_stock: int = Field(..., ge=0, description="Stock level cannot be negative")

# Create model: Fields required to create a new product
# We link the author by its ID
class ProductCreate(ProductBase):
    author_id: int

# Read model: the product model is int and in the author a nested model
class Product(ProductBase):
    product_id: int
    product_author: Author  # Nested Author model
    model_config = ConfigDict(from_attributes=True)


# --- User Models ---
class UserBase(BaseModel):
    user_name: str = Field(..., min_length=3, max_length=50)
    email: EmailStr

# Create model: Includes password for creation
class UserCreate(UserBase):
    password: str = Field(..., min_length=8)

# Read model: Excludes sensitive info like password
class User(UserBase):
    user_id: int
    
    model_config = ConfigDict(from_attributes=True)


# --- Order Models ---
# These are a bit more complex as an Order contains OrderItems

# OrderItem: Represents a product and its quantity within an order
class OrderItemBase(BaseModel):
    product_id: int
    quantity: int = Field(..., gt=0, description="Quantity must be at least 1")

class OrderItemCreate(OrderItemBase):
    pass

# Read model for an item in an order
class OrderItem(BaseModel):
    quantity: int
    product: Product  
    
    model_config = ConfigDict(from_attributes=True)


# Base model: Fields common to all Order schemas
class OrderBase(BaseModel):
    user_id: int
    status: str = Field("pending", description="Order status (e.g., pending, shipped, cancelled)")

# Create model: What the user sends to create an order
class OrderCreate(BaseModel):
    user_id: int
    items: List[OrderItemCreate]

# Read model: The full order details returned from the API
class Order(OrderBase):
    order_id: int
    created_at: datetime
    items: List[OrderItem]
    
    model_config = ConfigDict(from_attributes=True)