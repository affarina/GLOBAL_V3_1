import os
from sqlalchemy import create_engine, Column, String, Float
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL")

if DATABASE_URL:
    # Render fornece postgres://, mas SQLAlchemy prefere postgresql://
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

    engine = create_engine(DATABASE_URL)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    DB_PATH = os.path.join(BASE_DIR, "dados.db")
    engine = create_engine(f"sqlite:///{DB_PATH}", echo=False)

SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()


class Cadastro(Base):
    __tablename__ = "cadastro"
    numero = Column(String, primary_key=True)
    franquia_mb = Column(Float, nullable=False)


class ConsumoResumido(Base):
    __tablename__ = "consumo_resumido"
    numero = Column(String, primary_key=True)
    nome_usuario = Column(String, nullable=False)
    consumo_mb = Column(Float, nullable=False)


def init_db():
    Base.metadata.create_all(engine)


def get_session():
    return SessionLocal()