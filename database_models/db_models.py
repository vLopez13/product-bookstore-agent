from sqlalchemy import ForeignKey, Column, Integer, String, Float, Date, DateTime
from datetime import date
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import Mapped, mapped_column
from database import Base

class Product(Base):
    __tablename__ =  "_Books_"
    product_id: Mapped[int] = mapped_column(primary_key = True)
    product_name: Mapped[str] = mapped_column(String(100))
    product_author: Mapped[str] = mapped_column(String(100))
    product_price: Mapped[float] = mapped_column(Float)
    product_stock: Mapped[int] = mapped_column(Integer)

class Order(Base): 
    __tablename__ = "_Orders_"
    order_id: Mapped[int] = mapped_column(primary_key = True)
    product_id: Mapped[int] = mapped_column(Integer, ForeignKey("products.product_id"))
    order_name: Mapped[str] = mapped_column(String(100))
    order_date: Mapped[date] = mapped_column(Date, default=date.today)
    total_amount: Mapped[float]= mapped_column(Float)
    order_quantity: Mapped[int]= mapped_column(Integer)
    order_status: Mapped[str] = mapped_column(String(100))
