import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, Column, String, ForeignKey, Integer, Boolean, DateTime
from sqlalchemy.orm import sessionmaker, declarative_base
from datetime import datetime

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()


# ---------- SQLAlchemy Table Models ----------

class CompanyDB(Base):
    __tablename__ = "companies"

    Company_ID = Column(String, primary_key=True)
    Name = Column(String, nullable=False)
    Gstin = Column(String, unique=True, nullable=False)
    Address = Column(String)
    Password = Column(String, nullable=False)
    Domain = Column(String)


class EmployeeDB(Base):
    __tablename__ = "employees"

    Employee_ID = Column(String, primary_key=True)
    Name = Column(String, nullable=False)
    Email = Column(String, unique=True, nullable=False)
    Password = Column(String, nullable=False)


class CompanyHRDB(Base):
    __tablename__ = "company_hr"

    HR_ID = Column(String, primary_key=True)
    Company_ID = Column(String, ForeignKey("companies.Company_ID"), nullable=False)
    Name = Column(String, nullable=False)
    Company_Email = Column(String, unique=True, nullable=False)
    Password = Column(String, nullable=False)

class EmployeeNotificationDB(Base):
    __tablename__ = "employee_notifications"

    Notif_ID = Column(Integer, primary_key=True, index=True)
    Employee_ID = Column(String, ForeignKey("employees.Employee_ID"), nullable=False)
    Type = Column(String)
    Subject = Column(String)
    Message = Column(String)
    Status = Column(Boolean, default=True)
    Sent_Time = Column(DateTime, default=datetime.utcnow)


class CompanyNotificationDB(Base):
    __tablename__ = "company_notifications"

    Notif_ID = Column(Integer, primary_key=True, index=True)
    Company_ID = Column(String, ForeignKey("companies.Company_ID"), nullable=False)
    Type = Column(String)
    Subject = Column(String)
    Message = Column(String)
    Status = Column(String, default="sent")
    Sent_Time = Column(DateTime, default=datetime.utcnow)

class AuditLogDB(Base):
    __tablename__ = "audit_logs"

    Audit_Log_ID = Column(String, primary_key=True)
    Created_At = Column(DateTime, default=datetime.utcnow)
    HR_ID = Column(String, ForeignKey("company_hr.HR_ID"), nullable=False)
    Action_Type = Column(String, nullable=False)
    Employee_ID = Column(String, ForeignKey("employees.Employee_ID"), nullable=False)

# ---------- Create all tables ----------

Base.metadata.create_all(bind=engine)


# ---------- DB session dependency ----------

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
