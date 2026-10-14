from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

class DownloadRecord(Base):
    __tablename__ = "download_records"
    
    __table_args__ = (
        CheckConstraint(
          "access_type IN "
          "('view', 'download', 'blocked')",
            name="ck_download_records_valid_access_type"
        ),
    )
    
    id : Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    
    # Foreign keys
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    resource_id: Mapped[int] = mapped_column(
        ForeignKey("resources.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Access information
    access_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    
    # Timestamps
    accessed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)
    
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    
    user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True)
    
    # Relationships
    user: Mapped["User"] = relationship()
    
    resource: Mapped["Resource"] = relationship()
    
    
    
    