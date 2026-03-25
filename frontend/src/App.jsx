import React, { useState, useEffect } from 'react';
import { Activity, Users, AlertTriangle, CheckCircle, Zap } from 'lucide-react';

function App() {
  const [zones, setZones] = useState({});
  const [simulations, setSimulations] = useState(null);
  const [isSimulating, setIsSimulating] = useState(false);
  const [agentStatus, setAgentStatus] = useState(null);

  useEffect(() => {
    const ws = new WebSocket('ws://localhost:8000/ws/acuity');
    ws.onopen = () => console.log('✅ Conectado a AcuityFlow WebSocket');
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.error) {
        console.error("Backend reporta error:", data.error);
        return;
      }
      setZones(prev => ({
        ...prev,
        [data.zone]: data
      }));
    };
    ws.onerror = (e) => console.error('❌ WebSocket Error - Asegúrate de que el backend (uvicorn) esté corriendo en el puerto 8000', e);
    ws.onclose = () => console.log('⚠️ WebSocket Desconectado');
    return () => ws.close();
  }, []);

  const runSimulation = async () => {
    setIsSimulating(true);
    // Extraer estado actual o un mock si está vacío
    const baseState = Object.keys(zones).length > 0 
      ? Object.values(zones).map(z => ({ zone: z.zone, patients: z.patient_count }))
      : [{ zone: "ER-Trauma", patients: 12 }, { zone: "ICU", patients: 8 }];

    // Simular un evento catástrofe: +15 pacientes en ER con alta severidad
    const events = [
      {
        zone: "ER-Trauma",
        add_patients: 15,
        severity_multiplier: 1.8
      }
    ];

    try {
      const res = await fetch('http://localhost:8000/api/simulate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ base_state: baseState, events })
      });
      const data = await res.json();
      
      // Convert Array to object map for easy rendering
      const simMap = {};
      data.projections.forEach(p => simMap[p.zone] = p);
      setSimulations(simMap);
    } catch (e) {
      console.error(e);
    } finally {
      setIsSimulating(false);
    }
  };

  const clearSimulation = () => setSimulations(null);

  const triggerAgent = async (zone) => {
    setAgentStatus({ zone, status: 'calling', message: 'Orquestando contacto...' });
    try {
      const res = await fetch('http://localhost:8000/api/agent/trigger', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ zone, required_staff: 2 })
      });
      const data = await res.json();
      setAgentStatus({ 
        zone, 
        status: 'done', 
        message: `${data.status}! Reclutados: ${data.recruited?.join(', ') || 'Ninguno'}` 
      });
      setTimeout(() => setAgentStatus(null), 8000);
    } catch(e) {
      setAgentStatus({ zone, status: 'error', message: 'Fallo de conexión' });
    }
  };

  const getStatusColor = (status, isSim = false) => {
    if (isSim) {
      switch (status) {
        case 'critical': return 'text-fuchsia-600 bg-fuchsia-100 border-fuchsia-500';
        case 'warning': return 'text-amber-600 bg-amber-100 border-amber-500';
        case 'stable': return 'text-teal-600 bg-teal-100 border-teal-500';
        default: return 'text-gray-600 bg-gray-100 border-gray-500';
      }
    }
    switch (status) {
      case 'critical': return 'text-red-600 bg-red-100 border-red-500';
      case 'warning': return 'text-orange-600 bg-orange-100 border-orange-500';
      case 'stable': return 'text-emerald-600 bg-emerald-100 border-emerald-500';
      default: return 'text-gray-600 bg-gray-100 border-gray-500';
    }
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'critical': return <AlertTriangle className="w-8 h-8 text-red-500" />;
      case 'warning': return <Activity className="w-8 h-8 text-orange-500" />;
      case 'stable': return <CheckCircle className="w-8 h-8 text-emerald-500" />;
      default: return null;
    }
  };

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="bg-white border-b border-slate-200 sticky top-0 z-10">
        <div className="max-w-7xl mx-auto py-4 px-4 sm:px-6 lg:px-8 flex justify-between items-center">
          <div>
            <h1 className="text-3xl font-bold leading-tight text-slate-900 tracking-tight">
              AcuityFlow Dashboard
            </h1>
            <p className="text-sm text-slate-500 mt-1">Orquestación de Personal Basada en Agudeza</p>
          </div>
          <div className="flex gap-4">
            <button 
              onClick={simulations ? clearSimulation : runSimulation}
              disabled={isSimulating}
              className={`flex items-center space-x-2 px-4 py-2 rounded-full font-bold transition-all shadow-sm ${simulations ? 'bg-slate-200 text-slate-700 hover:bg-slate-300' : 'bg-indigo-600 text-white hover:bg-indigo-700 hover:shadow-md'}`}
            >
              <Zap className="w-4 h-4" />
              <span>{isSimulating ? 'Calculando...' : simulations ? 'Ocultar Gemelo Digital' : 'Activar Gemelo Digital: Incidente Masivo'}</span>
            </button>

            <div className="flex items-center space-x-2 text-sm text-emerald-600 bg-emerald-50 px-3 py-1 rounded-full ring-1 ring-emerald-200">
               <span className="relative flex h-3 w-3">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-3 w-3 bg-emerald-500"></span>
              </span>
              <span className="font-semibold">Live Telemetry</span>
            </div>
          </div>
        </div>
      </header>

      <main>
        <div className="max-w-7xl mx-auto py-8 sm:px-6 lg:px-8">
          {simulations && (
            <div className="mb-10 bg-indigo-50 border border-indigo-100 rounded-2xl p-6 shadow-sm">
               <h3 className="text-lg font-bold text-indigo-900 mb-4 flex items-center"><Zap className="w-5 h-5 text-indigo-500 mr-2" /> Proyecciones de Gemelo Digital (Escenario: +15 Trauma Severo)</h3>
               <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {Object.values(simulations).map(sim => (
                  <div key={`sim-${sim.zone}`} className={`bg-white rounded-xl border-l-4 shadow-sm p-4 ${getStatusColor(sim.status, true).split(' ')[2]}`}>
                     <div className="flex justify-between">
                       <h4 className="font-bold text-slate-800">{sim.zone}</h4>
                       <span className={`text-xs font-bold px-2 py-1 rounded capitalize ${getStatusColor(sim.status, true).split(' ').slice(0,2).join(' ')}`}>{sim.status}</span>
                     </div>
                     <div className="mt-4 flex items-end justify-between">
                        <div>
                           <p className="text-3xl font-black text-slate-900">{sim.projected_score}%</p>
                           <p className="text-xs text-slate-500 uppercase font-semibold tracking-wider">Acuity Proyectado</p>
                        </div>
                        <div className="text-right">
                           <p className="text-lg font-bold text-slate-700">{sim.projected_patients}</p>
                           <p className="text-xs text-slate-500">Pacientes</p>
                        </div>
                     </div>
                  </div>
                ))}
               </div>
            </div>
          )}

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {Object.keys(zones).length === 0 ? (
              <div className="col-span-full border-4 border-dashed border-slate-200 rounded-xl h-64 flex flex-col items-center justify-center">
                <Activity className="w-12 h-12 text-slate-300 animate-pulse mb-3" />
                <h2 className="text-xl text-slate-400 font-medium">Esperando conexión de monitores IoT...</h2>
                <p className="text-sm text-slate-400 mt-2">Puedes correr el Gemelo Digital para ver proyecciones teóricas.</p>
              </div>
            ) : (
              Object.values(zones).map(zoneData => (
                <div key={zoneData.zone} className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden transition-all duration-300 hover:shadow-lg focus-within:ring-2 ring-indigo-500">
                  <div className={`px-6 py-4 border-b-4 ${getStatusColor(zoneData.status).split(' ')[2]} flex justify-between items-center`}>
                     <div>
                        <h2 className="text-2xl font-bold text-slate-800">{zoneData.zone}</h2>
                        <div className="flex items-center text-slate-500 mt-1">
                          <Users className="w-4 h-4 mr-1" />
                          <span className="text-sm font-medium">{zoneData.patient_count} pacientes</span>
                        </div>
                     </div>
                     {getStatusIcon(zoneData.status)}
                  </div>
                  <div className={`px-6 py-8 flex flex-col items-center justify-center ${getStatusColor(zoneData.status).split(' ')[1]}`}>
                     <div className="text-6xl font-black tracking-tighter" style={{ color: 'inherit' }}>
                        {zoneData.acuity_score}<span className="text-3xl font-bold opacity-75">%</span>
                     </div>
                     <p className="font-bold mt-2 opacity-80 uppercase tracking-widest text-xs">Carga Ponderada Base</p>
                  </div>
                  <div className="px-6 py-4 bg-slate-50 border-t border-slate-100 flex justify-between items-center h-16">
                    <span className="text-xs text-slate-400 font-medium tracking-wider">Última act. {new Date(zoneData.timestamp * 1000).toLocaleTimeString()}</span>
                     {zoneData.status === 'critical' && (
                       agentStatus?.zone === zoneData.zone ? (
                         <span className={`text-xs font-bold px-3 py-1.5 rounded-full ${agentStatus.status === 'calling' ? 'bg-indigo-100 text-indigo-700 animate-pulse' : 'bg-green-100 text-green-700'}`}>
                           {agentStatus.message}
                         </span>
                       ) : (
                         <button onClick={() => triggerAgent(zoneData.zone)} className="text-xs font-bold text-white bg-red-600 px-4 py-2 rounded-full hover:bg-red-700 transition shadow-sm hover:shadow">
                           Intervención IA
                         </button>
                       )
                     )}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </main>
    </div>
  );
}

export default App;
