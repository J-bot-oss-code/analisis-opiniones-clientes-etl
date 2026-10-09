from sqlalchemy import Column, Integer, String
from domain.base import Base # importamos la base central que nos ayudara a crear las demas tablas

class Cliente(Base):
    __tablename__ = "Cliente"
    IdCliente = Column(Integer, primary_key=True, autoincrement=False)
    Nombre = Column(String(100), nullable=False)
    Email = Column(String(100), nullable=False, unique=True)
