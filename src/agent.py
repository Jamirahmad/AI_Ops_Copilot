import time
from langchain.chat_models import ChatOpenAI
from langchain.agents import initialize_agent
from langchain.agents.agent_types import AgentType

from src.config import MODEL_NAME, TEMPERATURE, MAX_ITERATIONS
from src.tools import tools
from src.memory import get_memory
from src.rag import retrieve_context, build_vectorstore
from src.logger import log_event
from src.feedback import adjust_prompt

vectorstore = build_vectorstore()

BASE_PROMPT = """
You are an AI Operations Copilot.

RULES:
- DO NOT perform actions or modify systems
- ONLY provide decision support
- If uncertain, say so clearly
- Recommend escalation when needed
- Do NOT expose sensitive data

Steps:
1. Analyze query
2. Use tools if needed
3. Provide hypothesis
4. Suggest next steps
5. Add confidence level
"""

def create_agent():
    llm = ChatOpenAI(
        model=MODEL_NAME,
        temperature=TEMPERATURE
    )

    memory = get_memory()

    agent = initialize_agent(
        tools=tools,
        llm=llm,
        agent=AgentType.CONVERSATIONAL_REACT_DESCRIPTION,
        memory=memory,
        max_iterations=MAX_ITERATIONS,
        verbose=True
    )

    return agent


def run_agent(query: str):
    start = time.time()

    agent = create_agent()

    context = retrieve_context(vectorstore, query)

    prompt = adjust_prompt(BASE_PROMPT)

    final_query = f"""
    Context:
    {context}

    User Query:
    {query}

    {prompt}
    """

    try:
        response = agent.run(final_query)
    except Exception:
        response = "System error. Please escalate to human analyst."

    latency = time.time() - start

    log_event(query, response, latency)

    return response
