# 🤖 Text-to-SQL AI Agent for Business Intelligence

Natural-language querying over the **Brazilian Olist E-Commerce** dataset, powered by **LangChain**, **PostgreSQL**, and **Google Gemini AI**.

Ask questions in plain Bahasa Indonesia or English and get instant SQL-backed answers.

---

## 🏗️ Architecture

```
User Question (NL)
       │
       ▼
  ┌─────────┐     ┌───────────────┐     ┌────────────┐
  │ FastAPI  │────▶│ LangChain SQL │────▶│ PostgreSQL │
  │  /query  │◀────│    Agent      │◀────│   (Olist)  │
  └─────────┘     └───────────────┘     └────────────┘
       │
       ▼
  JSON Response
```

## 📁 Project Structure

```
Text-To-SQL/
├── docker-compose.yml          # PostgreSQL + App containers
├── Dockerfile                  # Python app image
├── requirements.txt            # Python dependencies
├── .env.example                # Environment variable template
├── .gitignore
│
├── db/
│   └── init/
│       └── 01_create_tables.sql   # DDL – auto-runs on first DB start
│
├── datasets/                   # Place Olist CSVs here (from Kaggle)
│   └── README.md
│
└── src/
    ├── __init__.py
    ├── config.py               # Pydantic-settings configuration
    │
    ├── api/
    │   ├── __init__.py
    │   └── main.py             # FastAPI app (/health, /query)
    │
    ├── agent/
    │   ├── __init__.py
    │   ├── prompts.py          # System prompt + few-shot examples
    │   └── sql_agent.py        # LangChain SQL agent builder
    │
    └── db/
        ├── __init__.py
        ├── connection.py       # SQLAlchemy engine + session
        └── load_data.py        # CSV → PostgreSQL loader script
```

## 🚀 Quick Start

### 1. Clone & Configure

```bash
git clone <your-repo-url>
cd Text-To-SQL
cp .env.example .env
# Edit .env → set your GOOGLE_API_KEY (get free key at https://aistudio.google.com/apikey)
```

### 2. Download the Dataset

Download from [Kaggle – Brazilian E-Commerce (Olist)](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce) and place all CSV files in the `datasets/` folder.

### 3. Start Services

```bash
docker compose up -d --build
```

### 4. Load Data into PostgreSQL

```bash
docker compose exec app python -m src.db.load_data
```

### 5. Query the Agent

```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"question": "Top 5 kota dengan jumlah customer terbanyak?"}'
```

## 📡 API Endpoints

| Method | Path      | Description                        |
|--------|-----------|------------------------------------|
| GET    | `/health` | Database connectivity check        |
| POST   | `/query`  | Send NL question, get SQL answer   |
| GET    | `/docs`   | Swagger UI (auto-generated)        |

## 🛠️ Tech Stack

- **Python 3.11** – Runtime
- **LangChain** – LLM orchestration & SQL agent
- **Google Gemini 2.0 Flash** – Language model (free tier)
- **PostgreSQL 16** – Relational database
- **SQLAlchemy 2.0** – ORM & connection pooling
- **FastAPI** – REST API framework
- **Docker Compose** – Container orchestration

## 📄 License

MIT
