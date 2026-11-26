import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlmodel import Session, select, col, or_

from app.database import get_session
from app.models import Menu, MenuProduct, OrderItem, Product
from app.schemas import MenuCreate, MenuProductIn, MenuRead, MenuProductRead, MenuUpdate
from app.security import get_current_admin

router = APIRouter(prefix="/menus", tags=["menus"])


def build_menu_read(session: Session, menu: Menu) -> MenuRead:
    """Assemble un menu avec le détail de ses produits."""
    rows = session.exec(
        select(MenuProduct, Product)
        .where(MenuProduct.menu_id == menu.id)
        .where(MenuProduct.product_id == Product.id)
    ).all()
    return MenuRead(
        id=menu.id,
        name=menu.name,
        price=menu.price,
        available_from=menu.available_from,
        available_to=menu.available_to,
        products=[
            MenuProductRead(product_id=p.id, name=p.name, price=p.price, quantity=mp.quantity)
            for mp, p in rows
        ],
    )


def check_products_exist(session: Session, items: list[MenuProductIn]):
    ids = {i.product_id for i in items}
    found = set(session.exec(select(Product.id).where(col(Product.id).in_(ids))).all())
    missing = ids - found
    if missing:
        raise HTTPException(status_code=404, detail=f"Produit(s) introuvable(s) : {sorted(missing)}")


def set_menu_products(session: Session, menu_id: int, items: list[MenuProductIn]):
    """Remplace la composition d'un menu (sans commit)."""
    for old in session.exec(select(MenuProduct).where(MenuProduct.menu_id == menu_id)).all():
        session.delete(old)
    session.flush()
    for item in items:
        session.add(MenuProduct(menu_id=menu_id, product_id=item.product_id, quantity=item.quantity))


@router.get("/", response_model=list[MenuRead], summary="Afficher les menus")
def list_menus(on_date: Optional[datetime.date] = None, session: Session = Depends(get_session)):
    query = select(Menu)
    if on_date:
        query = query.where(or_(col(Menu.available_from).is_(None), Menu.available_from <= on_date))
        query = query.where(or_(col(Menu.available_to).is_(None), Menu.available_to >= on_date))
    return [build_menu_read(session, m) for m in session.exec(query).all()]


@router.get("/{menu_id}", response_model=MenuRead, summary="Détail d'un menu")
def get_menu(menu_id: int, session: Session = Depends(get_session)):
    menu = session.get(Menu, menu_id)
    if menu is None:
        raise HTTPException(status_code=404, detail="Menu introuvable")
    return build_menu_read(session, menu)


@router.post("/", response_model=MenuRead, status_code=201, summary="Créer un menu")
def create_menu(
    data: MenuCreate,
    session: Session = Depends(get_session),
    admin=Depends(get_current_admin),  # TODO security
):
    check_products_exist(session, data.products)
    menu = Menu(
        name=data.name,
        price=data.price,
        available_from=data.available_from,
        available_to=data.available_to,
    )
    session.add(menu)
    session.flush()  # envoie l'INSERT pour obtenir menu.id, sans valider
    set_menu_products(session, menu.id, data.products)
    session.commit()
    session.refresh(menu)
    return build_menu_read(session, menu)


@router.patch("/{menu_id}", response_model=MenuRead, summary="Modifier un menu")
def update_menu(
    menu_id: int,
    data: MenuUpdate,
    session: Session = Depends(get_session),
    admin=Depends(get_current_admin),  # TODO security
):
    menu = session.get(Menu, menu_id)
    if menu is None:
        raise HTTPException(status_code=404, detail="Menu introuvable")

    fields = data.model_dump(exclude_unset=True)
    fields.pop("products", None)
    menu.sqlmodel_update(fields)

    if menu.available_from and menu.available_to and menu.available_to < menu.available_from:
        raise HTTPException(status_code=422, detail="available_to doit être postérieure à available_from")

    if data.products is not None:
        check_products_exist(session, data.products)
        set_menu_products(session, menu.id, data.products)

    session.add(menu)
    session.commit()
    session.refresh(menu)
    return build_menu_read(session, menu)


@router.delete("/{menu_id}", status_code=204, summary="Supprimer un menu")
def delete_menu(
    menu_id: int,
    session: Session = Depends(get_session),
    admin=Depends(get_current_admin),  # TODO security
):
    menu = session.get(Menu, menu_id)
    if menu is None:
        raise HTTPException(status_code=404, detail="Menu introuvable")

    used = session.exec(select(OrderItem).where(OrderItem.menu_id == menu_id)).first()
    if used:
        raise HTTPException(status_code=409, detail="Menu présent dans des commandes : suppression impossible")

    for mp in session.exec(select(MenuProduct).where(MenuProduct.menu_id == menu_id)).all():
        session.delete(mp)
    session.delete(menu)
    session.commit()
    return Response(status_code=204)