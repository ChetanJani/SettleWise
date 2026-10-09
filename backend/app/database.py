from datetime import datetime, timezone
import hashlib
import uuid
from sqlalchemy import create_engine, String, Text, Integer, ForeignKey, UniqueConstraint, select, delete, update
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, Session
from sqlalchemy.types import JSON
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

def now():
    return datetime.now(timezone.utc).isoformat()

class Base(DeclarativeBase): pass

class PropertyRecord(Base):
    __tablename__ = 'sw_properties'
    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    payload: Mapped[dict] = mapped_column(JSON)
    updated_at: Mapped[str] = mapped_column(String(40), default=now)

class SavedRecord(Base):
    __tablename__ = 'sw_saved'
    client_hash: Mapped[str] = mapped_column(String(64),primary_key=True)
    property_id: Mapped[str] = mapped_column(ForeignKey('sw_properties.id'),primary_key=True)
    created_at: Mapped[str] = mapped_column(String(40),default=now)

class Observation(Base):
    __tablename__ = 'sw_observations'
    id: Mapped[str] = mapped_column(String(40),primary_key=True,default=lambda:str(uuid.uuid4()))
    area: Mapped[str] = mapped_column(String(160),index=True)
    city: Mapped[str] = mapped_column(String(80))
    category: Mapped[str] = mapped_column(String(30))
    sentiment: Mapped[str] = mapped_column(String(20))
    text: Mapped[str] = mapped_column(Text)
    occurred_on: Mapped[str | None] = mapped_column(String(10),nullable=True)
    created_at: Mapped[str] = mapped_column(String(40),default=now)
    status: Mapped[str] = mapped_column(String(20),default='unverified')
    helpful: Mapped[int] = mapped_column(Integer,default=0)

class Vote(Base):
    __tablename__ = 'sw_votes'
    client_hash: Mapped[str] = mapped_column(String(64),primary_key=True)
    observation_id: Mapped[str] = mapped_column(ForeignKey('sw_observations.id'),primary_key=True)

class PrivateInputs(Base):
    __tablename__ = 'sw_property_inputs'
    client_hash: Mapped[str] = mapped_column(String(64),primary_key=True)
    property_id: Mapped[str] = mapped_column(ForeignKey('sw_properties.id'),primary_key=True)
    payload: Mapped[dict] = mapped_column(JSON)

class Store:
    def __init__(self, url):
        self.kind = 'postgresql' if url.startswith('postgresql') else 'sqlite'
        args = {'connect_timeout':10} if self.kind == 'postgresql' else {'check_same_thread':False}
        self.engine = create_engine(url,connect_args=args,pool_pre_ping=True,hide_parameters=True,**({'pool_size':3,'max_overflow':2} if self.kind=='postgresql' else {}))
        self.ready = False

    def initialise(self):
        Base.metadata.create_all(self.engine)
        self.ready = True

    def put_properties(self, properties):
        if not properties:return
        with Session(self.engine) as session:
            statement=self.insert(PropertyRecord).values([{'id':item['id'],'payload':item,'updated_at':now()} for item in properties])
            session.execute(statement.on_conflict_do_update(index_elements=['id'],set_={'payload':statement.excluded.payload,'updated_at':statement.excluded.updated_at}))
            session.commit()

    def insert(self, model):
        return (pg_insert if self.kind=='postgresql' else sqlite_insert)(model)

    def inputs(self, client, properties):
        with Session(self.engine) as session:
            values={r.property_id:r.payload for r in session.scalars(select(PrivateInputs).where(PrivateInputs.client_hash==self.identity(client),PrivateInputs.property_id.in_([p['id'] for p in properties])))}
            return [{**p,**values[p['id']],'facts_source':'Your entered details · confirm with provider','entered_fields':list(values[p['id']])} if p['id'] in values else dict(p) for p in properties]

    def set_inputs(self, client, pid, values):
        with Session(self.engine) as session:
            statement=self.insert(PrivateInputs).values(client_hash=self.identity(client),property_id=pid,payload=values)
            session.execute(statement.on_conflict_do_update(index_elements=['client_hash','property_id'],set_={'payload':statement.excluded.payload}))
            session.commit()

    def get(self, property_id):
        with Session(self.engine) as session:
            row = session.get(PropertyRecord,property_id)
            return dict(row.payload) if row else None

    def many(self, ids):
        with Session(self.engine) as session:
            return [dict(r.payload) for r in session.scalars(select(PropertyRecord).where(PropertyRecord.id.in_(ids))).all()]

    @staticmethod
    def identity(client): return hashlib.sha256(client.encode()).hexdigest()

    def saved(self, client):
        with Session(self.engine) as session:
            statement=select(PropertyRecord).join(SavedRecord,PropertyRecord.id==SavedRecord.property_id).where(SavedRecord.client_hash==self.identity(client)).order_by(SavedRecord.created_at.desc())
            return [dict(r.payload) for r in session.scalars(statement).all()]

    def save(self, client, property_id, enabled):
        key=(self.identity(client),property_id)
        with Session(self.engine) as session:
            row=session.get(SavedRecord,key)
            if enabled: session.execute(self.insert(SavedRecord).values(client_hash=key[0],property_id=key[1]).on_conflict_do_nothing())
            if not enabled and row: session.delete(row)
            session.commit()

    def observations(self, area, city):
        with Session(self.engine) as session:
            rows=session.scalars(select(Observation).where(Observation.area.ilike(area.replace('%','\\%').replace('_','\\_'),escape='\\'),Observation.city.ilike(city.replace('%','\\%').replace('_','\\_'),escape='\\')).order_by(Observation.created_at.desc()).limit(100)).all()
            return [self.serialise(r) for r in rows]

    @staticmethod
    def serialise(row):
        return {k:getattr(row,k) for k in ('id','area','city','category','sentiment','text','occurred_on','created_at','status','helpful')}

    def observe(self, body):
        data=body.model_dump(mode='json')
        with Session(self.engine) as session:
            row=Observation(**data)
            session.add(row);session.commit();session.refresh(row)
            return self.serialise(row)

    def helpful(self, client, observation_id):
        with Session(self.engine) as session:
            row=session.get(Observation,observation_id)
            if not row:return None
            key=(self.identity(client),observation_id)
            inserted=session.execute(self.insert(Vote).values(client_hash=key[0],observation_id=key[1]).on_conflict_do_nothing()).rowcount
            if inserted:
                session.execute(update(Observation).where(Observation.id==observation_id).values(helpful=Observation.helpful+1))
            session.commit();session.refresh(row)
            return self.serialise(row)
