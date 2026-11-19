import datetime
from typing import Optional
from sqlmodel import SQLModel, Field


class User(SQLModel, table=True):
    __tablename__ = "users"

    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(unique=True, index=True)
    password: str                       # contient le HASH, jamais le mot de passe en clair
    is_admin: bool = Field(default=False)
    is_blocked: bool = Field(default=False)


class Product(SQLModel, table=True):
    __tablename__ = "products"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    price: float
    stock: int = Field(default=0)
    is_available: bool = Field(default=True)


class Menu(SQLModel, table=True):
    __tablename__ = "menus"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    price: float
    available_from: Optional[datetime.date] = Field(default=None)
    available_to: Optional[datetime.date] = Field(default=None)
    # les deux à None = menu permanent


class MenuProduct(SQLModel, table=True):
    __tablename__ = "menu_products"

    # clé primaire composée : le couple (menu_id, product_id) est unique
    menu_id: int = Field(foreign_key="menus.id", primary_key=True)
    product_id: int = Field(foreign_key="products.id", primary_key=True)
    quantity: int = Field(default=1)


class Order(SQLModel, table=True):
    __tablename__ = "orders"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id")
    pickup_date: datetime.date
    status: str = Field(default="pending")


class OrderItem(SQLModel, table=True):
    __tablename__ = "order_items"

    id: Optional[int] = Field(default=None, primary_key=True)
    order_id: int = Field(foreign_key="orders.id")
    product_id: Optional[int] = Field(default=None, foreign_key="products.id")
    menu_id: Optional[int] = Field(default=None, foreign_key="menus.id")
    quantity: int = Field(default=1)


class ClosingDay(SQLModel, table=True):
    __tablename__ = "closing_days"

    id: Optional[int] = Field(default=None, primary_key=True)
    date: datetime.date = Field(unique=True)