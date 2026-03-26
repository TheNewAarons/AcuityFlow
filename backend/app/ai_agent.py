"""
AcuityFlow - Autonomous Recruitment Agent (LangChain ReAct)
Refactored to be FULLY ASYNC to prevent event loop issues in FastAPI.
"""
import os
import asyncio
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import AsyncSession
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.prebuilt import create_react_agent

from .agent_tools import get_available_staff, coordinate_shift, book_shift

load_dotenv()

_agent_logs: list[dict] = []

SYSTEM_PROMPT = """You are AcuityFlow Orchestrator, an autonomous AI agent coordinating emergency medical staffing.
Your mission: recruit the required number of qualified healthcare professionals for a critical staffing deficit.

Protocol:
1. Search available candidates (Spanish: "buscar personal disponible").
2. Coordinate with each candidate via text message in Spanish using the coordinate_shift tool.
3. If they accept, book the shift immediately.
4. Stop when you meet the quota or exhaustion.

Respond in Spanish to the coordinator and candidates."""

def _check_api_keys():
    provider = os.getenv("LLM_PROVIDER", "openai").lower()
    if provider == "google":
        key = os.getenv("GOOGLE_API_KEY")
    else:
        key = os.getenv("OPENAI_API_KEY")
    return key and not key.startswith("sk-...your-key") and not key.startswith("AIza...your-key")

def _build_llm():
    provider = os.getenv("LLM_PROVIDER", "openai").lower()
    if provider == "google":
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(
            model="gemini-2.0-flash",
            google_api_key=os.getenv("GOOGLE_API_KEY"),
        )
    else:
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.5,
            api_key=os.getenv("OPENAI_API_KEY"),
        )

async def trigger_autonomous_recruitment(zone: str, required_staff: int, db: AsyncSession) -> dict:
    """
    Asynchronously triggers the LangChain agent.
    """
    print(f"\n[IA AGENT] ==== INICIANDO ORQUESTACION ASINCRONA ====")
    
    if not _check_api_keys():
        msg = "ERROR: No hay una API Key válida en el archivo .env. Por favor, configura tu OPENAI_API_KEY o GOOGLE_API_KEY."
        print(f"[IA AGENT] {msg}")
        return {"status": "Error", "message": msg, "recruited": [], "agent_log": msg}

    # Define tool wrappers that inject the 'db' session
    async def get_staff_bound(zone: str) -> str:
        return await get_available_staff.ainvoke({"zone": zone, "db": db})

    async def coordinate_shift_bound(candidate_name: str, zone: str, context: str) -> str:
        return await coordinate_shift.ainvoke({"candidate_name": candidate_name, "zone": zone, "context": context, "db": db})

    async def book_shift_bound(candidate_name: str, zone: str) -> str:
        return await book_shift.ainvoke({"candidate_name": candidate_name, "zone": zone, "db": db})

    # Tool list for the agent
    tools = [get_staff_bound, coordinate_shift_bound, book_shift_bound]
    
    # Give the bound tools better names/descriptions so the agent knows how to use them
    get_staff_bound.__name__ = "get_available_staff"
    get_staff_bound.__doc__ = get_available_staff.description
    book_shift_bound.__name__ = "book_shift"
    book_shift_bound.__doc__ = book_shift.description
    coordinate_shift_bound.__name__ = "coordinate_shift"
    coordinate_shift_bound.__doc__ = coordinate_shift.description

    llm = _build_llm()
    agent = create_react_agent(llm, tools)

    user_message = (
        f"CRISIS EN {zone.upper()}.\n"
        f"Necesitamos {required_staff} profesional(es). Zona: {zone}"
    )

    try:
        # Use ainvoke for true asynchronicity
        result = await agent.ainvoke({
            "messages": [
                SystemMessage(content=SYSTEM_PROMPT),
                HumanMessage(content=user_message),
            ]
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"status": "Error", "message": str(e), "recruited": [], "agent_log": f"Traceback: {str(e)}"}

    messages = result.get("messages", [])
    final_message = ""
    for msg in reversed(messages):
        if hasattr(msg, "content") and msg.content:
            final_message = msg.content
            break

    # Persist and log
    recruited = await _get_newly_booked_staff(db, zone)
    
    log_entry = {
        "zone": zone,
        "required": required_staff,
        "recruited": recruited,
        "agent_summary": final_message,
        "timestamp": os.getpid() # placeholder
    }
    _agent_logs.append(log_entry)

    print(f"[IA AGENT] Resumen: {len(recruited)} reclutados. Status: {'Success' if len(recruited) >= required_staff else 'Partial' if recruited else 'Failed'}")
    
    return {
        "status": "Success" if len(recruited) >= required_staff else "Partial" if recruited else "Failed",
        "message": f"Déficit {'resuelto' if len(recruited) >= required_staff else 'mitigado' if recruited else 'no resuelto'}.",
        "recruited": recruited,
        "agent_log": final_message,
    }

async def _get_newly_booked_staff(db: AsyncSession, zone: str) -> list[str]:
    from sqlalchemy.future import select
    from . import models
    try:
        # Just check staff marked unavailable in this session for this zone
        result = await db.execute(
            select(models.Staff).join(models.Shift, models.Staff.id == models.Shift.staff_id)
            .filter(models.Shift.zone == zone)
            .filter(models.Staff.is_available == False)
        )
        return list(set([s.name for s in result.scalars().all()]))
    except:
        return []

def get_agent_logs():
    return list(reversed(_agent_logs))
