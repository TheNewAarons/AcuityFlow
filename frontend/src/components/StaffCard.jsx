import React, { useState, useEffect } from 'react';
import { Edit2, Trash2, ChevronDown, ChevronUp, Clock, MapPin, Phone } from 'lucide-react';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// Role → color palette
const ROLE_STYLES = {
  Doctor:    { bg: 'bg-indigo-100', text: 'text-indigo-700', avatar: 'bg-indigo-600' },
  RN:        { bg: 'bg-emerald-100', text: 'text-emerald-700', avatar: 'bg-emerald-600' },
  Técnico:   { bg: 'bg-amber-100', text: 'text-amber-700', avatar: 'bg-amber-500' },
  Paramédico:{ bg: 'bg-red-100', text: 'text-red-700', avatar: 'bg-red-500' },
};

const getRoleStyle = (role) => {
  for (const [key, style] of Object.entries(ROLE_STYLES)) {
    if (role?.toLowerCase().includes(key.toLowerCase())) return style;
  }
  return { bg: 'bg-slate-100', text: 'text-slate-700', avatar: 'bg-slate-500' };
};

const getInitials = (name = '') =>
  name.split(' ').map(n => n[0]).filter(Boolean).join('').toUpperCase().slice(0, 2);

const StaffCard = ({ member, canEdit, canToggle, onToggle, onEdit, onDelete }) => {
  const [expanded, setExpanded] = useState(false);
  const [shifts, setShifts]     = useState([]);
  const [loadingShifts, setLoadingShifts] = useState(false);
  const [toggling, setToggling] = useState(false);

  const roleStyle = getRoleStyle(member.role);
  const token = localStorage.getItem('token');

  useEffect(() => {
    if (!expanded) return;
    setLoadingShifts(true);
    fetch(`${API_URL}/api/staff/${member.id}/shifts`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then(r => r.json())
      .then(data => setShifts(Array.isArray(data) ? data : []))
      .catch(console.error)
      .finally(() => setLoadingShifts(false));
  }, [expanded, member.id, token]);

  const handleToggle = async () => {
    if (!canToggle || toggling) return;
    setToggling(true);
    await onToggle(member.id);
    setToggling(false);
  };

  const effBar =
    member.efficiency_multiplier >= 1.5 ? 'bg-emerald-500' :
    member.efficiency_multiplier >= 1.0 ? 'bg-indigo-500' :
    member.efficiency_multiplier >= 0.7 ? 'bg-amber-400' : 'bg-red-400';

  const effPct = Math.min(((member.efficiency_multiplier - 0.5) / 1.5) * 100, 100);

  return (
    <div className={`bg-white rounded-2xl border overflow-hidden shadow-sm transition-all duration-200 hover:shadow-md flex flex-col ${
      member.is_available ? 'border-slate-200' : 'border-slate-100 opacity-70'
    }`}>

      {/* ── Card Body ── */}
      <div className="p-5 flex-1">
        {/* Top row: avatar + info + toggle */}
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-center gap-3 min-w-0">
            <div className={`w-12 h-12 rounded-xl ${roleStyle.avatar} flex items-center justify-center text-white font-black text-sm shadow-sm flex-shrink-0`}>
              {getInitials(member.name)}
            </div>
            <div className="min-w-0">
              <p className="font-bold text-slate-900 text-sm leading-tight truncate">{member.name}</p>
              <span className={`inline-block text-[10px] font-bold px-2 py-0.5 rounded-full mt-1 ${roleStyle.bg} ${roleStyle.text}`}>
                {member.role}
              </span>
            </div>
          </div>

          {/* Availability toggle */}
          <button
            onClick={handleToggle}
            disabled={!canToggle || toggling}
            title={canToggle ? 'Cambiar disponibilidad' : 'Sin permisos para modificar'}
            className={`relative inline-flex h-6 w-11 flex-shrink-0 items-center rounded-full transition-colors duration-300 focus:outline-none ${
              member.is_available ? 'bg-emerald-500' : 'bg-slate-300'
            } ${!canToggle ? 'cursor-not-allowed opacity-60' : 'cursor-pointer'}`}
          >
            <span className={`inline-block h-4 w-4 transform rounded-full bg-white shadow transition-transform duration-300 ${
              member.is_available ? 'translate-x-6' : 'translate-x-1'
            }`} />
          </button>
        </div>

        {/* Efficiency bar */}
        <div className="mt-4">
          <div className="flex justify-between items-center mb-1">
            <p className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Eficiencia</p>
            <span className="text-xs font-black text-slate-700 tabular-nums">{member.efficiency_multiplier?.toFixed(1)}x</span>
          </div>
          <div className="h-1.5 bg-slate-100 rounded-full overflow-hidden">
            <div className={`h-full rounded-full transition-all ${effBar}`} style={{ width: `${effPct}%` }} />
          </div>
        </div>

        {/* Status + phone */}
        <div className="mt-3 flex items-center justify-between">
          <span className={`text-xs font-semibold ${member.is_available ? 'text-emerald-600' : 'text-slate-400'}`}>
            {member.is_available ? '● Disponible' : '○ No disponible'}
          </span>
          {member.phone_number && member.phone_number !== 'REDACTED' ? (
            <span className="flex items-center gap-1 text-[11px] text-slate-400 font-mono">
              <Phone className="w-3 h-3" /> {member.phone_number}
            </span>
          ) : member.phone_number === 'REDACTED' ? (
            <span className="flex items-center gap-1 text-[11px] text-slate-300 font-mono">
              <Phone className="w-3 h-3" /> ••••••••
            </span>
          ) : null}
        </div>
      </div>

      {/* ── Shift History Toggle ── */}
      <button
        onClick={() => setExpanded(v => !v)}
        className="w-full flex items-center justify-between px-5 py-3 bg-slate-50 border-t border-slate-100 text-xs font-bold text-slate-500 hover:bg-slate-100 transition-colors"
      >
        <span className="flex items-center gap-1.5">
          <Clock className="w-3.5 h-3.5" />
          Historial de Turnos
        </span>
        {expanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
      </button>

      {/* ── Shift History Content ── */}
      {expanded && (
        <div className="border-t border-slate-100 px-5 py-4 bg-white">
          {loadingShifts ? (
            <div className="space-y-2">
              {[1, 2, 3].map(i => (
                <div key={i} className="h-8 bg-slate-100 rounded-lg animate-pulse" />
              ))}
            </div>
          ) : shifts.length === 0 ? (
            <p className="text-xs text-slate-400 text-center py-2 italic">Sin turnos registrados aún</p>
          ) : (
            <div className="space-y-2">
              {shifts.map(shift => (
                <div key={shift.id} className="flex items-center justify-between bg-slate-50 rounded-lg px-3 py-2">
                  <span className="flex items-center gap-1.5 text-xs font-bold text-slate-700">
                    <MapPin className="w-3 h-3 text-indigo-400" />
                    {shift.zone}
                  </span>
                  <span className="text-[10px] text-slate-400 font-mono">
                    {shift.start_time
                      ? new Date(shift.start_time).toLocaleString('es-CL', {
                          day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit',
                        })
                      : 'Sin fecha'}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ── Admin Actions ── */}
      {canEdit && (
        <div className="flex border-t border-slate-100">
          <button
            onClick={() => onEdit(member)}
            className="flex-1 flex items-center justify-center gap-1.5 py-3 text-xs font-bold text-slate-500 hover:text-indigo-600 hover:bg-indigo-50 transition-colors"
          >
            <Edit2 className="w-3.5 h-3.5" /> Editar
          </button>
          <div className="w-px bg-slate-100" />
          <button
            onClick={() => onDelete(member.id)}
            className="flex-1 flex items-center justify-center gap-1.5 py-3 text-xs font-bold text-slate-500 hover:text-red-600 hover:bg-red-50 transition-colors"
          >
            <Trash2 className="w-3.5 h-3.5" /> Eliminar
          </button>
        </div>
      )}
    </div>
  );
};

export default StaffCard;
