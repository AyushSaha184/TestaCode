from sqlalchemy import Column, Integer, String, Text, DateTime, Float, ForeignKey
from sqlalchemy.orm import relationship
import datetime
from backend.core.database import Base

class GenerationJob(Base):
    __tablename__ = "generation_jobs"

    id = Column(Integer, primary_key=True, index=True)
    input_text = Column(Text, nullable=True)
    mode = Column(String, index=True, nullable=False) # natural_language, pasted_code, file_upload
    language = Column(String, index=True, nullable=False) # python, javascript
    status = Column(String, default="pending", nullable=False) # pending, completed, failed
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)

    # Relationship setup (Cascade delete for results)
    test_results = relationship("TestRunResult", back_populates="job", cascade="all, delete-orphan")


class TestRunResult(Base):
    __tablename__ = "test_run_results"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("generation_jobs.id"), nullable=False)
    pass_count = Column(Integer, default=0)
    fail_count = Column(Integer, default=0)
    coverage_percentage = Column(Float, nullable=True)
    ci_run_url = Column(String, nullable=True)

    job = relationship("GenerationJob", back_populates="test_results")
