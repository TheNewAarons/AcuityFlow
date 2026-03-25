import React from 'react';
import { Users } from 'lucide-react';
import { LineChart, Line, ResponsiveContainer } from 'recharts';

const ZoneCard = ({ zoneData, zoneHist, getStatusColor, getStatusIcon, triggerAgent, agentStatus }) => {
  return (
    <div key={zoneData.zone} className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden transition-all duration-300 focus-within:ring-2 ring-indigo-500">
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

      <div className={`px-6 pt-8 pb-4 flex flex-col items-center justify-center relative ${getStatusColor(zoneData.status).split(' ')[1]}`}>
         <div className="text-6xl font-black tracking-tighter" style={{ color: 'inherit' }}>
            {zoneData.acuity_score}<span className="text-3xl font-bold opacity-75">%</span>
         </div>
         <p className="font-bold mt-2 opacity-80 uppercase tracking-widest text-xs">Carga Ponderada Base</p>

         {/* Curva Histórica TSDB con Recharts */}
         {zoneHist.length > 0 && (
            <div className="w-full h-24 mt-4 opacity-50 mix-blend-multiply">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={zoneHist}>
                  <Line type="stepAfter" dataKey="acuity_score" stroke="currentColor" strokeWidth={3} dot={false} isAnimationActive={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>
         )}
      </div>

      <div className="px-6 py-4 bg-slate-50 border-t border-slate-100 flex justify-between items-center h-16">
        <span className="text-xs text-slate-400 font-medium tracking-wider">Última act. {new Date(zoneData.timestamp * 1000).toLocaleTimeString()}</span>
         {zoneData.status === 'critical' && (
           agentStatus?.zone === zoneData.zone ? (
             <span className={`text-xs font-bold px-3 py-1.5 rounded-full ${agentStatus.status === 'calling' ? 'bg-indigo-100 text-indigo-700 animate-pulse' : 'bg-emerald-100 text-emerald-700'}`}>
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
  );
};

export default ZoneCard;
