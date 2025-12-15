import json
import operator
import os
from typing import TypedDict, Annotated, Sequence

from dotenv import load_dotenv
from langchain_core.messages import BaseMessage
from langchain_gigachat.chat_models import GigaChat
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import StateGraph, END

from app.price_list import load_price_list, search_services

# -------------------------
# ENV + LLM
# -------------------------

load_dotenv(verbose=True)

llm = GigaChat(
    credentials=os.environ.get("OPENAI_API_KEY"),
    scope="GIGACHAT_API_PERS",
    verify_ssl_certs=False,
    temperature=0
)

# -------------------------
# PRICE LIST
# -------------------------

PRICE_LIST = load_price_list()
app = None


# -------------------------
# STATE
# -------------------------

class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]
    normalized_query: str | None
    last_found_services: list[dict]


# -------------------------
# NODES
# -------------------------

def analyze_question(state: AgentState) -> dict:
    """
    Извлекаем ключевые слова услуги.
    LLM НЕ знает прайс-лист.
    """
    print(state["messages"])
    user_history = " ".join(
        m["content"]
        for m in state["messages"]
        if (m.get("role") == "human") or (m.get("type") == "human")
    )

    system_prompt = """
Ты — аналитик пользовательских запросов.

Строгие правила:
1. НЕ придумывай услуги.
2. НЕ используй общие слова: "услуга", "работы", "сервис".
3. НЕ добавляй слов, которых нет в названии услуги.
4. НЕ используй слова: "цена", "стоимость", "сколько".
5. Если есть только одно слово из списка:
   «диагностика», «ремонт», «замена» — верни его.
6. normalized_query — только ключевые слова услуги,
   без союзов и предлогов.
7. Если не уверен — верни null.

Ответ строго в JSON:
{
  "normalized_query": "..." | null
}
"""

    response = llm.invoke([
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_history},
    ])

    data = json.loads(response.content)

    return {
        "normalized_query": data.get("normalized_query")
    }


def search_price_list_node(state: AgentState) -> dict:
    """
    Поиск ТОЛЬКО по прайс-листу.
    """

    query = state.get("normalized_query")

    results = search_services(
        PRICE_LIST,
        query
    ) if query else []

    return {
        "last_found_services": results
    }


def form_answer(state: AgentState) -> dict:
    """
    Формируем финальный ответ пользователю.
    """

    services = state.get("last_found_services", [])

    if not services:
        return {
            "messages": state["messages"] + [{
                "role": "assistant",
                "content": (
                    "В предоставленном прайс-листе нет информации "
                    "по данному запросу."
                )
            }]
        }

    lines = []
    for s in services:
        price = s["price"] if s["price"] else "Цена не указана"
        lines.append(f"• {s['service']} — {price}")

    answer = (
            "Доступные услуги:\n\n"
            + "\n".join(lines)
    )

    return {
        "messages": state["messages"] + [{
            "role": "assistant",
            "content": answer
        }]
    }



graph = StateGraph(AgentState)

graph.add_node("analyze", analyze_question)
graph.add_node("search", search_price_list_node)
graph.add_node("answer", form_answer)

graph.set_entry_point("analyze")
graph.add_edge("analyze", "search")
graph.add_edge("search", "answer")
graph.add_edge("answer", END)


_checkpointer_cm = SqliteSaver.from_conn_string(f"{os.environ['DB_PATH']}/db/db.sqlite3")
_checkpointer = _checkpointer_cm.__enter__()


def build_app():
    return graph.compile(checkpointer=_checkpointer)
