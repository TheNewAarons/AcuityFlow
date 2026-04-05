import React, { useState, useEffect, useCallback } from 'react';
import { Plus, Search, Users, UserCheck, UserX, TrendingUp } from 'lucide-react';
import StaffCard  from './StaffCard';
import StaffModal from './StaffModal';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// ── Compact stat card ──────────────────────────────────────────
const StatCard = ({ icon, label, value, colorClass }) => (
  <div className={`${colorClass} rounded-2xl p-4 border border-white/60 flex items-center gap-4`}>
    <div className="flex-shrink-0">{icon}</div>
    <div>
      <p className="text-[10px] font-bold uppercase tracking-wider text-slate-500 leading-none mb-1">{label}</p>
      <p className="text-2xl font-black text-slate-900 leading-none tabular-nums">{value}</p>
    </div>
  </div>
);

// ── Main Panel ─────────────────────────────────────────────────
const StaffPanel = ({ user }) => {
  const [staff,        setStaff]        = useState([]);
  const [loading,      setLoading]      = useState(true);
  const [search,       setSearch]       = useState('');
  const [filter,       setFilter]       = useState('all'); // 'all' | 'available' | 'unavailable'
  const [showModal,    setShowModal]    = useState(false);
  const [editingStaff, setEditingStaff] = useState(null);

  const token      = localStorage.getItem('token');
  const authHdr    = { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' };
  const canEdit    = user.role === 'admin';
  const canToggle  = user.role === 'admin' || user.role === 'nurse';

  // ── Fetch ────────────────────────────────────────────────────
  const fetchStaff = useCallback(async () => {
    try {
      const res  = await fetch(`${API_URL}/api/staff`, { headers: { Authorization: `Bearer ${token}` } });
      const data = await res.json();
      if (Array.isArray(data)) setStaff(data);
    } catch (e) {
      console.error('Error al cargar el personal:', e);
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => { fetchStaff(); }, [fetchStaff]);

  // ── Handlers ─────────────────────────────────────────────────
  const handleToggle = async (staffId) => {
    const res = await fetch(`${API_URL}/api/staff/${staffId}/availability`, {
      method: 'PATCH', headers: authHdr,
    });
    if (res.ok) {
      const updated = await res.json();
      setStaff(prev => prev.map(s => s.id === staffId ? { ...s, is_available: updated.is_available } : s));
    }
  };

  const handleDelete = async (staffId) => {
    if (!window.confirm('¿Eliminar este miembro? El historial de turnos quedará intacto.')) return;
    const res = await fetch(`${API_URL}/api/staff/${staffId}`, { method: 'DELETE', headers: authHdr });
    if (res.ok) setStaff(prev => prev.filter(s => s.id !== staffId));
  };

  const handleSave = async (formData) => {
    if (editingStaff) {
      const res = await fetch(`${API_URL}/api/staff/${editingStaff.id}`, {
        method: 'PUT', headers: authHdr, body: JSON.stringify(formData),
      });
      if (res.ok) {
        const updated = await res.json();
        setStaff(prev => prev.map(s => s.id === editingStaff.id ? { ...s, ...updated } : s));
      }
    } else {
      const res = await fetch(`${API_URL}/api/staff`, {
        method: 'POST', headers: authHdr, body: JSON.stringify(formData),
      });
      if (res.ok) {
        const newMember = await res.json();
        setStaff(prev => [...prev, newMember]);
      }
    }
    setShowModal(false);
    setEditingStaff(null);
  };

  const openCreate = () => { setEditingStaff(null); setShowModal(true); };
  const openEdit   = (m) => { setEditingStaff(m);   setShowModal(true); };

  // ── Filtering ────────────────────────────────────────────────
  const filtered = staff.filter(s => {
    const q = search.toLowerCase();
    const matchSearch  = s.name?.toLowerCase().includes(q) || s.role?.toLowerCase().includes(q);
    const matchFilter  =
      filter === 'all'         ? true :
      filter === 'available'   ? s.is_available :
      /* unavailable */           !s.is_available;
    return matchSearch && matchFilter;
  });

  // ── Stats ────────────────────────────────────────────────────
  const available    = staff.filter(s => s.is_available).length;
  const unavailable  = staff.length - available;
  const avgEff       = staff.length
    ? (staff.reduce((a, s) => a + (s.efficiency_multiplier || 1), 0) / staff.length).toFixed(2)
    : '0.00';

  // ── Loading skeletons ────────────────────────────────────────
  if (loading) return (
    <div className="max-w-7xl mx-auto py-8 px-4 sm:px-6 lg:px-8">
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        {[...Array(4)].map((_, i) => (
          <div key={i} className="h-20 bg-slate-100 rounded-2xl animate-pulse" />
        ))}
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {[...Array(6)].map((_, i) => (
          <div key={i} className="bg-white rounded-2xl border border-slate-100 p-5 animate-pulse">
            <div className="flex gap-3">
              <div className="w-12 h-12 bg-slate-200 rounded-xl" />
              <div className="flex-1 space-y-2">
                <div className="h-4 bg-slate-200 rounded w-3/4" />
                <div className="h-3 bg-slate-100 rounded w-1/3" />
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );

  return (
    <div className="max-w-7xl mx-auto py-8 px-4 sm:px-6 lg:px-8">

      {/* ── Stats row ── */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <StatCard icon={<Users       className="w-6 h-6 text-indigo-500"  />} label="Total Personal"   value={staff.length} colorClass="bg-indigo-50"  />
        <StatCard icon={<UserCheck   className="w-6 h-6 text-emerald-500" />} label="Disponibles"      value={available}    colorClass="bg-emerald-50" />
        <StatCard icon={<UserX       className="w-6 h-6 text-slate-400"   />} label="No Disponibles"   value={unavailable}  colorClass="bg-slate-50"   />
        <StatCard icon={<TrendingUp  className="w-6 h-6 text-amber-500"   />} label="Eficiencia Prom." value={`${avgEff}x`} colorClass="bg-amber-50"   />
      </div>

      {/* ── Controls ── */}
      <div className="flex flex-col sm:flex-row gap-3 mb-6 items-start sm:items-center">

        {/* Search */}
        <div className="relative flex-1 w-full sm:w-auto">
          <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
          <input
            type="text"
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder="Buscar por nombre o especialidad…"
            className="w-full pl-10 pr-4 py-2.5 bg-white border border-slate-200 rounded-xl text-sm text-slate-700 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 transition"
          />
        </div>

        {/* Filter pills */}
        <div className="flex gap-1 bg-slate-100 p-1 rounded-xl flex-shrink-0">
          {[
            { key: 'all',         label: 'Todos'    },
            { key: 'available',   label: 'Disponibles'   },
            { key: 'unavailable', label: 'No disp.'      },
          ].map(f => (
            <button
              key={f.key}
              onClick={() => setFilter(f.key)}
              className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
                filter === f.key
                  ? 'bg-white text-slate-800 shadow-sm'
                  : 'text-slate-500 hover:text-slate-700'
              }`}
            >
              {f.label}
            </button>
          ))}
        </div>

        {/* Add — Admin only */}
        {canEdit && (
          <button
            onClick={openCreate}
            className="flex items-center gap-2 px-4 py-2.5 bg-indigo-600 text-white text-sm font-bold rounded-xl hover:bg-indigo-700 transition-colors shadow-sm hover:shadow-md flex-shrink-0 w-full sm:w-auto justify-center"
          >
            <Plus className="w-4 h-4" />
            Agregar Personal
          </button>
        )}
      </div>

      {/* ── Staff grid ── */}
      {filtered.length === 0 ? (
        <div className="flex flex-col items-center justify-center h-64 bg-white rounded-2xl border border-dashed border-slate-200">
          <Users className="w-12 h-12 text-slate-200 mb-3" />
          <p className="text-slate-400 font-medium text-sm">
            {search || filter !== 'all'
              ? 'No se encontró personal con esos filtros'
              : 'No hay personal registrado todavía'}
          </p>
          {canEdit && filter === 'all' && !search && (
            <button onClick={openCreate} className="mt-4 text-indigo-600 text-sm font-bold hover:underline">
              + Agregar el primero
            </button>
          )}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filtered.map(member => (
            <StaffCard
              key={member.id}
              member={member}
              canEdit={canEdit}
              canToggle={canToggle}
              onToggle={handleToggle}
              onEdit={openEdit}
              onDelete={handleDelete}
            />
          ))}
        </div>
      )}

      {/* ── Modal ── */}
      {showModal && (
        <StaffModal
          staff={editingStaff}
          onSave={handleSave}
          onClose={() => { setShowModal(false); setEditingStaff(null); }}
        />
      )}
    </div>
  );
};

export default StaffPanel;
