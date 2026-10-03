"""Explicit demo seeding; no production default passwords or auto-seeding."""

import argparse
import os
from decimal import Decimal
from sqlalchemy import select
from .db import connectors, engine, organisations, users
from .schemas import OrderInput
from .security import hash_password
from .services import accept_order, uid


def seed(email, password, name="Harare Trading", demo=False):
    if len(password) < 12:
        raise ValueError("Use a password of at least 12 characters.")
    with engine.begin() as conn:
        if conn.execute(select(users.c.id).where(users.c.email == email)).first():
            raise ValueError("This email already exists. Seeding never overwrites users.")
        org = uid()
        conn.execute(organisations.insert().values(id=org, name=name))
        conn.execute(connectors.insert().values(org_id=org, mode="available"))
        conn.execute(
            users.insert().values(
                id=uid(),
                org_id=org,
                name="Jayden Mapasure",
                email=email,
                password_hash=hash_password(password),
                role="admin",
                active=True,
            )
        )
    if demo:
        for i, (customer, amount) in enumerate(
            [
                ("Mbare Hardware", "129.00"),
                ("Northside Supplies", "349.90"),
                ("Chisipite Stores", "89.50"),
                ("Mutare Distribution", "560.00"),
                ("Borrowdale Office", "215.00"),
                ("Westgate Retail", "74.25"),
            ],
            1,
        ):
            accept_order(
                org,
                OrderInput(
                    event_id=f"demo-event-{i}",
                    reference=f"ORD-{1000 + i}",
                    customer=customer,
                    amount=Decimal(amount),
                    currency="USD",
                ),
                "demo seed",
            )
    return org


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--demo", action="store_true")
    args = parser.parse_args()
    email = os.environ.get("ADMIN_EMAIL", "")
    password = os.environ.get("ADMIN_PASSWORD", "")
    if not email or not password:
        raise SystemExit("Set ADMIN_EMAIL and ADMIN_PASSWORD before seeding.")
    seed(email.lower(), password, demo=args.demo)
    print("Administrator created." + (" Sample orders added." if args.demo else ""))
