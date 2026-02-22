from fastapi import FastAPI, Request, status, UploadFile, File, Form
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import time

from backend.core.config import logger
from backend.core.database import Base, engine
from backend.schemas import GenerationRequest, GenerationResponse, ErrorResponse, TargetLanguage, InputMode
import backend.models  # Requires this import to register Models to SQLAlchemy

# Import input processors
from backend.input.handlers import process_natural_language, process_pasted_code, process_file_upload

# Automatically create initialization if SQLite
try:
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables verified/created.")
except Exception as e:
    logger.critical(f"Database initialization failed: {e}")

app = FastAPI(
    title="AI Test Generator API",
    description="Backend for AI-Powered Test Case Generator",
    version="1.0.0"
)

# CORS configuration for Streamlit connections
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, restrict to frontend deployment URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global Exception Handler (Edge Case: Prevent raw stack traces)
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception on {request.method} {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An internal server error occurred. Please try again later."},
    )

# Middleware for timing and tracking usage
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    logger.info(f"Incoming request: {request.method} {request.url.path}")
    
    response = await call_next(request)
    
    process_time = (time.time() - start_time) * 1000  # Convert to ms
    logger.info(f"Completed request: {request.method} {request.url.path} - Status: {response.status_code} - Time: {process_time:.2f}ms")
    
    return response

@app.get("/api/health")
def health_check():
    return {"status": "ok"}

@app.post("/api/generate/text", response_model=GenerationResponse, responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}})
def generate_tests_from_text(request: GenerationRequest):
    """Processes Natural Language OR Pasted Code."""
    logger.info(f"Text-based generation started | Mode: {request.input_mode.value} | Language: {request.language.value}")
    
    if request.input_mode == InputMode.natural_language:
        unified_input = process_natural_language(request.content, request.language)
    elif request.input_mode == InputMode.pasted_code:
        unified_input = process_pasted_code(request.content, request.language)
    else:
        return JSONResponse(status_code=400, content={"detail": "Invalid input mode for this endpoint."})
        
    # Pass the Unified Object into Phase 3 LangChain Orchestrator
    try:
        from backend.agents.orchestrator import process_generation_flow
        agent_result = process_generation_flow(unified_input, request.options)
        
        # Determine if clarification stopped the flow
        if agent_result["status"] == "clarification_needed":
            return GenerationResponse(
                job_id=999,
                generated_test_code="",
                warnings=[f"Clarification specific to your prompt: \n{agent_result['message']}"]
            )
            
        return GenerationResponse(
            job_id=999,
            generated_test_code=agent_result["code"],
            quality_score=0.0, # Phase 4 evaluation pending
            warnings=unified_input.warnings + ([] if agent_result["status"] == "success" else [agent_result["message"]])
        )
    except Exception as e:
        logger.error(f"Agent Orchestrator failed: {e}")
        return JSONResponse(status_code=500, content={"detail": f"Agent generation crashed: {str(e)}"})

@app.post("/api/generate/file", response_model=GenerationResponse, responses={400: {"model": ErrorResponse}, 413: {"model": ErrorResponse}, 500: {"model": ErrorResponse}})
async def generate_tests_from_file(file: UploadFile = File(...)):
    """Processes uploaded source code files."""
    logger.info(f"File-based generation started | File: {file.filename}")
    
    unified_input = await process_file_upload(file)
    # Pass the Unified Object into Phase 3 LangChain Orchestrator
    try:
        from backend.agents.orchestrator import process_generation_flow
        from backend.schemas import GenerationOptions
        
        # File uploads use default options for now since FormData lacks nested params easily
        options = GenerationOptions() 
        agent_result = process_generation_flow(unified_input, options)
        
        return GenerationResponse(
            job_id=999,
            generated_test_code=agent_result["code"],
            quality_score=0.0, # Phase 4 evaluation pending
            warnings=unified_input.warnings + ([] if agent_result["status"] == "success" else [agent_result["message"]])
        )
    except Exception as e:
        logger.error(f"Agent Orchestrator failed on file processing: {e}")
        return JSONResponse(status_code=500, content={"detail": f"Agent generation crashed: {str(e)}"})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
