# AI Learning Assistant FastAPI Backend

This is a personalized learning roadmap generator, project recommender, and RAG-backed conversation helper built as an internship assignment for **Get Set Skilled**.

---

## 1. Architecture Overview

### System Workflow
```
+-----------------------------------------------------------------------------------+
|                                 FASTAPI APP                                       |
+-----------------------------------------------------------------------------------+
       |                                   |                                  |
       v                                   v                                  v
 [POST /roadmap]                    [POST /project]                    [POST /chat]
       |                                   |                                  |
  (Generate uuid)                          |                         (Check cache hit?)
       |                                   |                         - Yes -> Return
  (Query Groq)                             |                         - No -> RAG flow
       |                                   |                                  |
       v                                   v                                  v
[Store in Memory DB]              [LLM Recommendation]             [Retrieve context]
       |                                                               (Top 3-4 chunks)
  (Chunk & Embed)                                                             |
       |                                                                 (Query Groq)
       v                                                                      |
 [Local ChromaDB]                                                             v
                                                                      [Store in Cache]
```

### RAG Design & Semantic Cache Decisions

#### 1. Chunking by Task (Natural Boundaries)
Instead of dividing the roadmap into arbitrary fixed-length character chunks (which breaks up sentences and splits subtasks across different chunks), we chunk the data along **natural boundary lines**:
- **Roadmap Summary Chunk**: Summarizes the overall learning goal, recommended skills, and total estimated study time.
- **Roadmap Task Chunks**: One chunk per task including its title, estimated hours, and a combined list of its subtasks.

*Why?* Chunking by task preserves the contextual integrity of each roadmap step. When a user asks about a specific task, the entire task (along with its estimated hours and subtasks) is retrieved together.

#### 2. Local Embeddings (`all-MiniLM-L6-v2`)
We use a local Hugging Face `all-MiniLM-L6-v2` model through ChromaDB's default embedding utilities.

*Why?* 
- **Cost**: No external API keys or pay-per-token charges.
- **Latency**: Runs entirely on the local CPU/GPU, eliminating network overhead for embedding generation.
- **Privacy**: Embeddings are computed locally without sending student queries to third parties.

#### 3. Scoped Per-Roadmap Collections
For every generated roadmap, we dynamically instantiate a unique ChromaDB collection named `roadmap_<roadmap_id>`. Similarly, semantic caching is isolated in `cache_<roadmap_id>`.

*Why?* This provides **tenant isolation**. A user querying their own backend developer roadmap will never retrieve chunks or cache hits from another user's frontend developer roadmap, preventing data leakage.

#### 4. Semantic Cache Caching
Before querying the LLM, `/chat` converts the incoming question into an embedding and queries `cache_<roadmap_id>` (configured in **Cosine Similarity space**). If the closest cached question has a cosine similarity of **0.92 or greater** (Chroma distance of `0.08` or less), we return the cached response immediately, bypassing the LLM.

*Why?* Saves LLM API costs and reduces latency to milliseconds on repeated or rephrased questions.

---

## 2. Setup Instructions

### Environment Variables
Create a `.env` file in the project root containing your Groq API key:
```env
GROQ_API_KEY=gsk_your_actual_groq_api_key
CHROMA_DB_PATH=./chroma_db
HOST=0.0.0.0
PORT=8000
```

### Installation
Make sure you have Python 3.11+ installed. Run:
```bash
pip install -r requirements.txt
```

### Running the App
Start the Uvicorn development server:
```bash
uvicorn app.main:app --reload
```

### Running Tests
Execute the pytest suite (covers health, validation, project modes, RAG retrieval, cache bypass, and global exception handling):
```bash
python -m pytest
```

---

## 3. Assumptions Made

- **In-Memory Storage**: Roadmaps are stored in a global Python dictionary `roadmaps_db` keyed by `roadmap_id`. For a 48-hour assignment, this is sufficient and removes unnecessary SQL database complexity, although ChromaDB persists the embedding vectors on disk.
- **FastAPI / Pydantic v2**: Assumed Pydantic v2 is the standard for FastAPI and leveraged its `@field_validator` hooks for validating skills lists and hours.
- **API Key**: Assumed Groq is the primary LLM SDK as requested.

---

## 4. AI Tools / Frameworks Used

This project was built pair-programming with **Antigravity (Google DeepMind)**:
- **Project Setup & Scaffolding**: Antigravity generated the skeleton directories and `requirements.txt`.
- **JSON mode retry logic**: Antigravity suggested the retry wrapper loop in `app/services/llm.py` that appends validation error tracebacks to the prompt if Groq outputs malformed JSON.
- **Semantic Caching Design**: Antigravity implemented the Cosine Distance mapping (`distance = 1 - similarity`) to match the 0.92 cosine similarity threshold perfectly in ChromaDB.
- **Pytest Suite**: Antigravity wrote unit tests mocking the LLM API layer so tests can run cleanly without consuming Groq token quotas or requiring API keys.

---

## 5. Prompt Design Decisions

- **Strict JSON Mode**: We leverage Groq's `response_format={"type": "json_object"}` parameter. This guarantees the LLM returns valid JSON.
- **Pydantic Validation Retries**: Even with JSON mode, the LLM may output JSON that does not match our exact Pydantic schema (e.g. missing fields, or incorrect types). We implement a **3-attempt retry loop** that feeds validation errors back to the LLM so it can correct its own mistakes.
- **Context-Limited Prompts**: On chat requests, we limit the prompt context strictly to the top 3-4 chunks retrieved from the vector database. This prevents prompt-stuffing, keeps token costs minimal, and stops the model from hallucinating details outside the roadmap scope.
