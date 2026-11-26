from typing import Optional
from sqlmodel import SQLModel, Field
import datetime


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