import uuid
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = db.Column(db.String, nullable=False)
    role = db.Column(db.String, nullable=False)  # "student" or "staff"
    student = relationship("Student", back_populates="user", uselist=False)

class Student(db.Model):
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey('user.id'), nullable=False)
    reg_no = db.Column(db.String, unique=True)
    department = db.Column(db.String)
    semester = db.Column(db.Integer)
    cgpa = db.Column(db.Numeric(3,2))
    attendance = db.Column(db.Numeric(5,2))
    
    user = relationship("User", back_populates="student")
    marks = relationship("Mark", back_populates="student")

class Mark(db.Model):
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    student_id = db.Column(UUID(as_uuid=True), db.ForeignKey('student.id'), nullable=False)
    semester = db.Column(db.Integer)
    subject = db.Column(db.String)
    internal = db.Column(db.Integer)
    external = db.Column(db.Integer)
    total = db.Column(db.Integer)
    
    student = relationship("Student", back_populates="marks") 