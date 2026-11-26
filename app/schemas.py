from typing import Optional
from sqlmodel import SQLModel, Field
import datetime
from pydantic import model_validator
from enum import Enum


# Products 

class ProductCreate(SQLModel):
    name: str = Field(min_length=1)
    price: float = Field(gt=0)
    stock: int = Field(default=0, ge=0)
    is_available: bool = True

class ProductUpdate(SQLModel):
    # tout est optionnel : on n'envoie que ce qu'on veut modifier
    name: Optional[str] = Field(default=None, min_length=1)
    price: Optional[float] = Field(default=None, gt=0)
    stock: Optional[int] = Field(default=None, ge=0)
    is_available: Optional[bool] = None

class ProductRead(SQLModel):
    id: int
    name: str
    price: float
    stock: int
    is_available: bool
    
# closing Days

class ClosingDayCreate(SQLModel):
    date: datetime.date

class ClosingDayRead(SQLModel):
    id: int
    date: datetime.date
    
    
# Menus 

class MenuProductIn(SQLModel):
    product_id: int
    quantity: int = Field(default=1, gt=0)

class MenuProductRead(SQLModel):
    product_id: int
    name: str
    price: float
    quantity: int

def _check_menu_rules(menu):
    if menu.available_from and menu.available_to and menu.available_to < menu.available_from:
        raise ValueError("available_to doit être postérieure ou égale à available_from")
    if menu.products is not None:
        ids = [p.product_id for p in menu.products]
        if len(ids) != len(set(ids)):
            raise ValueError("Un produit ne peut apparaître qu'une fois dans un menu")
    return menu


class MenuCreate(SQLModel):
    name: str = Field(min_length=1)
    price: float = Field(gt=0)
    available_from: Optional[datetime.date] = None
    available_to: Optional[datetime.date] = None
    products: list[MenuProductIn] = Field(min_length=1)

    @model_validator(mode="after")
    def check_rules(self):
        return _check_menu_rules(self)


class MenuUpdate(SQLModel):
    name: Optional[str] = Field(default=None, min_length=1)
    price: Optional[float] = Field(default=None, gt=0)
    available_from: Optional[datetime.date] = None
    available_to: Optional[datetime.date] = None
    products: Optional[list[MenuProductIn]] = Field(default=None, min_length=1)

    @model_validator(mode="after")
    def check_rules(self):
        return _check_menu_rules(self)


class MenuRead(SQLModel):
    id: int
    name: str
    price: float
    available_from: Optional[datetime.date]
    available_to: Optional[datetime.date]
    products: list[MenuProductRead]
    
# Order

class OrderStatus(str, Enum):
    pending = "pending"
    in_progress = "in_progress"
    completed = "completed"
    delivered = "delivered"
    cancelled = "cancelled"
    no_show = "no_show"


class OrderItemIn(SQLModel):
    product_id: Optional[int] = None
    menu_id: Optional[int] = None
    quantity: int = Field(default=1, gt=0)

    @model_validator(mode="after")
    def exactly_one_target(self):
        if (self.product_id is None) == (self.menu_id is None):
            raise ValueError("Une ligne doit contenir soit product_id, soit menu_id (un seul des deux)")
        return self


class OrderCreate(SQLModel):
    user_id: int  # TODO security : sera remplacé par l'utilisateur du token
    pickup_date: datetime.date
    items: list[OrderItemIn] = Field(min_length=1)


class OrderStatusUpdate(SQLModel):
    status: OrderStatus


class OrderItemRead(SQLModel):
    id: int
    product_id: Optional[int]
    menu_id: Optional[int]
    name: str
    quantity: int
    unit_price: float


class OrderRead(SQLModel):
    id: int
    user_id: int
    pickup_date: datetime.date
    status: str
    items: list[OrderItemRead]
    total: float