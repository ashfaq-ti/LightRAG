from fastapi import FastAPI, HTTPException, File, UploadFile, WebSocket,WebSocketException
from pydantic import BaseModel
import os
from dotenv import load_dotenv
from lightrag import LightRAG, QueryParam
from lightrag.llm import ollama_embed, ollama_model_complete
from lightrag.utils import EmbeddingFunc
from typing import Optional
import asyncio
import nest_asyncio
import aiofiles
import inspect

load_dotenv()
BATCH_SIZE_NODES = 500
BATCH_SIZE_EDGES = 100
os.environ["NEO4J_URI"] = os.getenv("NEO4J_URI")
os.environ["NEO4J_USERNAME"] = os.getenv("NEO4J_USERNAME")
os.environ["NEO4J_PASSWORD"] = os.getenv("NEO4J_PASSWORD")

os.environ["MILVUS_URI"] = os.getenv("MILVUS_URI")
os.environ["MILVUS_USER"] = os.getenv("MILVUS_USER")
os.environ["MILVUS_PASSWORD"] = os.getenv("MILVUS_PASSWORD")
os.environ["MILVUS_DB_NAME"] = os.getenv("MILVUS_DB_NAME")

os.environ["MONGO_URI"] = os.getenv("MONGO_URI")
os.environ["MONGO_DATABASE"] = os.getenv("MONGO_DATABASE")

# Apply nest_asyncio to solve event loop issues
nest_asyncio.apply()

DEFAULT_RAG_DIR = "/home/technoidentity/Desktop/phi_cit_test_local"
app = FastAPI(title="LightRAG API", description="API for RAG operations")

# Configure working directory
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
WORKING_DIR = os.path.join(ROOT_DIR, f"{DEFAULT_RAG_DIR}")
if not os.path.exists(WORKING_DIR):
    os.mkdir(WORKING_DIR)

async def ini_rag():
    rag = LightRAG(
        working_dir=WORKING_DIR,
        llm_model_func=ollama_model_complete,
        # llm_model_name="phi4:14b-q8_0",
        # llm_model_name="phi4:14b-q4_K_M",
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
        ),
        kv_storage="MongoKVStorage",
        graph_storage="Neo4JStorage",
        vector_storage="MilvusVectorDBStorge",
    )
    return rag
rag = asyncio.run(ini_rag())
with open("/home/technoidentity/LightRAG/outputLlama.md", "r", encoding="utf-8") as f:
    rag.insert(f.read())

# Data models
class QueryRequest(BaseModel):
    prompt: str
    mode: str = "hybrid"
    only_need_context: bool = False
    only_need_prompt: bool = False
    kgContextOnly: bool = True


class InsertRequest(BaseModel):
    text: str


class Response(BaseModel):
    status: str
    data: Optional[str] = None
    message: Optional[str] = None


# API routes

# @app.websocket("/ws")
# async def websocket_endpoint(websocket: WebSocket):
#     await websocket.accept()

#     # Receive prompt
#     prompt = await websocket.receive_text()
#     loop = asyncio.get_event_loop()
#     result = await loop.run_in_executor(
#         None,
#         lambda: rag.query(
#             prompt,
#             param=QueryParam(
#                 mode="hybrid",stream=True
#             ),
#         ),
#     )
#     async def print_stream(stream):
#         async for chunk in stream:
#             await websocket.send_text(chunk)
#     if inspect.isasyncgen(result):
#         asyncio.run(print_stream(result))
#     else:
#         raise Exception("Response is not an async generator, which is required for Streaming, There may be a problem with inner dependencies or their connections.")
#     await websocket.close()
    
@app.post("/query", response_model=Response)
async def query_endpoint(request: QueryRequest):
    try:
        loop = asyncio.get_event_loop()
        prompt_inclusive_of_citation_request = f"{request.prompt} also Provide top level reference document names and relevant page numbers ONLY IF THEY ARE RELATED TO THE USER'S QUESTION . DO NOT MENTION ABOUT ENTITIES OR RELATIONSHIPS OR DATA TABLES. ALSO CONSOLIDATE ALL PAGE NUMBERS AT THE END OF RESPONSE for eg. Page numbers : 30,57,23"
        # prompt_inclusive_of_citation_request = f"{request.prompt}"
        result = await loop.run_in_executor(
            None,
            lambda: rag.query(
                prompt_inclusive_of_citation_request,
                param=QueryParam(
                    mode=request.mode, only_need_context=request.only_need_context, only_need_prompt=request.only_need_prompt, kgContextOnly=request.kgContextOnly
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

    # uvicorn.run(app, host="0.0.0.0", port=8020, loop='asyncio')
    uvicorn.run(app, host="0.0.0.0", port=8020)
