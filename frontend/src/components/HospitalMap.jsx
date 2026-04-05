import React, { useState } from 'react';
import { AlertTriangle, MapPin, Zap } from 'lucide-react';

// Si el usuario aún no reemplaza el mapa por su imagen real, Vite cargará el dummy en assets.
// NOTA: Para que funcione, debes sobreescribir 'hospital-map.png' en la carpeta frontend/src/assets/
import mapImage from '../assets/hospital-map.png';

// Coordenadas estimadas según el plano. X, Y en porcentajes para que la UI sea responsiva al tamaño.
const MAP_CONFIG = {
  "Triage":     { top: '68%', left: '18%' },  // Zona Inferior Izquierda (Urgencias)
  "ER-Trauma":  { top: '22%', left: '17%' },  // Zona Superior Izquierda (Urgencias/Shock Room)
  "Pediatrics": { top: '26%', left: '41%' },  // Zona Verde Superior (Consultas de Pediatría)
  "ICU":        { top: '46%', left: '73%' }   // Bloque derecho medio (Plantas Superiores - UCI)
};

const HospitalMap = ({ zones, getStatusColor, agentStatus }) => {
  const [activePopover, setActivePopover] = useState(null);

  return (
    <div className="mt-8 relative w-full rounded-2xl overflow-hidden shadow-sm border border-slate-200 bg-white">
      {/* 
        La imagen define el tamaño y proporción del contenedor.
        Los % de las coordenadas (top, left) se calculan respecto a esta imagen. 
      */}
      <img 
        src={mapImage} 
        alt="Plano del Hospital" 
        className="w-full h-auto block object-cover" 
      />
      
      {/* Capa de Marcadores (Pines) */}
      {Object.values(zones).map(zoneData => {
         // Posición por defecto al centro si la zona no está mapeada
         const pos = MAP_CONFIG[zoneData.zone] || { top: '50%', left: '50%' };
         const isCritical = zoneData.status === 'critical';
         // Status del Agente respecto a esta zona
         const isCalling = agentStatus?.zone === zoneData.zone && agentStatus?.status === 'calling';
         const hasAutoTrigger = agentStatus?.zone === zoneData.zone && agentStatus?.status === 'done';

         // Selección dinámica de color en base al estado de AcuityFlow
         let bgColor = 'bg-slate-400';
         let ringColor = 'ring-slate-400/50';
         let textColor = 'text-slate-600';
         
         if (zoneData.status === 'stable') { bgColor = 'bg-emerald-500'; ringColor = 'ring-emerald-500/50'; textColor = 'text-emerald-600'; }
         if (zoneData.status === 'warning') { bgColor = 'bg-orange-500'; ringColor = 'ring-orange-500/50'; textColor = 'text-orange-600'; }
         if (isCritical) { bgColor = 'bg-red-500'; ringColor = 'ring-red-500/50'; textColor = 'text-red-600'; }

         return (
           <div 
             key={zoneData.zone}
             className="absolute transform -translate-x-1/2 -translate-y-1/2 flex flex-col items-center group cursor-pointer z-10"
             style={{ top: pos.top, left: pos.left }}
             onClick={() => setActivePopover(activePopover === zoneData.zone ? null : zoneData.zone)}
           >
              {/* Animación de latido crítico y urgente */}
              {isCritical && !isCalling && !hasAutoTrigger && (
                <span className="absolute flex h-10 w-10 -m-3">
                  <span className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${bgColor}`}></span>
                </span>
              )}
              {/* Animación de intervención de IA (Halo morado) */}
              {isCalling && (
                <span className="absolute flex h-16 w-16 -m-6">
                  <span className={`animate-pulse absolute inline-flex h-full w-full rounded-full opacity-60 bg-indigo-500`}></span>
                </span>
              )}

              {/* El Pin Central */}
              <div className={`relative flex items-center justify-center w-8 h-8 rounded-full shadow-xl text-white ${isCalling ? 'bg-indigo-600 ring-indigo-500/50' : bgColor} ring-4 ${isCalling ? 'ring-indigo-500/50' : ringColor} transition-transform hover:scale-110 z-20`}>
                {isCalling ? <Zap className="w-4 h-4 animate-bounce" /> : <MapPin className="w-4 h-4" />}
              </div>
              
              {/* Etiqueta flotante inferior, siempre visible */}
              <div className="absolute top-10 mt-1 bg-white/90 backdrop-blur-sm text-[11px] font-black px-2.5 py-1 rounded-lg border shadow-sm whitespace-nowrap text-slate-800 z-10 flex items-center gap-1.5 transition-all">
                 {zoneData.zone}
                 <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${bgColor.replace('bg-', 'bg-').replace('-500', '-100')} ${textColor}`}>
                   {zoneData.acuity_score}%
                 </span>
              </div>

              {/* Popover/Tooltip al hacer CLICK */}
              {activePopover === zoneData.zone && (
                 <div className="absolute bottom-12 left-1/2 transform -translate-x-1/2 bg-white rounded-2xl shadow-2xl border flex flex-col border-slate-200 p-4 w-56 z-50" onClick={e => e.stopPropagation()}>
                    <button 
                      className="absolute top-2 right-2 text-slate-400 hover:text-slate-700 p-1"
                      onClick={() => setActivePopover(null)}
                    ><XIcon className="w-4 h-4" /></button>
                    
                    <h3 className="font-black text-slate-800 mb-0.5 uppercase tracking-tight">{zoneData.zone}</h3>
                    <p className="text-xs text-slate-500 mb-3 font-medium">Capacidad actual: {zoneData.patient_count} pacientes</p>
                    
                    <div className="flex items-end gap-1 mb-3">
                      <span className={`text-4xl font-black leading-none tracking-tighter ${textColor}`}>
                        {zoneData.acuity_score}
                      </span>
                      <span className="text-sm font-bold text-slate-400 mb-0.5">%</span>
                    </div>

                    {isCritical && !isCalling && !hasAutoTrigger && (
                       <div className="bg-red-50 text-red-700 text-xs p-2.5 rounded-xl border border-red-100 font-bold flex flex-col gap-1 mb-1">
                         <div className="flex items-center gap-1.5">
                            <AlertTriangle className="w-3.5 h-3.5 animate-pulse" /> 
                            <span>Sobrecarga Crítica</span>
                         </div>
                         <span className="text-[10px] font-medium opacity-80 leading-tight">El Agente IA debería dispararse automáticamente.</span>
                       </div>
                    )}
                    
                    {agentStatus?.zone === zoneData.zone && (
                       <div className={`text-[10px] p-2.5 rounded-xl border font-bold flex flex-col gap-1 mb-1 ${
                         agentStatus.status === 'error' ? 'bg-red-50 text-red-700 border-red-200' :
                         agentStatus.status === 'calling' ? 'bg-indigo-50 text-indigo-700 border-indigo-200' : 'bg-emerald-50 text-emerald-700 border-emerald-200'
                       }`}>
                         <div className="flex items-center gap-1.5 uppercase tracking-wide">
                            <Zap className="w-3.5 h-3.5" /> IA Autónoma
                         </div>
                         <span className="opacity-90">{agentStatus.message}</span>
                       </div>
                    )}
                 </div>
              )}
           </div>
         );
      })}
    </div>
  );
};

const XIcon = ({ className }) => (
  <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
);

export default HospitalMap;
