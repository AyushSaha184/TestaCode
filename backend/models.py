from sqlalchemy import Column, Integer, String, Text, DateTime, Float, ForeignKey
from sqlalchemy.orm import relationship
import datetime
from backend.core.database import Base


class GenerationJob(Base):
    __tablename__ = "generation_jobs"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    input_mode = Column(String, index=True, nullable=False)  # paste, upload
    original_filename = Column(String, nullable=True)  # only set when input_mode=upload
    language = Column(String, index=True, nullable=False)  # python, javascript, typescript, java
    raw_prompt = Column(Text, nullable=True)  # the user's free-text instruction
    classified_intent = Column(Text, nullable=True)  # JSON string of classified intent
    generated_test_code = Column(Text, nullable=True)  # the generated test output
    quality_score = Column(Float, nullable=True)  # 0-10 self-evaluation score
    status = Column(String, default="pending", nullable=False)  # pending, processing, completed, failed

    # Relationship setup (Cascade delete for results)
    test_results = relationship("TestRunResult", back_populates="job", cascade="all, delete-orphan")


class TestRunResult(Base):
    __tablename__ = "test_run_results"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("generation_jobs.id"), nullable=False)
    pass_count = Column(Integer, default=0)
    fail_count = Column(Integer, default=0)
    error_count = Column(Integer, default=0)
    coverage_percentage = Column(Float, nullable=True)
    ci_run_url = Column(String, nullable=True)
    run_timestamp = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)

    job = relationship("GenerationJob", back_populates="test_results")
