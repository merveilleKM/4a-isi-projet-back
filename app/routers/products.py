from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlmodel import Session, select

from app.database import get_session
from app.models import Product
from app.schemas import ProductCreate, ProductRead, ProductUpdate
from app.security import get_current_admin

router = APIRouter(prefix="/products", tags=["products"])


@router.get("/", response_model=list[ProductRead], summary="Lister / rechercher les produits")
def list_products(search: Optional[str] = None, session: Session = Depends(get_session)):
    query = select(Product)
    if search:
        query = query.where(Product.name.contains(search))
    return session.exec(query).all()


@router.get("/{product_id}", response_model=ProductRead, summary="Détail d'un produit")
def get_product(product_id: int, session: Session = Depends(get_session)):
    product = session.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Produit introuvable")
    return product


@router.post("/", response_model=ProductRead, status_code=201, summary="Ajouter un produit")
def create_product(
    data: ProductCreate,
    session: Session = Depends(get_session),
    admin=Depends(get_current_admin),  # TODO security
):
    product = Product.model_validate(data)
    session.add(product)
    session.commit()
    session.refresh(product)
    return product


@router.patch("/{product_id}", response_model=ProductRead, summary="Modifier un produit (stock, prix...)")
def update_product(
    product_id: int,
    data: ProductUpdate,
    session: Session = Depends(get_session),
    admin=Depends(get_current_admin),  # TODO security
):
    product = session.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Produit introuvable")
    product.sqlmodel_update(data.model_dump(exclude_unset=True))
    session.add(product)
    session.commit()
    session.refresh(product)
    return product


@router.delete("/{product_id}", status_code=204, summary="Supprimer un produit")
def delete_product(
    product_id: int,
    session: Session = Depends(get_session),
    admin=Depends(get_current_admin),  # TODO security
):
    product = session.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Produit introuvable")
    session.delete(product)
    session.commit()
    return Response(status_code=204)