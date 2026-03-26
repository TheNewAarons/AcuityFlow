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
# Tool 2: Coordinate Shift with Staff via Direct Message (ASYNC)
# ------------------------------------------------------------------
@tool
async def coordinate_shift(candidate_name: str, zone: str, context: str, db: AsyncSession) -> str:
    """
    Sends a real direct message (WhatsApp/SMS via Twilio) to a specific staff member.
    'db' is automatically injected from the agent's state/context.
    'context' should summarize the urgency and any relevant details.
    Always use this tool to ask a human to take a shift.
    """
    from langchain_core.messages import HumanMessage, SystemMessage
    from .communications import send_message
    from . import models
    from sqlalchemy.future import select

    provider = os.getenv("LLM_PROVIDER", "openai").lower()

    # Get Candidate Phone Number from DB
    try:
        result = await db.execute(
            select(models.Staff).filter(models.Staff.name == candidate_name)
        )
        candidate = result.scalars().first()
        if not candidate:
            return json.dumps({"decision": "declined", "response": f"Error: No se encontró al candidato {candidate_name}."})
            
        test_phone = os.getenv("TEST_PHONE_NUMBER")
        phone = candidate.phone_number or test_phone
        
        if not phone:
             return json.dumps({"decision": "declined", "response": f"Error: {candidate_name} no tiene teléfono registrado."})

        # Generate the exact message to send using LLM
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

        system_prompt = f"""You are the automated AI Recruitment Agent for AcuityFlow Hospital Management.
    You need to compose a short, direct, and professional message (en español) to human staff member {candidate_name}.
    Context: {context}
    Zone: {zone}
    Ask them directly if they can take the shift and tell them to reply with "SI [Zona]" o "NO [Zona]".
    DO NOT use placeholders like [Nombre], use their actual name.
    Respond ONLY with the exact text message you want to send them, nothing else."""

        user_message = f"Escribe el mensaje de texto para alertar a {candidate_name} sobre la urgencia en {zone}."

        messages = [SystemMessage(content=system_prompt), HumanMessage(content=user_message)]
        result = await llm.ainvoke(messages)
        message_to_send = result.content.strip()

        # Send actual Twilio message
        success = send_message(phone, message_to_send)
        if success:
            # Note: A fully asynchronous human-in-the-loop would pause here and wait for a webhook.
            # For this MVP without a guaranteed fast human response, we will simulate a positive response
            # in order to not block the autonomous agent loop forever, BUT the message is actually sent.
            print(f"[AGENTE IA] Mensaje real enviado a {candidate_name} al tlf {phone}.")
            
            # TODO: For production, we should pause and wait for the Twilio Webhook.
            # For now, we simulate their acceptance to keep the demo flowing.
            return json.dumps({"decision": "accepted", "response": "Mensaje enviado via Twilio. (Simulando respuesta positiva para demo)"}, ensure_ascii=False)
        else:
            return json.dumps({"decision": "declined", "response": "Error: falló el envío de Twilio."})

    except Exception as e:
         return json.dumps({"decision": "declined", "response": f"Lo siento, hubo un error técnico al enviar el mensaje: {str(e)}"})


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
