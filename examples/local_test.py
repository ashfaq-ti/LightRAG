from fastapi import FastAPI, HTTPException, File, UploadFile, WebSocket, WebSocketException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
import os
import asyncio
import logging
import aiofiles
from functools import lru_cache
from datetime import datetime
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from contextlib import asynccontextmanager

from lightrag import LightRAG, QueryParam
from lightrag.llm import ollama_embed, ollama_model_complete
from lightrag.utils import EmbeddingFunc

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration class
class Settings:
    def __init__(self):
        # Neo4j settings
        self.NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        self.NEO4J_USERNAME = os.getenv("NEO4J_USERNAME", "neo4j")
        self.NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")
        
        # Milvus settings
        self.MILVUS_URI = os.getenv("MILVUS_URI", "http://127.0.0.1:19530")
        self.MILVUS_USER = os.getenv("MILVUS_USER", "root")
        self.MILVUS_PASSWORD = os.getenv("MILVUS_PASSWORD", "root")
        self.MILVUS_DB_NAME = os.getenv("MILVUS_DB_NAME", "phiDB")
        
        # MongoDB settings
        self.MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
        self.MONGO_DATABASE = os.getenv("MONGO_DATABASE", "phiDB")
        
        # RAG settings
        self.DEFAULT_RAG_DIR = os.getenv("RAG_DIR", "/home/technoidentity/Desktop/phi_cit_test_local")
        self.LLM_MODEL_NAME = os.getenv("LLM_MODEL_NAME", "phi4:14b-q8_0")
        self.LLM_HOST = os.getenv("LLM_HOST", "http://183.82.7.112:9066/")
        
        # Ensure working directory exists
        if not os.path.exists(self.DEFAULT_RAG_DIR):
            os.makedirs(self.DEFAULT_RAG_DIR)

@lru_cache()
def get_settings():
    return Settings()

# Initialize rate limiter (limits the number of requests per IP)
def get_limiter() -> Limiter:
    return Limiter(key_func=get_remote_address)

# RAG instance management
class RAGManager:
    _instance: Optional[LightRAG] = None
    _lock = asyncio.Lock()
    
    @classmethod
    async def get_instance(cls) -> LightRAG:
        if cls._instance is None:
            async with cls._lock:
                if cls._instance is None:
                    settings = get_settings()
                    cls._instance = await cls._initialize_rag(settings)
        return cls._instance
    
    @staticmethod
    async def _initialize_rag(settings: Settings) -> LightRAG:
        try:
            rag = LightRAG(
                working_dir=settings.DEFAULT_RAG_DIR,
                llm_model_func=ollama_model_complete,
                llm_model_name=settings.LLM_MODEL_NAME,
                llm_model_max_async=4,
                llm_model_max_token_size=32768,
                llm_model_kwargs={
                    "host": settings.LLM_HOST,
                    "options": {"num_ctx": 32768}
                },
                embedding_func=EmbeddingFunc(
                    embedding_dim=1024,
                    max_token_size=8192,
                    func=lambda texts: ollama_embed(
                        texts=texts,
                        embed_model="bge-m3:latest",
                        host=settings.LLM_HOST
                    ),
                ),
                kv_storage="MongoKVStorage",
                graph_storage="Neo4JStorage",
                vector_storage="MilvusVectorDBStorge",
            )
            return rag
        except Exception as e:
            logger.error(f"Failed to initialize RAG: {str(e)}")
            raise

# FastAPI app initialization with lifespan
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting up LightRAG API")
    await RAGManager.get_instance()
    yield
    # Shutdown
    logger.info("Shutting down LightRAG API")

app = FastAPI(
    title="LightRAG API",
    description="Production-ready API for RAG operations",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add rate limiter error handler
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Data models with validation
class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=1000)
    mode: str = Field(default="hybrid", pattern="^(hybrid|semantic|keyword)$")
    only_need_context: bool = Field(default=False)
    only_need_prompt: bool = Field(default=False)

class InsertRequest(BaseModel):
    text: str = Field(..., min_length=1)

class Response(BaseModel):
    status: str
    data: Optional[str] = None
    message: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

# Dependency for getting RAG instance
async def get_rag():
    return await RAGManager.get_instance()

# Exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Global exception handler caught: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"status": "error", "message": "Internal server error"}
    )

# WebSocket endpoint
@app.websocket("/ws")
@limiter.limit("60/minute")
async def websocket_endpoint(
    websocket: WebSocket,
    rag: LightRAG = Depends(get_rag)
):
    try:
        await websocket.accept()
        while True:
            try:
                data = await websocket.receive_json()
                query = data.get("query")
                if not query:
                    await websocket.send_json({"error": "Query is required"})
                    continue
                
                result = await rag.aquery(
                    query=query,
                    query_param=QueryParam(
                        mode=data.get("mode", "hybrid"),
                        only_need_context=data.get("only_need_context", False),
                        only_need_prompt=data.get("only_need_prompt", False)
                    )
                )
                await websocket.send_json({"result": result})
                
            except WebSocketException:
                logger.error("WebSocket error", exc_info=True)
                break
            except Exception as e:
                logger.error(f"Error processing WebSocket message: {str(e)}", exc_info=True)
                await websocket.send_json({"error": str(e)})
                
    except Exception as e:
        logger.error(f"WebSocket connection error: {str(e)}", exc_info=True)
        raise
    finally:
        await websocket.close()

# Query endpoint
@app.post("/query", response_model=Response)
@limiter.limit("30/minute")
async def query_endpoint(
    request: QueryRequest,
    background_tasks: BackgroundTasks,
    rag: LightRAG = Depends(get_rag)
):
    try:
        result = await rag.aquery(
            query=request.query,
            query_param=QueryParam(
                mode=request.mode,
                only_need_context=request.only_need_context,
                only_need_prompt=request.only_need_prompt
            )
        )
        return Response(status="success", data=result)
    except Exception as e:
        logger.error(f"Query error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

# Insert text endpoint
@app.post("/insert", response_model=Response)
@limiter.limit("10/minute")
async def insert_endpoint(
    request: InsertRequest,
    background_tasks: BackgroundTasks,
    rag: LightRAG = Depends(get_rag)
):
    try:
        background_tasks.add_task(rag.insert, request.text)
        return Response(
            status="success",
            message="Text queued for insertion"
        )
    except Exception as e:
        logger.error(f"Insert error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

# Insert file endpoint
@app.post("/insert_file", response_model=Response)
@limiter.limit("5/minute")
async def insert_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    rag: LightRAG = Depends(get_rag)
):
    try:
        if file.content_type not in ["text/plain", "application/json", "text/markdown"]:
            raise HTTPException(
                status_code=400,
                detail="Only text, JSON, and markdown files are supported"
            )
            
        file_content = await file.read()
        try:
            content = file_content.decode("utf-8")
            background_tasks.add_task(rag.insert, content)
            return Response(
                status="success",
                message="File content queued for insertion"
            )
        except UnicodeDecodeError:
            raise HTTPException(
                status_code=400,
                detail="File must be UTF-8 encoded"
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"File insert error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

# Health check endpoint
@app.get("/health", response_model=Response)
async def health_check():
    try:
        rag = await RAGManager.get_instance()
        return Response(
            status="healthy",
            message="Service is running"
        )
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}", exc_info=True)
        return Response(
            status="unhealthy",
            message=str(e)
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "local:app",
        host="0.0.0.0",
        port=8020,
        reload=False,
        workers=1,
        log_level="info"
    )
