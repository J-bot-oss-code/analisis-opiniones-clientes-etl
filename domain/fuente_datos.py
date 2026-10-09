from sqlalchemy import Column, Integer, String, Date
from domain.base import Base # importamos la base central que nos ayudara a crear las demas tablas

class FuenteDatos(Base):
    __tablename__ = 'FuenteDatos' 
    IdFuente = Column(Integer, primary_key=True, autoincrement=False)
    TipoFuente = Column(String(50))
    FechaCarga = Column(Date)

