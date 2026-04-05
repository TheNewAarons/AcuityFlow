import React, { useState } from 'react';
import { X, User, Phone, Briefcase, Zap } from 'lucide-react';

const ROLES = ['Doctor', 'RN', 'Técnico', 'Paramédico'];

const StaffModal = ({ staff, onSave, onClose }) => {
  const [form, setForm] = useState({
    name:                  staff?.name               ?? '',
    role:                  staff?.role               ?? 'RN',
    phone_number:          staff?.phone_number        ?? '',
    efficiency_multiplier: staff?.efficiency_multiplier ?? 1.0,
  });
  const [errors, setSaveErrors] = useState({});
  const [saving, setSaving]     = useState(false);

  const set = (key, val) => setForm(p => ({ ...p, [key]: val }));

  const validate = () => {
    const e = {};
    if (!form.name.trim())
      e.name = 'El nombre es obligatorio';
    if (!form.phone_number.trim())
      e.phone_number = 'El teléfono es obligatorio (el agente de IA lo necesita)';
    else if (!/^\+\d{7,15}$/.test(form.phone_number.trim()))
      e.phone_number = 'Formato inválido — ej: +56912345678';
    setSaveErrors(e);
    return Object.keys(e).length === 0;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!validate()) return;
    setSaving(true);
    await onSave({ ...form, phone_number: form.phone_number.trim() });
    setSaving(false);
  };

  const effLabel =
    form.efficiency_multiplier >= 1.8 ? '🏆 Elite'  :
    form.efficiency_multiplier >= 1.2 ? '⬆ Alto'    :
    form.efficiency_multiplier >= 0.9 ? '✓ Normal'  :
    form.efficiency_multiplier >= 0.7 ? '⬇ Bajo'    : '⚠ Mínimo';

  return (
    <div className="fixed inset-0 z-50 flex">
      {/* Backdrop */}
      <div
        className="flex-1 bg-slate-900/50 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Drawer */}
      <div className="w-full max-w-md bg-white flex flex-col shadow-2xl animate-slide-in-right">

        {/* ── Header ── */}
        <div className="flex items-start justify-between p-6 border-b border-slate-100">
          <div>
            <h2 className="text-xl font-black text-slate-900 leading-tight">
              {staff ? 'Editar miembro' : 'Agregar personal'}
            </h2>
            <p className="text-sm text-slate-400 mt-0.5">
              {staff ? `Modificando datos de ${staff.name}` : 'Nuevo integrante del equipo médico'}
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-xl text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* ── Form ── */}
        <form onSubmit={handleSubmit} className="flex-1 overflow-y-auto p-6 space-y-6">

          {/* Name */}
          <div>
            <label className="block text-[11px] font-bold uppercase tracking-wider text-slate-500 mb-2">
              Nombre Completo
            </label>
            <div className="relative">
              <User className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
              <input
                type="text"
                value={form.name}
                onChange={e => set('name', e.target.value)}
                placeholder="Dr. House, Nurse Jackie…"
                className={`w-full pl-10 pr-4 py-3 rounded-xl border text-sm text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 transition ${
                  errors.name ? 'border-red-300 bg-red-50' : 'border-slate-200 bg-white'
                }`}
              />
            </div>
            {errors.name && <p className="text-xs text-red-500 mt-1">{errors.name}</p>}
          </div>

          {/* Role */}
          <div>
            <label className="block text-[11px] font-bold uppercase tracking-wider text-slate-500 mb-2">
              Rol / Especialidad
            </label>
            <div className="grid grid-cols-2 gap-2">
              {ROLES.map(r => (
                <button
                  key={r}
                  type="button"
                  onClick={() => set('role', r)}
                  className={`py-2.5 rounded-xl text-sm font-bold transition-all ${
                    form.role === r
                      ? 'bg-indigo-600 text-white shadow-sm shadow-indigo-200'
                      : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                  }`}
                >
                  {r}
                </button>
              ))}
            </div>
          </div>

          {/* Phone */}
          <div>
            <label className="block text-[11px] font-bold uppercase tracking-wider text-slate-500 mb-2">
              Teléfono{' '}
              <span className="normal-case text-red-400 ml-1">(requerido para el agente IA)</span>
            </label>
            <div className="relative">
              <Phone className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
              <input
                type="tel"
                value={form.phone_number}
                onChange={e => set('phone_number', e.target.value)}
                placeholder="+56912345678"
                className={`w-full pl-10 pr-4 py-3 rounded-xl border text-sm font-mono text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 transition ${
                  errors.phone_number ? 'border-red-300 bg-red-50' : 'border-slate-200 bg-white'
                }`}
              />
            </div>
            {errors.phone_number && (
              <p className="text-xs text-red-500 mt-1">{errors.phone_number}</p>
            )}
          </div>

          {/* Efficiency */}
          <div>
            <div className="flex justify-between items-center mb-2">
              <label className="block text-[11px] font-bold uppercase tracking-wider text-slate-500">
                Multiplicador de Eficiencia
              </label>
              <div className="flex items-center gap-1.5">
                <span className="text-sm font-black text-slate-800 tabular-nums">
                  {form.efficiency_multiplier.toFixed(1)}x
                </span>
                <span className="text-[10px] text-slate-400 font-semibold">{effLabel}</span>
              </div>
            </div>
            <input
              type="range"
              min="0.5" max="2.0" step="0.1"
              value={form.efficiency_multiplier}
              onChange={e => set('efficiency_multiplier', parseFloat(e.target.value))}
              className="w-full h-2 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-indigo-600"
            />
            <div className="flex justify-between text-[10px] text-slate-400 mt-1 font-mono">
              <span>0.5x</span>
              <span>1.0x Normal</span>
              <span>2.0x Elite</span>
            </div>
          </div>
        </form>

        {/* ── Footer ── */}
        <div className="p-6 border-t border-slate-100 flex gap-3">
          <button
            type="button"
            onClick={onClose}
            className="flex-1 py-3 rounded-xl border border-slate-200 text-slate-600 text-sm font-bold hover:bg-slate-50 transition-colors"
          >
            Cancelar
          </button>
          <button
            type="submit"
            onClick={handleSubmit}
            disabled={saving}
            className="flex-1 py-3 rounded-xl bg-indigo-600 text-white text-sm font-bold hover:bg-indigo-700 transition-colors shadow-sm disabled:opacity-50 flex items-center justify-center gap-2"
          >
            <Zap className="w-4 h-4" />
            {saving ? 'Guardando…' : staff ? 'Guardar Cambios' : 'Agregar al Equipo'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default StaffModal;
