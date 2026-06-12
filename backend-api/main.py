from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from database import get_db, EmployeeDB, CompanyDB, CompanyHRDB, EmployeeNotificationDB, CompanyNotificationDB, AuditLogDB

app = FastAPI()


# ---------- Pydantic schemas (request validation) ----------

class Company(BaseModel):
    Company_ID: str
    Name: str
    Gstin: str
    Address: str
    Password: str
    Domain: str


class Employee(BaseModel):
    Employee_ID: str
    Name: str
    Email: EmailStr
    Password: str


class CompanyHR(BaseModel):
    HR_ID: str
    Company_ID: str
    Name: str
    Company_Email: EmailStr
    Password: str


# ---------- Signup schemas (no ID — server generates it) ----------

class CompanySignup(BaseModel):
    Name: str
    Gstin: str
    Address: str
    Password: str
    Domain: str


class EmployeeSignup(BaseModel):
    Name: str
    Email: EmailStr
    Password: str


class HRSignup(BaseModel):
    Company_ID: str
    Name: str
    Company_Email: EmailStr
    Password: str


class EmployeeLogin(BaseModel):
    Email: EmailStr
    Password: str


class CompanyLogin(BaseModel):
    Gstin: str
    Password: str


class HRLogin(BaseModel):
    Company_Email: EmailStr
    Password: str

class EmployeeNotification(BaseModel):
    Employee_ID: str
    Type: str
    Subject: str
    Message: str


class CompanyNotification(BaseModel):
    Company_ID: str
    Type: str
    Subject: str
    Message: str

class AuditLog(BaseModel):
    HR_ID: str
    Action_Type: str
    Employee_ID: str
# ---------- ID generation helper ----------

def generate_custom_id(name: str, type_char: str, db: Session, model_class, id_column) -> str:
    """Generate a custom ID in the format AAT000.
    AA = first 2 letters of name (uppercased)
    T  = type char (C for company, E for employee, H for HR)
    000 = incrementing number based on total existing records
    """
    prefix = name[:2].upper()
    count = db.query(model_class).count()
    number = str(count + 1).zfill(3)
    return f"{prefix}{type_char}{number}"


def generate_audit_log_id(db: Session) -> str:
    """Generate an Audit Log ID in the format AUD000."""
    count = db.query(AuditLogDB).count()
    number = str(count + 1).zfill(3)
    return f"AUD{number}"


# ---------- Routes ----------

@app.get("/")
def read_root():
    return {"Hello": "World"}


# ---------- Signup Routes ----------

@app.post("/company/signup")
def company_signup(data: CompanySignup, db: Session = Depends(get_db)):
    # Check for duplicate GSTIN
    existing = db.query(CompanyDB).filter(CompanyDB.Gstin == data.Gstin).first()
    if existing:
        raise HTTPException(status_code=400, detail="A company with this GSTIN already exists")

    custom_id = generate_custom_id(data.Name, "C", db, CompanyDB, CompanyDB.Company_ID)

    new_company = CompanyDB(
        Company_ID=custom_id,
        Name=data.Name,
        Gstin=data.Gstin,
        Address=data.Address,
        Password=data.Password,
        Domain=data.Domain
    )
    db.add(new_company)
    db.commit()
    db.refresh(new_company)

    return {"message": "Company registered successfully", "Company_ID": custom_id}


@app.post("/employee/signup")
def employee_signup(data: EmployeeSignup, db: Session = Depends(get_db)):
    # Check for duplicate email
    existing = db.query(EmployeeDB).filter(EmployeeDB.Email == data.Email).first()
    if existing:
        raise HTTPException(status_code=400, detail="An employee with this email already exists")

    custom_id = generate_custom_id(data.Name, "E", db, EmployeeDB, EmployeeDB.Employee_ID)

    new_employee = EmployeeDB(
        Employee_ID=custom_id,
        Name=data.Name,
        Email=data.Email,
        Password=data.Password
    )
    db.add(new_employee)
    db.commit()
    db.refresh(new_employee)

    return {"message": "Employee registered successfully", "Employee_ID": custom_id}


@app.post("/hr/signup")
def hr_signup(data: HRSignup, db: Session = Depends(get_db)):
    # Verify that the Company_ID exists
    company = db.query(CompanyDB).filter(CompanyDB.Company_ID == data.Company_ID).first()
    if not company:
        raise HTTPException(status_code=400, detail="Company Does Not Exist")

    # Check for duplicate company email
    existing = db.query(CompanyHRDB).filter(CompanyHRDB.Company_Email == data.Company_Email).first()
    if existing:
        raise HTTPException(status_code=400, detail="An HR with this company email already exists")

    custom_id = generate_custom_id(data.Name, "H", db, CompanyHRDB, CompanyHRDB.HR_ID)

    new_hr = CompanyHRDB(
        HR_ID=custom_id,
        Company_ID=data.Company_ID,
        Name=data.Name,
        Company_Email=data.Company_Email,
        Password=data.Password
    )
    db.add(new_hr)
    db.commit()
    db.refresh(new_hr)

    return {"message": "HR registered successfully", "HR_ID": custom_id}


@app.post("/employee/login")
def employee_login(data: EmployeeLogin, db: Session = Depends(get_db)):
    emp = db.query(EmployeeDB).filter(
        EmployeeDB.Email == data.Email,
        EmployeeDB.Password == data.Password
    ).first()
    if emp:
        return {"message": "Employee login successful", "Employee_ID": emp.Employee_ID, "Name": emp.Name}
    raise HTTPException(status_code=401, detail="Invalid email or password")


@app.post("/company/login")
def company_login(data: CompanyLogin, db: Session = Depends(get_db)):
    company = db.query(CompanyDB).filter(
        CompanyDB.Gstin == data.Gstin,
        CompanyDB.Password == data.Password
    ).first()
    if company:
        return {"message": "Company login successful", "Company_ID": company.Company_ID, "Name": company.Name}
    raise HTTPException(status_code=401, detail="Invalid GSTIN or password")


@app.post("/hr/login")
def hr_login(data: HRLogin, db: Session = Depends(get_db)):
    hr = db.query(CompanyHRDB).filter(
        CompanyHRDB.Company_Email == data.Company_Email,
        CompanyHRDB.Password == data.Password
    ).first()
    if hr:
        return {"message": "HR login successful", "HR_ID": hr.HR_ID, "Name": hr.Name}
    raise HTTPException(status_code=401, detail="Invalid company email or password")


@app.post("/employee/notification")
def send_employee_notification(data: EmployeeNotification, db: Session = Depends(get_db)):
    employee = db.query(EmployeeDB).filter(EmployeeDB.Employee_ID == data.Employee_ID).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")

    notification = EmployeeNotificationDB(
        Employee_ID=data.Employee_ID,
        Type=data.Type,
        Subject=data.Subject,
        Message=data.Message,
        Status=True
    )

    db.add(notification)
    db.commit()
    db.refresh(notification)

    return {
        "message": "Notification sent to employee",
        "notification_id": notification.Notif_ID
    }


@app.post("/company/notification")
def send_company_notification(data: CompanyNotification, db: Session = Depends(get_db)):
    company = db.query(CompanyDB).filter(CompanyDB.Company_ID == data.Company_ID).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    notification = CompanyNotificationDB(
        Company_ID=data.Company_ID,
        Type=data.Type,
        Subject=data.Subject,
        Message=data.Message,
        Status="sent"
    )

    db.add(notification)
    db.commit()
    db.refresh(notification)

    return {
        "message": "Notification sent to company",
        "notification_id": notification.Notif_ID
    }


@app.get("/employee/{employee_id}/notifications")
def get_employee_notifications(employee_id: str, db: Session = Depends(get_db)):
    notifications = db.query(EmployeeNotificationDB).filter(
        EmployeeNotificationDB.Employee_ID == employee_id
    ).all()

    return notifications


@app.get("/company/{company_id}/notifications")
def get_company_notifications(company_id: str, db: Session = Depends(get_db)):
    notifications = db.query(CompanyNotificationDB).filter(
        CompanyNotificationDB.Company_ID == company_id
    ).all()

    return notifications

@app.post("/audit-log")
def create_audit_log(data: AuditLog, db: Session = Depends(get_db)):
    hr = db.query(CompanyHRDB).filter(CompanyHRDB.HR_ID == data.HR_ID).first()
    if not hr:
        raise HTTPException(status_code=404, detail="HR not found")

    employee = db.query(EmployeeDB).filter(EmployeeDB.Employee_ID == data.Employee_ID).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")

    log_id = generate_audit_log_id(db)

    new_log = AuditLogDB(
        Audit_Log_ID=log_id,
        HR_ID=data.HR_ID,
        Action_Type=data.Action_Type,
        Employee_ID=data.Employee_ID
    )
    db.add(new_log)
    db.commit()
    db.refresh(new_log)

    return {"message": "Audit log created", "Audit_Log_ID": log_id}


@app.get("/audit-logs/hr/{hr_id}")
def get_audit_logs_by_hr(hr_id: str, db: Session = Depends(get_db)):
    logs = db.query(AuditLogDB).filter(AuditLogDB.HR_ID == hr_id).all()
    return logs


@app.get("/audit-logs/employee/{employee_id}")
def get_audit_logs_by_employee(employee_id: str, db: Session = Depends(get_db)):
    logs = db.query(AuditLogDB).filter(AuditLogDB.Employee_ID == employee_id).all()
    return logs
