import React, { useEffect, useState } from 'react';
import { Terminal, Clock } from 'lucide-react';

const AgentLogs = () => {
  const [logs, setLogs] = useState([]);

  const fetchLogs = () => {
    fetch('http://localhost:8000/api/agent/logs')
      .then(res => res.json())
      .then(data => setLogs(data))
      .catch(console.error);
  };

  useEffect(() => {
    fetchLogs();
    const interval = setInterval(fetchLogs, 5000);
    return () => clearInterval(interval);
  }, []);

  if (logs.length === 0) return null;

  return (
    <div className="mt-10 bg-slate-900 rounded-2xl p-6 shadow-xl border border-slate-800">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-bold text-slate-100 flex items-center">
          <Terminal className="w-5 h-5 text-emerald-400 mr-2" />
          Consola del Agente de Orquestación
        </h3>
        <span className="text-xs text-slate-500 font-mono animate-pulse">Monitorizando eventos...</span>
      </div>

      <div className="space-y-4 max-h-96 overflow-y-auto pr-2 custom-scrollbar">
        {logs.map((log, idx) => (
          <div key={idx} className="border-l-2 border-emerald-500/30 pl-4 py-1">
            <div className="flex items-center gap-2 mb-1">
              <span className="text-xs font-bold text-emerald-400 uppercase tracking-wider">{log.zone}</span>
              <span className="text-[10px] text-slate-500 flex items-center">
                <Clock className="w-3 h-3 mr-1" /> Requeridos: {log.required}
              </span>
            </div>
            <p className="text-sm text-slate-300 italic mb-2 leading-relaxed">
              "{log.agent_summary}"
            </p>
            <div className="flex flex-wrap gap-2">
              {log.recruited.map(name => (
                <span key={name} className="text-[10px] bg-emerald-500/10 text-emerald-400 px-2 py-0.5 rounded border border-emerald-500/20">
                  ✅ {name}
                </span>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default AgentLogs;
