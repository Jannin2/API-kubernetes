import os

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import Column, ForeignKey, Integer, String, create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker




DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL no está configurada")

engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False
)




class Base(DeclarativeBase):
    pass


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    price = Column(Integer, nullable=False)


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True)
    product_id = Column(
        Integer,
        ForeignKey("products.id"),
        nullable=False
    )
    quantity = Column(Integer, nullable=False)



class ProductCreate(BaseModel):
    name: str
    price: int = Field(ge=0)


class OrderCreate(BaseModel):
    product_id: int
    quantity: int = Field(ge=1)




app = FastAPI(title="k8s-shop")




app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)




def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()




def seed_products():
    db = SessionLocal()

    try:
        if db.query(Product).count() == 0:
            db.add_all(
                [
                    Product(
                        name="Laptop",
                        price=2000000
                    ),
                    Product(
                        name="Mouse",
                        price=80000
                    ),
                    Product(
                        name="Teclado",
                        price=120000
                    ),
                ]
            )

            db.commit()

    finally:
        db.close()



@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)
    seed_products()




@app.get("/health")
def health():
    return {
        "status": "ok"
    }


@app.get("/ready")
def ready():
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))

        return {
            "status": "ready"
        }

    except Exception:
        raise HTTPException(
            status_code=503,
            detail={
                "status": "not ready"
            }
        )




@app.get("/products")
def list_products(
    db: Session = Depends(get_db)
):
    products = (
        db.query(Product)
        .order_by(Product.id)
        .all()
    )

    return [
        {
            "id": product.id,
            "name": product.name,
            "price": product.price
        }
        for product in products
    ]




@app.get("/products/{product_id}")
def get_product(
    product_id: int,
    db: Session = Depends(get_db)
):
    product = db.get(Product, product_id)

    if product is None:
        raise HTTPException(
            status_code=404,
            detail="Product not found"
        )

    return {
        "id": product.id,
        "name": product.name,
        "price": product.price
    }




@app.post("/products", status_code=201)
def create_product(
    payload: ProductCreate,
    db: Session = Depends(get_db)
):
    product = Product(
        name=payload.name,
        price=payload.price
    )

    db.add(product)
    db.commit()
    db.refresh(product)

    return {
        "id": product.id,
        "name": product.name,
        "price": product.price
    }




@app.put("/products/{product_id}")
def update_product(
    product_id: int,
    payload: ProductCreate,
    db: Session = Depends(get_db)
):
    product = db.get(Product, product_id)

    if product is None:
        raise HTTPException(
            status_code=404,
            detail="Product not found"
        )

    product.name = payload.name
    product.price = payload.price

    db.commit()
    db.refresh(product)

    return {
        "id": product.id,
        "name": product.name,
        "price": product.price
    }




@app.delete("/products/{product_id}")
def delete_product(
    product_id: int,
    db: Session = Depends(get_db)
):
    product = db.get(Product, product_id)

    if product is None:
        raise HTTPException(
            status_code=404,
            detail="Product not found"
        )

    # Verificar si existen pedidos asociados
    orders = (
        db.query(Order)
        .filter(Order.product_id == product_id)
        .count()
    )

    if orders > 0:
        raise HTTPException(
            status_code=409,
            detail=(
                "No se puede eliminar el producto porque "
                "tiene pedidos asociados"
            )
        )

    db.delete(product)
    db.commit()

    return {
        "message": "Product deleted successfully"
    }




@app.get("/orders")
def list_orders(
    db: Session = Depends(get_db)
):
    orders = (
        db.query(Order)
        .order_by(Order.id)
        .all()
    )

    return [
        {
            "id": order.id,
            "product_id": order.product_id,
            "quantity": order.quantity
        }
        for order in orders
    ]




@app.post("/orders", status_code=201)
def create_order(
    payload: OrderCreate,
    db: Session = Depends(get_db)
):
    product = db.get(
        Product,
        payload.product_id
    )

    if product is None:
        raise HTTPException(
            status_code=404,
            detail="Product not found"
        )

    order = Order(
        product_id=payload.product_id,
        quantity=payload.quantity
    )

    db.add(order)
    db.commit()
    db.refresh(order)

    return {
        "id": order.id,
        "product_id": order.product_id,
        "quantity": order.quantity
    }



@app.delete("/orders/{order_id}")
def delete_order(
    order_id: int,
    db: Session = Depends(get_db)
):
    order = db.get(
        Order,
        order_id
    )

    if order is None:
        raise HTTPException(
            status_code=404,
            detail="Order not found"
        )

    db.delete(order)
    db.commit()

    return {
        "message": "Order deleted successfully"
    }
