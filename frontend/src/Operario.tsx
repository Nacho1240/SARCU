import { useState, useEffect } from 'react';
import { Plus, Wallet, TrendingDown, History, ArrowLeft } from 'lucide-react';
import { ExpenseHistory } from "./Expense_history";
import { ExpenseForm } from './expense-form';
import { ExpenseDetailModal } from './expense-detail-modal';
import { Button } from './button';

const GATEWAY_URL = import.meta.env.VITE_GATEWAY_URL || 'http://localhost:8000';

export interface Expense {
    id: string;
    concept: string;
    amount: number;
    photo: string;
    date: Date;
    estado: 'pendiente' | 'aprobado' | 'rechazado'; // <--- AGREGAR ESTO
}

interface OperarioProps {
    onReturnToAdmin?: () => void;
}

export default function Operario({ onReturnToAdmin }: OperarioProps) {
    const [usuario, setUsuario] = useState({
        id: "",
        nombre: "Trabajador", // Usamos un nombre genérico por ahora
        apellido: "",
        rol: "operario",
        saldo_disponible: 0
    });
    const [view, setView] = useState<'home' | 'form'>('home');
    const [cargando, setCargando] = useState(true);
    const [expenses, setExpenses] = useState<Expense[]>([]);
    const [selectedExpense, setSelectedExpense] = useState<Expense | null>(null);
    const [modalOpen, setModalOpen] = useState(false);

    // 1. Efecto que carga los datos desde el GATEWAY SOA
    useEffect(() => {
        obtenerDatosSOA();
    }, []);

    async function obtenerDatosSOA() {
        try {
            const token = localStorage.getItem('scg_token');
            const rol = localStorage.getItem('scg_rol') || 'operario';
            if (!token) return;

            // Consultamos al microservicio ssald
            const resSaldo = await fetch(`${GATEWAY_URL}/saldos/mio?token=${token}`);
            const dataSaldo = await resSaldo.json();

            if (dataSaldo.status === 'ok') {
                setUsuario(prev => ({
                    ...prev,
                    rol: rol,
                    saldo_disponible: dataSaldo.saldo_disponible || 0
                }));
            }

            // Consultamos al microservicio sgast
            const resGastos = await fetch(`${GATEWAY_URL}/gastos?token=${token}`);
            const dataGastos = await resGastos.json();

            if (dataGastos.status === 'ok' && dataGastos.gastos) {
                const historialFormateado = dataGastos.gastos.map((g: any) => ({
                    id: g.id,
                    concept: g.concepto || g.descripcion, 
                    amount: g.monto,
                    photo: g.comprobante_url || g.foto_url || "",
                    date: new Date(g.fecha || g.created_at),
                    estado: g.estado || 'pendiente' // Aseguramos que tenga un estado
                }));
                setExpenses(historialFormateado);
            }
        } catch (err) {
            console.error("Error al cargar los datos vía SOA:", err);
        } finally {
            setCargando(false);
        }
    }

    // 2. Función de subir gasto apuntando al GATEWAY SOA
    const handleAddExpense = async (nuevoGasto: { concept: string; amount: number; photo: string; date: Date }) => {
        try {
            const token = localStorage.getItem('scg_token');
            
            const res = await fetch(`${GATEWAY_URL}/gastos`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    token: token,
                    monto: nuevoGasto.amount,
                    concepto: nuevoGasto.concept,
                    fecha: nuevoGasto.date.toISOString().split('T')[0], // Enviar solo YYYY-MM-DD
                    comprobanteUrl: nuevoGasto.photo
                })
            });

            const data = await res.json();
            if (data.status !== 'ok') {
                throw new Error(data.mensaje);
            }

            // Si es exitoso, recargamos los datos para ver el nuevo saldo
            await obtenerDatosSOA();
            setView('home');

        } catch (error: any) {
            console.error("Error procesando la transacción:", error);
            alert("Hubo un error al registrar el gasto: " + error.message);
        }
    };

    const handleExpenseClick = (expense: Expense) => {
        setSelectedExpense(expense);
        setModalOpen(true);
    };

    if (cargando) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-gray-50">
                <p className="text-cyan-600 font-medium">Cargando tu información del servidor...</p>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-gray-50">
            {view === 'form' ? (
                <ExpenseForm
                    workerName={usuario.nombre}
                    availableBalance={usuario.saldo_disponible}
                    onSubmit={handleAddExpense}
                    onCancel={() => setView('home')}
                />
            ) : (
                <div className="min-h-screen bg-gradient-to-b from-cyan-50 to-white">
                    <div className="bg-gradient-to-r from-cyan-600 to-cyan-500 text-white p-6 pb-8 rounded-b-3xl shadow-lg">
                        {onReturnToAdmin && (
                            <div className="flex justify-start mb-4">
                                <Button
                                    variant="ghost"
                                    size="sm"
                                    onClick={onReturnToAdmin}
                                    className="text-cyan-50 hover:text-white hover:bg-cyan-700/50 bg-cyan-900/20 rounded-full px-4 transition-colors"
                                >
                                    <ArrowLeft className="h-4 w-4 mr-2" />
                                    Volver al Panel Admin
                                </Button>
                            </div>
                        )}
                        <div className="mb-6 flex items-center gap-4">
                            <img
                                src="/c-mvt_logo.png"
                                alt="Logo CMVT"
                                className="h-12 w-auto drop-shadow-md"
                            />
                            <div>
                                <p className="text-sm font-light tracking-wide text-cyan-100 text-left">Bienvenido</p>
                                <h1 className="text-2xl font-semibold mt-0.5 text-left leading-tight">
                                    {usuario.nombre}
                                </h1>
                            </div>
                        </div>
                        <div className="bg-white/10 backdrop-blur-sm rounded-2xl p-5 border border-white/20">
                            <div className="flex items-center gap-2 mb-3">
                                <Wallet className="h-5 w-5" />
                                <span className="text-sm text-cyan-100">Saldo Disponible</span>
                            </div>
                            <p className="text-4xl mb-4 text-left">${usuario.saldo_disponible.toLocaleString('es-CL')}</p>
                        </div>
                    </div>
                    <div className="p-4 pb-24">
                        {expenses.length > 0 && (
                            <div className="bg-gradient-to-r from-cyan-50 to-teal-50 rounded-xl p-4 mb-6 border border-cyan-200">
                                <div className="flex items-center gap-2 text-cyan-800">
                                    <TrendingDown className="h-5 w-5" />
                                    <div>
                                        <p className="text-sm">Gastos reportados</p>
                                        <p className="text-xl font-semibold">
                                            {expenses.length} {expenses.length === 1 ? 'boleta' : 'boletas'}
                                        </p>
                                    </div>
                                </div>
                            </div>
                        )}
                        <div className="flex items-center justify-between mb-4 mt-2">
                            <div className="flex items-center gap-2">
                                <History className="h-5 w-5 text-gray-600" />
                                <h2 className="text-lg text-gray-700 font-semibold">Historial de Gastos</h2>
                            </div>
                        </div>
                        <ExpenseHistory
                            expenses={expenses}
                            onExpenseClick={handleExpenseClick}
                        />
                    </div>
                    <div className="fixed bottom-6 right-6">
                        <Button
                            size="lg"
                            className="h-14 w-14 rounded-full shadow-lg bg-cyan-600 hover:bg-cyan-700"
                            onClick={() => setView('form')}
                        >
                            <Plus className="h-6 w-6 text-white" />
                        </Button>
                    </div>
                </div>
            )}
            <ExpenseDetailModal
                expense={selectedExpense}
                open={modalOpen}
                onClose={() => {
                    setModalOpen(false);
                    setSelectedExpense(null);
                }}
            />
        </div>
    );
}