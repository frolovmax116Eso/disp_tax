"""Database models."""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey, JSON, Enum as SQLEnum
from sqlalchemy.orm import relationship
from datetime import datetime
from enum import Enum
from src.database.base import Base


class OrderState(Enum):
    """Order FSM states."""
    DRAFT = "draft"
    PREVIEW = "preview"
    CONFIRMED = "confirmed"
    SENDING = "sending"
    ACTIVE = "active"
    ASSIGNED = "assigned"
    CLOSED = "closed"
    CANCELLED = "cancelled"


class ResponseType(Enum):
    """Driver response types."""
    YA = "ya"
    REPLY = "reply"


class Dispatcher(Base):
    """Dispatcher model."""
    __tablename__ = "dispatchers"
    
    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, nullable=False, index=True)
    username = Column(String, nullable=True)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=True)
    session_file = Column(String, nullable=False)
    session_active = Column(Boolean, default=False, index=True)
    session_expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    orders = relationship("Order", back_populates="dispatcher")
    groups = relationship("Group", back_populates="dispatcher")
    regions = relationship("Region", back_populates="dispatcher")
    scenarios = relationship("Scenario", back_populates="dispatcher")


class Order(Base):
    """Order model."""
    __tablename__ = "orders"
    
    id = Column(Integer, primary_key=True)
    dispatcher_id = Column(Integer, ForeignKey("dispatchers.id"), nullable=False, index=True)
    state = Column(SQLEnum(OrderState), nullable=False, index=True)
    content = Column(Text, nullable=False)
    normalized_content = Column(Text, nullable=False)
    is_vip = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    confirmed_at = Column(DateTime, nullable=True)
    sent_at = Column(DateTime, nullable=True)
    closed_at = Column(DateTime, nullable=True)
    
    # Relationships
    dispatcher = relationship("Dispatcher", back_populates="orders")
    responses = relationship("DriverResponse", back_populates="order")
    assignments = relationship("Assignment", back_populates="order")
    group_messages = relationship("GroupMessage", back_populates="order")
    history = relationship("OrderHistory", back_populates="order")


class DriverResponse(Base):
    """Driver response model."""
    __tablename__ = "driver_responses"
    
    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False, index=True)
    group_id = Column(Integer, ForeignKey("groups.id"), nullable=False)
    driver_telegram_id = Column(Integer, nullable=False, index=True)
    driver_username = Column(String, nullable=True)
    driver_name = Column(String, nullable=False)
    driver_phone = Column(String, nullable=True)
    response_text = Column(Text, nullable=False)
    response_type = Column(SQLEnum(ResponseType), nullable=False)
    message_id = Column(Integer, nullable=False)
    replied_to_message_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Relationships
    order = relationship("Order", back_populates="responses")
    group = relationship("Group", back_populates="responses")


class Assignment(Base):
    """Assignment model."""
    __tablename__ = "assignments"
    
    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False, index=True)
    driver_telegram_id = Column(Integer, nullable=False, index=True)
    driver_username = Column(String, nullable=True)
    driver_name = Column(String, nullable=False)
    assigned_by = Column(Integer, nullable=False)
    reason = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, index=True)
    assigned_at = Column(DateTime, default=datetime.utcnow)
    unassigned_at = Column(DateTime, nullable=True)
    
    # Relationships
    order = relationship("Order", back_populates="assignments")


class Group(Base):
    """Group model."""
    __tablename__ = "groups"
    
    id = Column(Integer, primary_key=True)
    dispatcher_id = Column(Integer, ForeignKey("dispatchers.id"), nullable=False, index=True)
    telegram_group_id = Column(Integer, nullable=False)
    title = Column(String, nullable=False)
    region_id = Column(Integer, ForeignKey("regions.id"), nullable=True)
    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    dispatcher = relationship("Dispatcher", back_populates="groups")
    region = relationship("Region", back_populates="groups")
    responses = relationship("DriverResponse", back_populates="group")
    messages = relationship("GroupMessage", back_populates="group")


class Region(Base):
    """Region model."""
    __tablename__ = "regions"
    
    id = Column(Integer, primary_key=True)
    dispatcher_id = Column(Integer, ForeignKey("dispatchers.id"), nullable=False, index=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    dispatcher = relationship("Dispatcher", back_populates="regions")
    groups = relationship("Group", back_populates="region")


class Scenario(Base):
    """Scenario model."""
    __tablename__ = "scenarios"
    
    id = Column(Integer, primary_key=True)
    dispatcher_id = Column(Integer, ForeignKey("dispatchers.id"), nullable=False, index=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    group_ids = Column(JSON, nullable=False)  # List[int]
    delay_min = Column(Integer, nullable=False)
    delay_max = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    dispatcher = relationship("Dispatcher", back_populates="scenarios")


class Admin(Base):
    """Admin model."""
    __tablename__ = "admins"
    
    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, nullable=False, index=True)
    username = Column(String, nullable=True)
    first_name = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_access_at = Column(DateTime, nullable=True)
    
    # Relationships
    access_logs = relationship("AdminAccessLog", back_populates="admin")


class AdminAccessLog(Base):
    """Admin access log model."""
    __tablename__ = "admin_access_logs"
    
    id = Column(Integer, primary_key=True)
    admin_id = Column(Integer, ForeignKey("admins.id"), nullable=False, index=True)
    action = Column(String, nullable=False)
    details = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Relationships
    admin = relationship("Admin", back_populates="access_logs")


class OrderHistory(Base):
    """Order history model."""
    __tablename__ = "order_history"
    
    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False, index=True)
    old_state = Column(SQLEnum(OrderState), nullable=True)
    new_state = Column(SQLEnum(OrderState), nullable=False)
    changed_by = Column(Integer, nullable=False)
    change_reason = Column(Text, nullable=True)
    changes = Column(JSON, nullable=False)  # Dict with change details
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    order = relationship("Order", back_populates="history")


class GroupMessage(Base):
    """Group message model."""
    __tablename__ = "group_messages"
    
    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False, index=True)
    group_id = Column(Integer, ForeignKey("groups.id"), nullable=False)
    telegram_message_id = Column(Integer, nullable=False, index=True)
    message_text = Column(Text, nullable=False)
    sent_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=True)
    is_deleted = Column(Boolean, default=False)
    
    # Relationships
    order = relationship("Order", back_populates="group_messages")
    group = relationship("Group", back_populates="messages")

