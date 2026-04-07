from fastapi import FastAPI
from pydantic import BaseModel
from app.tools.schema_tool import get_schema, get_schema_text
from app.tools.sql_tool import execute_sql
from app.agents.nl2sql_agent import run_nl2sql

app = FastAPI(title="ChatBI Agent MVP", version="0.2.0")


class SQLRequest(BaseModel):
    sql: str
    limit: int = 200


class QuestionRequest(BaseModel):
    question: str


@app.get("/")
def root():
    return {"message": "ChatBI Agent backend is running"}


@app.get("/schema")
def read_schema():
    return {
        "schema_text": get_schema_text(),
        "schema_json": get_schema()
    }


@app.post("/execute_sql")
def run_sql(req: SQLRequest):
    return execute_sql(req.sql, req.limit)


@app.post("/nl2sql")
def nl2sql(req: QuestionRequest):
    return run_nl2sql(req.question)
