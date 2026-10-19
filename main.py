
from datetime import datetime
from decimal import Decimal
import os
from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Integer,
    Numeric,
    String,
    Text,
    create_engine,
    func,
)
from sqlalchemy.orm import Session, declarative_base, sessionmaker

app = FastAPI(title="Product Management API")

# SQLite database configuration
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_URL = f"sqlite:///{os.path.join(BASE_DIR, 'products.db')}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

Base = declarative_base()


# Database table
class ProductDB(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    price = Column(Numeric(10, 2), nullable=False)
    category = Column(String(50), nullable=False)
    brand = Column(String(50), nullable=False)
    stock = Column(Integer, nullable=False)
    is_available = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )


# Create tables that do not already exist
Base.metadata.create_all(bind=engine)


# Request validation
class Product(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = None
    price: Decimal = Field(..., gt=0, max_digits=10, decimal_places=2)
    category: str = Field(..., min_length=1, max_length=50)
    brand: str = Field(..., min_length=1, max_length=50)
    stock: int = Field(..., ge=0)
    is_available: bool = True


# Database session dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Format a database product for API responses
def product_response(product):
    return {
        "id": product.id,
        "name": product.name,
        "description": product.description,
        "price": product.price,
        "category": product.category,
        "brand": product.brand,
        "stock": product.stock,
        "is_available": product.is_available,
        "created_at": product.created_at,
        "updated_at": product.updated_at,
    }


# CREATE: Add a product
@app.post("/CreateProduct", status_code=201)
def create_product(product: Product, db: Session = Depends(get_db)):
    db_product = ProductDB(**product.model_dump())

    db.add(db_product)
    db.commit()
    db.refresh(db_product)

    return {
        "message": "Product created successfully",
        "product": product_response(db_product),
    }


# READ: Get all products
@app.get("/ReadProducts")
def read_products(db: Session = Depends(get_db)):
    products = db.query(ProductDB).all()

    return {
        "message": "Products retrieved successfully",
        "products": [product_response(p) for p in products],
    }


# READ: Get one product by ID
@app.get("/ReadProduct/{product_id}")
def read_product(product_id: int, db: Session = Depends(get_db)):
    product = db.query(ProductDB).filter(
        ProductDB.id == product_id
    ).first()

    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")

    return {
        "message": "Product retrieved successfully",
        "product": product_response(product),
    }


# UPDATE: Replace product fields using its ID
@app.put("/UpdateProduct/{product_id}")
def update_product(
    product_id: int,
    product: Product,
    db: Session = Depends(get_db),
):
    db_product = db.query(ProductDB).filter(
        ProductDB.id == product_id
    ).first()

    if db_product is None:
        raise HTTPException(status_code=404, detail="Product not found")

    try:
        for field, value in product.model_dump().items():
            setattr(db_product, field, value)

        # Refresh updated_at when the record changes
        db_product.updated_at = datetime.utcnow()

        db.commit()
        db.refresh(db_product)

        return {
            "message": "Product updated successfully",
            "product": product_response(db_product),
        }

    except Exception:
        db.rollback()
        raise


# DELETE: Remove a product using its ID
@app.delete("/DeleteProduct/{product_id}")
def delete_product(product_id: int, db: Session = Depends(get_db)):
    db_product = db.query(ProductDB).filter(
        ProductDB.id == product_id
    ).first()

    if db_product is None:
        raise HTTPException(status_code=404, detail="Product not found")

    db.delete(db_product)
    db.commit()

    return {
        "message": "Product deleted successfully",
        "product_id": product_id,
    }