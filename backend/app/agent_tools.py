"""
LangChain custom tools (ASYNCHRONOUS) for the AcuityFlow recruitment agent.
Using async tools allows us to safely interact with the SQLAlchemy AsyncSession 
from within the LangGraph agent without thread/loop conflicts.
"""
import json
import os
from langchain_core.tools import tool
from sqlalchemy.future import select
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from . import models

# ------------------------------------------------------------------
# Tool 1: Query available staff from the database (ASYNC)
# ------------------------------------------------------------------
@tool
async def get_available_staff(zone: str, db: AsyncSession) -> str:
    """
    Returns a JSON-formatted list of staff members currently available for recruitment.
    'db' is automatically injected from the agent's state/context.
    """
    try:
        result = await db.execute(
            select(models.Staff).filter(models.Staff.is_available == True)
        )
        staff_list = result.scalars().all()

        # Get historical shift count per staff member
        shift_counts_result = await db.execute(
            select(models.Shift.staff_id, func.count(models.Shift.id).label("count"))
            .group_by(models.Shift.staff_id)
        )
        shift_counts = {row.staff_id: row.count for row in shift_counts_result}

        output = []
        for s in staff_list:
            output.append({
                "id": s.id,
                "name": s.name,
                "role": s.role,
                "efficiency": s.efficiency_multiplier,
                "past_shifts": shift_counts.get(s.id, 0),
            })
        
        if not output:
            return "No available staff found in the database."

        return json.dumps(output, ensure_ascii=False)
    except Exception as e:
        return f"Error querying staff: {str(e)}"


# ------------------------------------------------------------------
# Tool 2: Negotiate a shift with a candidate via LLM sub-call (ASYNC)
# ------------------------------------------------------------------
@tool
async def negotiate_shift(candidate_name: str, zone: str, context: str) -> str:
    """
    Initiates a natural-language negotiation with a specific staff member.
    'context' should summarize the urgency and any relevant details (e.g., other colleagues also attending).
    Returns a JSON object with 'decision' ('accepted' or 'declined') and 'response' (their words in Spanish).
    """
    from langchain_core.messages import HumanMessage, SystemMessage
    
    provider = os.getenv("LLM_PROVIDER", "openai").lower()
    
    # Check for API key
    if provider == "google" and not os.getenv("GOOGLE_API_KEY"):
        return json.dumps({"decision": "declined", "response": "ERROR: GOOGLE_API_KEY no está configurada."})
    if provider == "openai" and not os.getenv("OPENAI_API_KEY"):
        return json.dumps({"decision": "declined", "response": "ERROR: OPENAI_API_KEY no está configurada."})

    try:
        if provider == "google":
            from langchain_google_genai import ChatGoogleGenerativeAI
            llm = ChatGoogleGenerativeAI(
                model="gemini-2.0-flash",
                google_api_key=os.getenv("GOOGLE_API_KEY")
            )
        else:
            from langchain_openai import ChatOpenAI
            llm = ChatOpenAI(
                model="gpt-4o-mini",
                temperature=0.8,
                api_key=os.getenv("OPENAI_API_KEY")
            )

        system_prompt = f"""You are {candidate_name}, a healthcare professional in a hospital.
    You have your own personality, preferences, and professional ethics.
    You respond in first person, in a natural and human way (Spanish).
    You may accept or decline based on the context provided — be realistic and sometimes decline if overworked.
    Respond ONLY with a JSON object in this exact format:
    {{"decision": "accepted" or "declined", "response": "Su respuesta exacta en personaje"}}"""

        user_message = f"""El coordinador de RR.HH. te contacta para una guardia urgente en {zone}.
    Contexto: {context}
    ¿Aceptas el turno?"""

        messages = [SystemMessage(content=system_prompt), HumanMessage(content=user_message)]
        result = await llm.ainvoke(messages)

        raw = result.content.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"): raw = raw[4:]
            raw = raw.strip()

        # Final cleanup for potential stray text
        import re
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        if match:
            raw = match.group(0)

        parsed = json.loads(raw)
    except Exception as e:
        parsed = {"decision": "declined", "response": f"Lo siento, hubo un error técnico en mi terminal: {str(e)}"}

    return json.dumps(parsed, ensure_ascii=False)


# ------------------------------------------------------------------
# Tool 3: Persist the shift booking in the database (ASYNC)
# ------------------------------------------------------------------
@tool
async def book_shift(candidate_name: str, zone: str, db: AsyncSession) -> str:
    """
    Persists a confirmed shift booking in the database.
    'db' is automatically injected from the agent's state/context.
    """
    try:
        result = await db.execute(
            select(models.Staff).filter(models.Staff.name == candidate_name)
        )
        candidate = result.scalars().first()

        if candidate is None:
            return f"ERROR: No se encontró staff con nombre '{candidate_name}'."

        if not candidate.is_available:
            return f"ERROR: {candidate_name} ya está marcado como no disponible."

        candidate.is_available = False
        shift = models.Shift(staff_id=candidate.id, zone=zone)
        db.add(shift)
        await db.commit()
        return f"SUCCESS: Turno agendado para {candidate_name} en {zone}."
    except Exception as e:
        return f"Error booking shift: {str(e)}"
