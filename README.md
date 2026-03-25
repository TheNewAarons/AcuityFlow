# 🏥 AcuityFlow (Sistema de Orquestación de Personal Basado en Agudeza)

![AcuityFlow Banner](https://img.shields.io/badge/Status-Prototype-blue) ![Python](https://img.shields.io/badge/Backend-FastAPI-009688?logo=fastapi&logoColor=white) ![React](https://img.shields.io/badge/Frontend-React-61DAFB?logo=react&logoColor=black) ![Redis](https://img.shields.io/badge/Eventos-Redis-DC382D?logo=redis&logoColor=white)

**AcuityFlow** es una aplicación analítica integral diseñada para resolver la desalineación entre la capacidad del personal laboral y la demanda operativa real en entornos de alta presión (hospitales, centros de trauma, unidades de cuidados intensivos). 

En lugar de basarse en ratios fijos estáticos (ej. "1 enfermera por cada 4 pacientes"), AcuityFlow calcula la **"Carga de Trabajo Ponderada" (Acuity Score)** en tiempo real integrando señales de telemetría y dispositivos IoT de los pacientes.

---

## 🚀 Problema vs. Solución

### El Problema
Históricamente, los hospitales programan a su personal médico basándose en el conteo de pacientes (censo). Sin embargo, 10 pacientes estables no requieren la misma atención que 4 pacientes en estado crítico. Esta ceguera de datos provoca que las áreas de urgencias se saturen, llevando al personal al síndrome de agotamiento extremo (*Burnout*) y poniendo en riesgo la calidad de la atención al paciente.

### La Solución: AcuityFlow
AcuityFlow actúa como un "Sistema Nervioso Central" hospitalario. Lee datos de **monitores en tiempo real (IoT)** para entender la gravedad (SpO2, Pulso) de cada paciente y proyecta un porcentaje de carga de trabajo. Si esa carga excede las capacidades humanas del turno vigente, **un Agente de Inteligencia Artificial interviene de manera autónoma** para contactar a médicos de reserva, equilibrando el ecosistema hospitalario dinámicamente.

---

## 🌟 Funcionalidades Principales

1. **🩺 Motor de Agudeza (Acuity Engine):** Un complejo algoritmo matemático en el backend de Python que reemplaza el conteo básico de cuerpos. Evalúa la condición clínica simulada y emite un índice de 0 a 100% que refleja el nivel de estrés operativo del lugar.
2. **📡 Telemetría IoT en Tiempo Real:** Un simulador de inyección de ráfagas continuas de datos hacia Redis, procesado y enviado vía WebSockets a un panel de control inmediato.
3. **📊 Dashboard Reactivo:** Panel de control de operaciones para administradores del hospital, construido con React + Tailwind CSS. Muestra el estado de todas las "zonas" médicas a cada milisegundo.
4. **🔮 Gemelo Digital Predictivo (What-If):** Botón de simulación para proyectar crisis antes de que sucedan. Responde preguntas críticas como: *"¿Qué pasaría con la carga de nuestro personal si llegan 15 heridos graves en los próximos 10 minutos por un accidente de autobús?"*
5. **🤖 Agente Autónomo de IA (Smart Recruitment):** Cuando se alcanzan umbrales de saturación crítica (Score > 80%), puedes disparar un Agente LLM. Este agente rastrea internamente la base de datos de RRHH del hospital (PostgreSQL/SQLite), busca profesionales médicos cualificados que no estén de turno y simula el envío de invitaciones (SMS/WhatsApp) logrando escalar la capacidad del piso de 1 enfermera a 4 enfermeras instantáneamente, sin intervención humana administrativa.

---

## 💼 Casos de Uso Reales (Producción)

Si bien este proyecto es un prototipo, en un entorno de la vida real su aplicación beneficiaría enormemente a:
- **Centros de Trauma de Nivel 1:** Durante incidentes masivos (MCI), el sistema alerta automáticamente si la plantilla física no podrá soportar la demanda generada y orquesta movilizaciones desde otras alas del hospital.
- **Unidades de Cuidados Intensivos (UCI):** Ajusta los algoritmos de alarmas silenciosas. En lugar de que suenen pitidos de monitor sin cesar, AcuityFlow detecta una alza prolongada en la agudeza del pabellón y convoca apoyo.
- **Respuesta a Pandemias / Epidemias Estacionales:** Cuando los flujos de urgencias de pacientes se triplican impredeciblemente en invierno por virus respiratorios, AcuityFlow garantiza los llamamientos automatizados de personal eventual limitando la caída del sistema de salud.
- **Centros Logísticos o Cuarteles de Bomberos:** Los conceptos de **Acuity Engine** y **Digital Twin** no se limitan a hospitales; aplicar telemetría dinámica puede anticipar refuerzos en cualquier línea base asolada por ráfagas intensas de demanda (Servicio al Cliente, Despacho de Flotas, etc.).

---

## 🛠 Arquitectura Tecnológica

- **Backend:** `FastAPI` (Python) para control de endpoints de alta velocidad de respuesta y WebSockets asíncronos concurrentes.
- **Pub/Sub Bus:** `Redis` asíncrono. Utilizado como Message Broker ultrarrápido entre el hardware externo generador de datos y los clientes web suscritos.
- **Frontend:** `React.js` empaquetado mediante `Vite`, estilizado modernamente utilizando `TailwindCSS` con una interfaz modular basada en íconos SVG de `Lucide`.
- **Base de Datos:** Inicialmente configurado con `SQLite` para facilidad de demo de prototipo portátil (migrable a `PostgreSQL` cambiando una variable de entorno), utilizando `SQLAlchemy ORM` para gestionar los perfiles del personal médico.

---

## ⚙️ Instrucciones de Instalación Local

Para correr AcuityFlow en tu máquina y experimentar el gemelo digital y la IA por ti mismo, necesitas levantar los TRES motores que componen la arquitectura:

**Requisitos:** 
- `Python 3.10+`
- `Node.js 18+`
- `Redis` (Corriendo en el puerto 6379, puede ser nativo o por Docker: `docker run -d -p 6379:6379 redis`)

### 1. El Cerebro (Backend API)
Abre la primera terminal en la raíz del proyecto.
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```
*Esto iniciará la API en el puerto 8000 y creará la BD con médicos de prueba.*

### 2. El Corazón (Simulador de Telemetría IoT)
Abre una segunda terminal en la raíz del proyecto.
```bash
cd backend
source .venv/bin/activate
python scripts/iot_simulator.py
```
*Simulará el latido y presión de pacientes empujando datos a Redis cada 3 segundos.*

### 3. Los Ojos (Panel Dashboard Web)
Abre una tercera terminal en la raíz del proyecto.
```bash
cd frontend
npm install
npm run dev
```
*Ingresa a `http://localhost:5173` para visualizar las fluctuaciones predictivas y oprimir el botón de Inyectar IA de reclutamiento.*

---

## 🗺 Hoja de Ruta Futura (Roadmap)
- [ ] Módulo asíncrono para bases de datos transaccionales (`asyncpg`).
- [ ] Guardador de métricas en Bases de Datos de Series de Tiempo (TSDB) tipo TimescaleDB.
- [ ] Integración Real LLM: LangChain + SDK OpenAI/Gemini para que el agente converse de vuelta con médicos humanos para reclutar suplentes.
- [ ] Integración WhatsApp: Usar Meta Messaging API o Twilio para reemplazar logs de consola por verdaderas notificaciones de emergencia al móvil del personal.
- [ ] JWT Role-Base auth (Gestores vs Médicos).
