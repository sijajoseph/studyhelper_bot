# -----------------------------------------
# ✅ BACKEND: FastAPI (rag_backend.py)
# -----------------------------------------
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from llama_index.core import VectorStoreIndex, Settings
from llama_index.readers.file import PDFReader
from llama_index.core.node_parser import SimpleNodeParser
from langchain.chat_models import ChatOpenAI
from typing import List, Dict, Union
import tempfile, shutil, os
import re

app: FastAPI = FastAPI()

# CORS (allow frontend to access backend)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global state
query_engine = None
index: Union[VectorStoreIndex, None] = None
file_lookup: Dict[str, str] = {}
topic_mapping: Dict[int, Dict[str, str]] = {}

os.environ["OPENAI_API_KEY"] = "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"
llm: ChatOpenAI = ChatOpenAI(model_name="gpt-3.5-turbo", temperature=0.7)
Settings.llm = llm

@app.post("/upload")
async def upload_and_index(files: List[UploadFile] = File(...)) -> Dict:
    global query_engine, topic_mapping, file_lookup

    if not files:
        return JSONResponse(content={"error": "No files uploaded."}, status_code=400)

    parser: SimpleNodeParser = SimpleNodeParser()
    reader: PDFReader = PDFReader()

    topic_mapping.clear()
    file_lookup.clear()
    all_docs: List = []
    topic_idx: int = 0

    temp_dir: str = tempfile.mkdtemp()

    for file in files:
        file_path: str = os.path.join(temp_dir, file.filename)
        with open(file_path, "wb") as f:
            f.write(await file.read())
        file_lookup[file.filename] = file_path

        docs = reader.load_data(file=file_path)
        all_docs.extend(docs)

        nodes = parser.get_nodes_from_documents(docs)
        seen: set = set()
        
        for node in nodes:
            if topic_idx >= 20:
                break
            lines = node.text.strip().split("\n")
            for line in lines:
                line = line.strip()

                # Skip short, duplicate, or garbage lines
                if not line or len(line) < 10 or line.lower() in seen:
                    continue

                # Accept lines that look like numbered headings or long titles
                is_heading = bool(re.match(r"^\d+(\.\d+)*\s+.+", line))  # e.g., 2.1 Introduction
                is_title = line.istitle() and len(line.split()) >= 2     # e.g., Problem Definition

                if is_heading or is_title:
                    topic = line
                    page: str = node.metadata.get("page_label", '0')
                    print(node.metadata)
                    topic_mapping[topic_idx] = {
                        "file": file.filename,
                        "page": page,
                        "topic": topic
                    }
                    seen.add(line.lower())
                    topic_idx += 1
                    break




    index = VectorStoreIndex.from_documents(all_docs)
    query_engine = index.as_query_engine()
    print('\n',topic_mapping,'\n')
    return {"status": "success", "topics": topic_mapping}

@app.post("/ask")
async def ask_question(question: str = Form(...)) -> Dict[str, str]:
    if query_engine is None:
        return JSONResponse(content={"error": "Upload PDFs first."}, status_code=400)
    response = query_engine.query(question)
    return {"question": question, "answer": str(response)}

@app.get("/topics")
def get_topics() -> Dict[int, Dict[str, str]]:
    return topic_mapping

@app.get("/pdf/{filename}")
def get_pdf_path(filename: str) :
    path: Union[str, None] = file_lookup.get(filename)
    return {"path": path} if path else JSONResponse(content={"error": "Not found."}, status_code=404)


# Run with: uvicorn rag_backend:app --reload
