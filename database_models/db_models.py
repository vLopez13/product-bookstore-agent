from sqlalchemy import ForeignKey, Column, Integer, String, Numeric, Date, DateTime
from datetime import date
from decimal import Decimal
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database import Base

class Product(Base):
    __tablename__ =  "products" #products
    product_id: Mapped[int] = mapped_column(primary_key = True)
    product_name: Mapped[str] = mapped_column(String(100))
    product_author: Mapped[str] = mapped_column(String(100))
    product_price: Mapped[Decimal] = mapped_column(Numeric(precision=10, scale=2))
    product_stock: Mapped[int] = mapped_column(Integer)

    order_item: Mapped[list["Order"]] = relationship(back_populates="product_item")
class Order(Base): 
    __tablename__ = "orders"
    order_id: Mapped[int] = mapped_column(primary_key = True)
    product_id: Mapped[int] = mapped_column(Integer, ForeignKey("products.product_id"))
    order_name: Mapped[str] = mapped_column(String(100))
    order_date: Mapped[date] = mapped_column(Date, default=date.today)
    total_amount: Mapped[Decimal]= mapped_column(Numeric(precision=10, scale=2))
    order_quantity: Mapped[int]= mapped_column(Integer)
    order_status: Mapped[str] = mapped_column(String(100))

    product_item: Mapped["Product"] = relationship(back_populates="order_item")