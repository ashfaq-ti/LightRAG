from fastapi import FastAPI, HTTPException, File, UploadFile, WebSocket,WebSocketException
from pydantic import BaseModel
import os
from lightrag import LightRAG, QueryParam
from lightrag.llm import ollama_embed, ollama_model_complete
from lightrag.utils import EmbeddingFunc
from typing import Optional
import asyncio
import nest_asyncio
import aiofiles
import inspect
# # neo4j
BATCH_SIZE_NODES = 500
BATCH_SIZE_EDGES = 100
os.environ["NEO4J_URI"] = "bolt://localhost:7687"
os.environ["NEO4J_USERNAME"] = "neo4j"
os.environ["NEO4J_PASSWORD"] = "password"

# # milvus
os.environ["MILVUS_URI"] = "http://127.0.0.1:19530"
os.environ["MILVUS_USER"] = "root"
os.environ["MILVUS_PASSWORD"] = "root"
os.environ["MILVUS_DB_NAME"] = "lightrag1"

#mongo
# os.environ["MONGO_URI"] = "mongodb+srv://lokeshdande:vkurQ05x5pqPOZUM@cluster0.ce8rn.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
os.environ["MONGO_URI"] = "mongodb+srv://aceprimenum:G8ahSD5QZWa3ixJ7@cluster0.31xjj.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
os.environ["MONGO_DATABASE"] = "lightrag1"

# Apply nest_asyncio to solve event loop issues
nest_asyncio.apply()

DEFAULT_RAG_DIR = "/home/technoidentity/Desktop/local_test_llama3.1"
# DEFAULT_RAG_DIR = "/home/technoidentity/Desktop/testing"
app = FastAPI(title="LightRAG API", description="API for RAG operations")

# DEFAULT_INPUT_FILE = "book.txt"
# INPUT_FILE = os.environ.get("INPUT_FILE", f"{DEFAULT_INPUT_FILE}")
# print(f"INPUT_FILE: {INPUT_FILE}")

# Configure working directory
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
WORKING_DIR = os.path.join(ROOT_DIR, f"{DEFAULT_RAG_DIR}")
if not os.path.exists(WORKING_DIR):
    os.mkdir(WORKING_DIR)
print(f"WorkingDir: {WORKING_DIR}")
# WORKING_DIR = os.environ.get("RAG_DIR", f"{DEFAULT_RAG_DIR}")
# print(f"WORKING_DIR: {WORKING_DIR}")

if not os.path.exists(WORKING_DIR):
    os.mkdir(WORKING_DIR)

async def ini_rag():
    rag = LightRAG(
        working_dir=WORKING_DIR,
        llm_model_func=ollama_model_complete,
        # llm_model_name="phi4:14b-q8_0",
        # llm_model_name="qwen2.5",
        llm_model_name="llama3.1",
        llm_model_max_async=4,
        llm_model_max_token_size=32768,
        llm_model_kwargs={"host": "http://183.82.7.112:9066/", "options": {"num_ctx": 32768}},
        embedding_func=EmbeddingFunc(
            embedding_dim=1024,
            max_token_size=8192,
            func=lambda texts: ollama_embed(
                texts=texts, embed_model="bge-m3:latest", host="http://183.82.7.112:9066/"
            ),
            # embedding_dim=768,
            # max_token_size=8192,
            # func=lambda texts: ollama_embed(
            #     texts=texts, embed_model="nomic-embed-text", host="http://183.82.7.112:9066/"
            # ),
            
            
        ),
        kv_storage="MongoKVStorage",
        graph_storage="Neo4JStorage",
        vector_storage="MilvusVectorDBStorge",
    )
    return rag
rag = asyncio.run(ini_rag())
with open("/home/technoidentity/LightRAG/outputTest.md", "r", encoding="utf-8") as f:
    rag.insert(f.read())

# Data models
class QueryRequest(BaseModel):
    query: str
    mode: str = "hybrid"
    only_need_context: bool = False
    only_need_prompt: bool = False


class InsertRequest(BaseModel):
    text: str


class Response(BaseModel):
    status: str
    data: Optional[str] = None
    message: Optional[str] = None


# API routes

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()

    # Receive prompt
    prompt = await websocket.receive_text()
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        None,
        lambda: rag.query(
            prompt,
            param=QueryParam(
                mode="hybrid",stream=True
            ),
        ),
    )
    async def print_stream(stream):
        async for chunk in stream:
            await websocket.send_text(chunk)
    if inspect.isasyncgen(result):
        asyncio.run(print_stream(result))
    else:
        raise Exception("Response is not an async generator, which is required for Streaming, There may be a problem with inner dependencies or their connections.")
    await websocket.close()
    
@app.post("/query", response_model=Response)
async def query_endpoint(request: QueryRequest):
    try:
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: rag.query(
                request.query,
                param=QueryParam(
                    mode=request.mode, only_need_context=request.only_need_context, only_need_prompt=request.only_need_prompt
                ),
            ),
        )
        return Response(status="success", data=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# insert by text
@app.post("/insert", response_model=Response)
async def insert_endpoint(request: InsertRequest):
    try:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, lambda: rag.insert(request.text))
        return Response(status="success", message="Text inserted successfully")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# insert by file in payload
@app.post("/insert_file", response_model=Response)
async def insert_file(file: UploadFile = File(...)):
    try:
        file_content = await file.read()
        # Read file content
        try:
            content = file_content.decode("utf-8")
        except UnicodeDecodeError:
            # If UTF-8 decoding fails, try other encodings
            content = file_content.decode("gbk")
        # Insert file content
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, lambda: rag.insert(content))

        return Response(
            status="success",
            message=f"File content from {file.filename} inserted successfully",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# insert by local default file
# @app.post("/insert_default_file", response_model=Response)
# @app.get("/insert_default_file", response_model=Response)
# async def insert_default_file():
#     try:
#         # Read file content from book.txt
#         async with aiofiles.open(INPUT_FILE, "r", encoding="utf-8") as file:
#             content = await file.read()
#         print(f"read input file {INPUT_FILE} successfully")
#         # Insert file content
#         loop = asyncio.get_event_loop()
#         await loop.run_in_executor(None, lambda: rag.insert(content))

#         return Response(
#             status="success",
#             message=f"File content from {INPUT_FILE} inserted successfully",
#         )
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8020, loop='asyncio')
    # uvicorn.run(app, host="0.0.0.0", port=8020)

# Usage example
# To run the server, use the following command in your terminal:
# python lightrag_api_openai_compatible_demo.py

# Example requests:
# 1. Query:
# curl -X POST "http://127.0.0.1:8020/query" -H "Content-Type: application/json" -d '{"query": "your query here", "mode": "hybrid"}'

# 2. Insert text:
# curl -X POST "http://127.0.0.1:8020/insert" -H "Content-Type: application/json" -d '{"text": "your text here"}'

# 3. Insert file:
# curl -X POST "http://127.0.0.1:8020/insert_file" -H "Content-Type: application/json" -d '{"file_path": "path/to/your/file.txt"}'

# 4. Health check:
# curl -X GET "http://127.0.0.1:8020/health"
