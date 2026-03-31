import React, { useState, useEffect, useRef } from 'react';
import { Activity, Users, AlertTriangle, CheckCircle, Zap, LogOut } from 'lucide-react';
import ZoneCard from './components/ZoneCard';
import AgentLogs from './components/AgentLogs';
import Login from './components/Login';

function App() {
  const [user, setUser] = useState(null);
  const [zones, setZones] = useState({});
  const [history, setHistory] = useState({});
  
  const zonesBuffer = useRef({}); // Buffer mudo para eventos actuales
  const historyBuffer = useRef({}); // Buffer mudo para la gráfica temporal
  
  const [simulations, setSimulations] = useState(null);
  const [isDigitalTwinActive, setIsDigitalTwinActive] = useState(false);
  const [agentStatus, setAgentStatus] = useState(null);

  useEffect(() => {
    const savedUser = localStorage.getItem('user');
    if (savedUser) {
      setUser(JSON.parse(savedUser));
    }
  }, []);

  useEffect(() => {
    if (!user) return;

    const token = localStorage.getItem('token');
    const headers = { 'Authorization': `Bearer ${token}` };

    // 1. Cargar historial desde la TSDB al arrancar la UI
    fetch('http://localhost:8000/api/history/all', { headers })
      .then(res => res.json())
      .then(data => { if (!data.error) setHistory(data); })
      .catch(console.error);

    // 2. Conectar a Time-Series viva (Redis)
    const ws = new WebSocket('ws://localhost:8000/ws/acuity');
    ws.onopen = () => console.log('✅ Conectado a AcuityFlow WebSocket');
    
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.error) {
        console.error("Backend reporta error:", data.error);
        return;
      }
      
      // Almacenamos el latido en el buffer C
      zonesBuffer.current[data.zone] = data;
      
      // Almacenar el historial
      const timeStr = new Date(data.timestamp * 1000).toLocaleTimeString();
      if(!historyBuffer.current[data.zone]) historyBuffer.current[data.zone] = [];
      historyBuffer.current[data.zone].push({ time: timeStr, acuity_score: data.acuity_score });
    };
    
    // Limitador de Frecuencia (Throttle): Transferencia limpia
    const renderIntervalProcess = setInterval(() => {
      let isZoneChanged = false;
      let isHistoryChanged = false;
      
      if (Object.keys(zonesBuffer.current).length > 0) isZoneChanged = true;
      if (Object.keys(historyBuffer.current).length > 0) isHistoryChanged = true;
      
      if (isZoneChanged) {
        setZones(prev => ({ ...prev, ...zonesBuffer.current }));
      }
      
      if (isHistoryChanged) {
        setHistory(prev => {
          const next = { ...prev };
          for (let z in historyBuffer.current) {
            next[z] = [...(next[z] || []), ...historyBuffer.current[z]].slice(-20); // Ventana deslizante de 20 puntos
          }
          return next;
        });
        // Limpiamos el buffer de historia
        historyBuffer.current = {};
      }
      
    }, 500);

    ws.onerror = (e) => console.error('❌ WebSocket Error - Asegúrate de que el backend (uvicorn) esté corriendo en el puerto 8000', e);
    ws.onclose = () => console.log('⚠️ WebSocket Desconectado');
    
    return () => {
      clearInterval(renderIntervalProcess);
      ws.close();
    };
  }, [user]);

  useEffect(() => {
    if (!isDigitalTwinActive) {
      setSimulations(null);
      return;
    }

    const baseState = Object.keys(zones).length > 0 
      ? Object.values(zones).map(z => ({ zone: z.zone, patients: z.patient_count }))
      : [{ zone: "ER-Trauma", patients: 12 }, { zone: "ICU", patients: 8 }];

    const events = [
      {
        zone: "ER-Trauma",
        add_patients: 15,
        severity_multiplier: 1.8
      }
    ];

    const abortController = new AbortController();
    const token = localStorage.getItem('token');
    
    fetch('http://localhost:8000/api/simulate', {
      method: 'POST',
      headers: { 
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify({ base_state: baseState, events }),
      signal: abortController.signal
    })
    .then(res => {
      if (res.status === 403) {
            alert("Acceso Denegado: Tu rol no tiene permisos para realizar simulaciones de incidentes.");
            setIsDigitalTwinActive(false);
        throw new Error("Forbidden");
      }
      return res.json();
    })
    .then(data => {
      if (data.projections) {
          const simMap = {};
          data.projections.forEach(p => simMap[p.zone] = p);
          setSimulations(simMap);
      }
    })
    .catch(e => {
        if (e.name !== 'AbortError') console.error(e);
    });

    return () => { abortController.abort(); };
  }, [zones, isDigitalTwinActive]);

  const triggerAgent = async (zone) => {
    setAgentStatus({ zone, status: 'calling', message: 'Orquestando contacto...' });
    try {
      const token = localStorage.getItem('token');
      const res = await fetch('http://localhost:8000/api/agent/trigger', {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ zone, required_staff: 2 })
      });

      if (res.status === 403) {
        setAgentStatus({ zone, status: 'error', message: 'ERROR RBAC: Permisos insuficientes' });
        setTimeout(() => setAgentStatus(null), 5000);
        return;
      }

      const data = await res.json();
      const recruited = data.recruited ?? [];
      const label = data.status === 'Success'
        ? `Reclutados: ${recruited.join(', ')}`
        : data.status === 'Partial'
        ? `Parcial: ${recruited.join(', ')}`
        : recruited.length === 0
        ? 'Sin personal disponible — reiniciando pool...'
        : 'Nadie aceptó el turno';
      setAgentStatus({ zone, status: data.status === 'Success' ? 'done' : 'error', message: label });
      // Auto-reset the staff pool when exhausted so next attempt works
      if (recruited.length === 0) {
        fetch('http://localhost:8000/api/staff/reset', { method: 'POST' }).catch(() => {});
      }
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
      case 'critical': return 'text-red-500 bg-red-50 border-red-500';
      case 'warning': return 'text-orange-500 bg-orange-50 border-orange-500';
      case 'stable': return 'text-emerald-500 bg-emerald-50 border-emerald-500';
      default: return 'text-gray-500 bg-gray-50 border-gray-500';
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

  const handleLogout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    setUser(null);
  };

  if (!user) {
    return <Login onLogin={(u) => setUser(u)} />;
  }

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
          <div className="flex gap-4 items-center">
            {/* User Profile */}
            <div className="flex flex-col text-right mr-2 border-r border-slate-200 pr-4">
              <span className="text-sm font-black text-slate-800 uppercase tracking-tight">{user.username}</span>
              <span className="text-[10px] font-bold text-indigo-500 uppercase tracking-widest">{user.role}</span>
            </div>

            {/* restricted action for admin/nurse only */}
            {(user.role === 'admin' || user.role === 'nurse') && (
              <button 
                onClick={() => setIsDigitalTwinActive(!isDigitalTwinActive)}
                className={`flex items-center space-x-2 px-4 py-2 rounded-full font-bold transition-all shadow-sm ${isDigitalTwinActive ? 'bg-slate-200 text-slate-700 hover:bg-slate-300' : 'bg-indigo-600 text-white hover:bg-indigo-700 hover:shadow-md'}`}
              >
                <Zap className="w-4 h-4" />
                <span>{isDigitalTwinActive ? 'Ocultar Gemelo Digital' : 'Activar Gemelo Digital: Incidente Masivo'}</span>
              </button>
            )}

            <button 
              onClick={handleLogout}
              className="p-2 text-slate-400 hover:text-red-500 transition-colors"
              title="Cerrar Sesión"
            >
              <LogOut className="w-5 h-5" />
            </button>
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
                <ZoneCard
                  key={zoneData.zone}
                  zoneData={zoneData}
                  zoneHist={history[zoneData.zone] || []}
                  getStatusColor={getStatusColor}
                  getStatusIcon={getStatusIcon}
                  triggerAgent={triggerAgent}
                  agentStatus={agentStatus}
                />
              ))
            )}
          </div>

          <AgentLogs />
        </div>
      </main>
    </div>
  );
}

export default App;
