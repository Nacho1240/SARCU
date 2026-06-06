import { useState } from 'react';
import { UserPlus, X, CheckCircle, AlertCircle, User, Mail, Lock, ShieldCheck } from 'lucide-react';

const GATEWAY_URL = import.meta.env.VITE_GATEWAY_URL || 'http://localhost:8000';

export default function CrearUsuario() {
    const [mostrarFormulario, setMostrarFormulario] = useState(false);
    const [nombre, setNombre] = useState('');
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [rol, setRol] = useState('operario');
    const [loading, setLoading] = useState(false);
    const [mensaje, setMensaje] = useState<{ tipo: 'exito' | 'error', texto: string } | null>(null);

    const handleCrearUsuario = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true);
        setMensaje(null);

        try {
            const token = localStorage.getItem('scg_token');
            
            // Enviamos los 5 campos que sauth_service exige: token, email, password, nombre y rol
            const response = await fetch(`${GATEWAY_URL}/auth/registro`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    token, 
                    email, 
                    password, 
                    nombre, 
                    rol 
                }),
            });

            const data = await response.json();

            if (data.status === 'ok') {
                setMensaje({ tipo: 'exito', texto: '✅ Usuario registrado y perfil creado correctamente.' });
                // Limpiamos campos
                setNombre('');
                setEmail('');
                setPassword('');
                
                setTimeout(() => {
                    setMostrarFormulario(false);
                    setMensaje(null);
                }, 3000);
            } else {
                setMensaje({ tipo: 'error', texto: data.mensaje || '❌ Error al procesar el registro.' });
            }
        } catch (error) {
            setMensaje({ tipo: 'error', texto: '❌ Error de conexión: El Gateway no responde.' });
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="w-full transition-all duration-300">
            {!mostrarFormulario ? (
                <button
                    onClick={() => setMostrarFormulario(true)}
                    className="w-full flex items-center justify-center gap-3 bg-cyan-600 hover:bg-cyan-700 text-white py-4 px-6 rounded-xl font-bold transition-all shadow-lg hover:shadow-cyan-200/50 group"
                >
                    <UserPlus className="h-6 w-6 group-hover:scale-110 transition-transform" />
                    Registrar Nuevo Personal CMVT
                </button>
            ) : (
                <div className="bg-slate-50 border border-slate-200 rounded-2xl p-6 shadow-inner animate-in fade-in slide-in-from-top-4 duration-300">
                    <div className="flex justify-between items-center mb-6">
                        <h3 className="text-lg font-bold text-slate-800 flex items-center gap-2">
                            <ShieldCheck className="h-5 w-5 text-cyan-600" />
                            Formulario de Registro
                        </h3>
                        <button 
                            onClick={() => setMostrarFormulario(false)}
                            className="text-slate-400 hover:text-slate-600 p-1"
                        >
                            <X className="h-5 w-5" />
                        </button>
                    </div>

                    <form onSubmit={handleCrearUsuario} className="space-y-5">
                        {/* Campo Nombre */}
                        <div>
                            <label className="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-1.5 ml-1">Nombre Completo</label>
                            <div className="relative">
                                <User className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
                                <input
                                    type="text"
                                    placeholder="Ej: Damian CMVT"
                                    value={nombre}
                                    onChange={(e) => setNombre(e.target.value)}
                                    required
                                    className="w-full pl-10 pr-4 py-2.5 bg-white border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:border-transparent transition-all"
                                />
                            </div>
                        </div>

                        {/* Campo Email */}
                        <div>
                            <label className="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-1.5 ml-1">Correo Electrónico</label>
                            <div className="relative">
                                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
                                <input
                                    type="email"
                                    placeholder="usuario@cmvt.cl"
                                    value={email}
                                    onChange={(e) => setEmail(e.target.value)}
                                    required
                                    className="w-full pl-10 pr-4 py-2.5 bg-white border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:border-transparent transition-all"
                                />
                            </div>
                        </div>

                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            {/* Campo Password */}
                            <div>
                                <label className="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-1.5 ml-1">Contraseña</label>
                                <div className="relative">
                                    <Lock className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
                                    <input
                                        type="password"
                                        placeholder="••••••••"
                                        value={password}
                                        onChange={(e) => setPassword(e.target.value)}
                                        required
                                        minLength={6}
                                        className="w-full pl-10 pr-4 py-2.5 bg-white border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:border-transparent transition-all"
                                    />
                                </div>
                            </div>

                            {/* Campo Rol */}
                            <div>
                                <label className="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-1.5 ml-1">Rol Asignado</label>
                                <select
                                    value={rol}
                                    onChange={(e) => setRol(e.target.value)}
                                    className="w-full px-4 py-2.5 bg-white border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:border-transparent appearance-none cursor-pointer font-medium text-slate-700 transition-all"
                                >
                                    <option value="operario">Operario (Terreno)</option>
                                    <option value="contador">Contador (Auditoría)</option>
                                    <option value="tecnico">Técnico (TI)</option>
                                </select>
                            </div>
                        </div>

                        {/* Mensajes de feedback */}
                        {mensaje && (
                            <div className={`p-4 rounded-xl flex items-center gap-3 text-sm font-semibold animate-bounce-short ${
                                mensaje.tipo === 'exito' ? 'bg-green-100 text-green-800 border border-green-200' : 'bg-red-100 text-red-800 border border-red-200'
                            }`}>
                                {mensaje.tipo === 'exito' ? <CheckCircle className="h-5 w-5 shrink-0" /> : <AlertCircle className="h-5 w-5 shrink-0" />}
                                <p>{mensaje.texto}</p>
                            </div>
                        )}

                        {/* Botones de acción */}
                        <div className="flex gap-3 pt-2">
                            <button
                                type="submit"
                                disabled={loading}
                                className="flex-1 bg-cyan-600 hover:bg-cyan-700 text-white py-3 px-6 rounded-xl font-bold transition-all shadow-md disabled:opacity-50 disabled:cursor-not-allowed flex justify-center items-center"
                            >
                                {loading ? (
                                    <span className="flex items-center gap-2">
                                        <svg className="animate-spin h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                                            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                                            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                                        </svg>
                                        Registrando...
                                    </span>
                                ) : 'Confirmar Alta de Usuario'}
                            </button>
                        </div>
                    </form>
                </div>
            )}
        </div>
    );
}