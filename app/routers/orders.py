import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.database import get_session
from app.models import ClosingDay, Menu, MenuProduct, Order, OrderItem, Product, User
from app.schemas import OrderCreate, OrderRead, OrderItemRead, OrderStatus, OrderStatusUpdate
from app.security import get_current_admin

router = APIRouter(prefix="/orders", tags=["orders"])

# Transitions de statut autorisées
TRANSITIONS = {
    "pending": {"in_progress", "cancelled"},
    "in_progress": {"completed", "cancelled"},
    "completed": {"delivered", "no_show"},
    "delivered": set(),
    "cancelled": set(),
    "no_show": set(),
}


def build_order_read(session: Session, order: Order) -> OrderRead:
    items = session.exec(select(OrderItem).where(OrderItem.order_id == order.id)).all()
    out = []
    for it in items:
        target = session.get(Product, it.product_id) if it.product_id else session.get(Menu, it.menu_id)
        out.append(OrderItemRead(
            id=it.id,
            product_id=it.product_id,
            menu_id=it.menu_id,
            name=target.name if target else "(supprimé)",
            quantity=it.quantity,
            unit_price=it.unit_price,
        ))
    return OrderRead(
        id=order.id,
        user_id=order.user_id,
        pickup_date=order.pickup_date,
        status=order.status,
        items=out,
        total=sum(i.unit_price * i.quantity for i in out),
    )


def give_back_stock(session: Session, product_id: int, qty: int):
    product = session.get(Product, product_id)
    if product is None:
        return
    if product.stock == 0 and not product.is_available:
        product.is_available = True   # il n'était indisponible que faute de stock
    product.stock += qty
    session.add(product)


def restore_stock(session: Session, order: Order):
    items = session.exec(select(OrderItem).where(OrderItem.order_id == order.id)).all()
    for it in items:
        if it.product_id:
            give_back_stock(session, it.product_id, it.quantity)
        else:
            rows = session.exec(select(MenuProduct).where(MenuProduct.menu_id == it.menu_id)).all()
            for mp in rows:
                give_back_stock(session, mp.product_id, mp.quantity * it.quantity)


def change_status(session: Session, order: Order, new_status: str):
    if new_status not in TRANSITIONS[order.status]:
        raise HTTPException(
            status_code=409,
            detail=f"Passage de '{order.status}' à '{new_status}' impossible",
        )
    if new_status == "cancelled":
        restore_stock(session, order)
    order.status = new_status
    session.add(order)
    session.commit()
    session.refresh(order)


@router.post("/", response_model=OrderRead, status_code=201, summary="Créer une commande")
def create_order(data: OrderCreate, session: Session = Depends(get_session)):
    # TODO security : user = utilisateur connecté, pas un user_id envoyé par le client
    user = session.get(User, data.user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")
    if user.is_blocked:
        raise HTTPException(status_code=403, detail="Compte bloqué : commande impossible")

    if data.pickup_date < datetime.date.today():
        raise HTTPException(status_code=422, detail="La date de retrait ne peut pas être dans le passé")
    closed = session.exec(select(ClosingDay).where(ClosingDay.date == data.pickup_date)).first()
    if closed:
        raise HTTPException(status_code=409, detail="L'établissement est fermé ce jour-là")

    # 1) Calculer le prix de chaque ligne et le stock total nécessaire par produit
    needs: dict[int, int] = {}
    lines = []  # (ligne demandée, prix unitaire)
    for item in data.items:
        if item.product_id is not None:
            product = session.get(Product, item.product_id)
            if product is None:
                raise HTTPException(status_code=404, detail=f"Produit {item.product_id} introuvable")
            needs[product.id] = needs.get(product.id, 0) + item.quantity
            lines.append((item, product.price))
        else:
            menu = session.get(Menu, item.menu_id)
            if menu is None:
                raise HTTPException(status_code=404, detail=f"Menu {item.menu_id} introuvable")
            if menu.available_from and data.pickup_date < menu.available_from:
                raise HTTPException(status_code=409, detail=f"Le menu '{menu.name}' n'est pas encore disponible à cette date")
            if menu.available_to and data.pickup_date > menu.available_to:
                raise HTTPException(status_code=409, detail=f"Le menu '{menu.name}' n'est plus disponible à cette date")
            rows = session.exec(select(MenuProduct).where(MenuProduct.menu_id == menu.id)).all()
            for mp in rows:
                needs[mp.product_id] = needs.get(mp.product_id, 0) + mp.quantity * item.quantity
            lines.append((item, menu.price))

    # 2) Vérifier disponibilité et stock AVANT de modifier quoi que ce soit
    problems = []
    for pid, qty in needs.items():
        product = session.get(Product, pid)
        if product is None:
            raise HTTPException(status_code=404, detail=f"Produit {pid} introuvable")
        if not product.is_available:
            problems.append(f"'{product.name}' est indisponible")
        elif product.stock < qty:
            problems.append(f"'{product.name}' : stock insuffisant ({product.stock} restant, {qty} demandé)")
    if problems:
        raise HTTPException(status_code=409, detail=problems)

    # 3) Tout est valide : créer la commande, ses lignes, et décrémenter le stock
    order = Order(user_id=user.id, pickup_date=data.pickup_date, status="pending")
    session.add(order)
    session.flush()  # pour obtenir order.id sans valider

    for item, unit_price in lines:
        session.add(OrderItem(
            order_id=order.id,
            product_id=item.product_id,
            menu_id=item.menu_id,
            quantity=item.quantity,
            unit_price=unit_price,
        ))

    for pid, qty in needs.items():
        product = session.get(Product, pid)
        product.stock -= qty
        if product.stock == 0:
            product.is_available = False   # grisé côté front
        session.add(product)

    session.commit()
    session.refresh(order)
    return build_order_read(session, order)


@router.get("/", response_model=list[OrderRead], summary="Lister les commandes")
def list_orders(
    user_id: Optional[int] = None,
    status: Optional[OrderStatus] = None,
    pickup_date: Optional[datetime.date] = None,
    session: Session = Depends(get_session),
):
    # TODO security : un utilisateur ne voit que ses commandes, l'admin voit tout
    query = select(Order).order_by(Order.pickup_date)
    if user_id is not None:
        query = query.where(Order.user_id == user_id)
    if status is not None:
        query = query.where(Order.status == status.value)
    if pickup_date is not None:
        query = query.where(Order.pickup_date == pickup_date)
    return [build_order_read(session, o) for o in session.exec(query).all()]


@router.get("/{order_id}", response_model=OrderRead, summary="Détail d'une commande")
def get_order(order_id: int, session: Session = Depends(get_session)):
    # TODO security : vérifier order.user_id == utilisateur connecté (sauf admin)
    order = session.get(Order, order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Commande introuvable")
    return build_order_read(session, order)


@router.post("/{order_id}/cancel", response_model=OrderRead, summary="Annuler une commande")
def cancel_order(order_id: int, session: Session = Depends(get_session)):
    # TODO security : seulement le propriétaire de la commande
    order = session.get(Order, order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Commande introuvable")
    if order.status != "pending":
        raise HTTPException(status_code=409, detail="Seule une commande en attente peut être annulée")
    change_status(session, order, "cancelled")
    return build_order_read(session, order)


@router.patch("/{order_id}/status", response_model=OrderRead, summary="Changer l'état d'une commande")
def update_status(
    order_id: int,
    data: OrderStatusUpdate,
    session: Session = Depends(get_session),
    admin=Depends(get_current_admin),  # TODO security
):
    order = session.get(Order, order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Commande introuvable")
    change_status(session, order, data.status.value)
    return build_order_read(session, order)