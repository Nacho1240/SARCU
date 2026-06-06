import { useState, useEffect, useMemo } from 'react';
import { LayoutDashboard, Receipt, TrendingDown, Calendar as CalendarIcon, Search, X, Filter, Download, FileDown, ArrowLeftRight, Clock } from 'lucide-react';
import { Button } from './button';
import { AdminCalendar } from './admin-calendar';
import { ExpenseDetailModal } from './expense-detail-modal';
import { Input } from './input';
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from './select';
import { Badge } from './badge';
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from './table';
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuTrigger,
    DropdownMenuSeparator,
} from './dropdown-menu';
import { downloadMultipleExpensesPDF } from './pdf-generator';





const GATEWAY_URL = import.meta.env.VITE_GATEWAY_URL || 'http://localhost:8000';

interface Expense {
    id: string;
    workerId?: string;
    workerName?: string;
    concept: string;
    amount: number;
    photo: string;
    date: Date;
    estado: 'pendiente' | 'aprobado' | 'rechazado';
}

interface AdminViewProps {
    onSwitchView?: () => void;
}

export default function AdminView({ onSwitchView }: AdminViewProps) {
    const [expenses, setExpenses] = useState<Expense[]>([]);
    const [selectedExpense, setSelectedExpense] = useState<Expense | null>(null);
    const [modalOpen, setModalOpen] = useState(false);
    const [activeView, setActiveView] = useState<'dashboard' | 'calendar'>('dashboard');
    const [cargando, setCargando] = useState(true);

    const [searchTerm, setSearchTerm] = useState('');
    const [dateFilter, setDateFilter] = useState('all');
    const [amountFilter, setAmountFilter] = useState('all');
    const [workerFilter, setWorkerFilter] = useState('all');

    // 1. Cargar el historial completo de egresos a través de la API Gateway (SOA)
    useEffect(() => {
        async function fetchGastosSOA() {
            try {
                const token = localStorage.getItem('scg_token');
                if (!token) return;

                const response = await fetch(`${GATEWAY_URL}/gastos?token=${token}`);
                const data = await response.json();

                if (data.status === 'ok' && data.gastos) {
                    const formatExpenses = data.gastos.map((g: any) => ({
                        id: g.id,
                        workerId: g.operario_id,
                        // Si el backend aún no hace el JOIN del nombre, mostramos los primeros caracteres del ID como respaldo
                        workerName: g.worker_name || `Operario (${g.operario_id?.slice(0, 6)})`,
                        concept: g.concepto || g.descripcion || 'Sin concepto',
                        amount: g.monto,
                        photo: g.foto_url || g.comprobante_url || '',
                        date: new Date(g.fecha_creacion || g.created_at || g.fecha),
                        estado: g.estado || 'pendiente'
                    }));
                    setExpenses(formatExpenses);
                }
            } catch (error) {
                console.error("Error cargando datos de gastos vía SOA:", error);
            } finally {
                setCargando(false);
            }
        }

        fetchGastosSOA();
    }, []);

    // 2. Extraer la lista de trabajadores de forma dinámica basado en las boletas existentes
    const workersList = useMemo(() => {
        const uniqueWorkers = new Map<string, string>();
        expenses.forEach((exp) => {
            if (exp.workerId) {
                uniqueWorkers.set(exp.workerId, exp.workerName || exp.workerId);
            }
        });
        return Array.from(uniqueWorkers.entries()).map(([id, name]) => ({ id, name }));
    }, [expenses]);

    // 3. Filtros aplicados en memoria en el cliente
    const filteredExpenses = useMemo(() => {
        let filtered = [...expenses];

        if (searchTerm) {
            filtered = filtered.filter((exp) =>
                exp.concept.toLowerCase().includes(searchTerm.toLowerCase())
            );
        }

        if (workerFilter !== 'all') {
            filtered = filtered.filter((exp) => exp.workerId === workerFilter);
        }

        if (dateFilter !== 'all') {
            const now = new Date();
            filtered = filtered.filter((exp) => {
                const expDate = new Date(exp.date);
                const diffTime = now.getTime() - expDate.getTime();
                const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));

                switch (dateFilter) {
                    case 'today': return diffDays === 1;
                    case 'week': return diffDays <= 7;
                    case 'month': return diffDays <= 30;
                    case '3months': return diffDays <= 90;
                    default: return true;
                }
            });
        }

        if (amountFilter !== 'all') {
            filtered = filtered.filter((exp) => {
                switch (amountFilter) {
                    case '0-5000': return exp.amount >= 0 && exp.amount < 5000;
                    case '5000-10000': return exp.amount >= 5000 && exp.amount < 10000;
                    case '10000-20000': return exp.amount >= 10000 && exp.amount < 20000;
                    case '20000-50000': return exp.amount >= 20000 && exp.amount < 50000;
                    case '50000+': return exp.amount >= 50000;
                    default: return true;
                }
            });
        }

        return filtered.sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime());
    }, [expenses, searchTerm, dateFilter, amountFilter, workerFilter]);

    const activeFiltersCount = [
        searchTerm ? 1 : 0,
        dateFilter !== 'all' ? 1 : 0,
        amountFilter !== 'all' ? 1 : 0,
        workerFilter !== 'all' ? 1 : 0,
    ].reduce((sum, val) => sum + val, 0);

    const handleClearFilters = () => {
        setSearchTerm('');
        setDateFilter('all');
        setAmountFilter('all');
        setWorkerFilter('all');
    };

    const handleExpenseClick = (expense: Expense) => {
        setSelectedExpense(expense);
        setModalOpen(true);
    };

    const totalAmount = filteredExpenses.reduce((sum, exp) => sum + exp.amount, 0);
    const totalPendientes = expenses.filter(exp => exp.estado === 'pendiente').length;

    const formatDate = (date: Date) => {
        return new Intl.DateTimeFormat('es-CL', {
            day: '2-digit',
            month: 'short',
            year: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
        }).format(date);
    };

const handleCerrarSesion = () => {
    localStorage.clear(); 
    sessionStorage.clear(); // Opcional, pero buena práctica
    window.location.href = '/'; 
};


    if (cargando) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-slate-300">
                <p className="text-cyan-700 font-medium text-lg">Cargando panel de contabilidad...</p>
            </div>
        );
    }

    return (
        <div className="flex h-screen bg-slate-300">
            {/* Barra Lateral Izquierda (Menú Contador) */}
            <aside className="w-64 bg-gradient-to-b from-cyan-700 to-cyan-600 text-white flex flex-col">
                <div className="p-6">
                    <div className="flex items-center gap-3 mb-1">
                        <img
                            src="/c-mvt_logo.png"
                            alt="Logo CMVT"
                            className="h-12 w-auto drop-shadow-md"
                        />
                        <h1 className="text-2xl font-semibold tracking-tight">Control Gastos</h1>
                    </div>
                    <p className="text-cyan-100 text-sm ml-11">Módulo de Contabilidad</p>
                </div>

                <nav className="flex-1 px-3 space-y-1">
                    <button
                        onClick={() => setActiveView('dashboard')}
                        className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-colors ${activeView === 'dashboard'
                            ? 'bg-white/20 backdrop-blur-sm'
                            : 'hover:bg-white/10'
                            }`}
                    >
                        <LayoutDashboard className="h-5 w-5" />
                        <span>Dashboard</span>
                    </button>
                    <button
                        onClick={() => setActiveView('calendar')}
                        className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-colors ${activeView === 'calendar'
                            ? 'bg-white/20 backdrop-blur-sm'
                            : 'hover:bg-white/10'
                            }`}
                    >
                        <CalendarIcon className="h-5 w-5" />
                        <span>Calendario</span>
                    </button>
                </nav>

                <div className="p-4 border-t border-cyan-500">
                    {onSwitchView && (
                        <button
                            onClick={onSwitchView}
                            className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-cyan-800/50 hover:bg-cyan-900/50 text-cyan-100 rounded-lg transition-colors text-sm border border-cyan-700"
                        >
                            <ArrowLeftRight className="h-4 w-4" />
                            Vista Simulación Terreno
                        </button>
                        
                        
                    )}
                </div>
            </aside>

            {/* Contenedor Principal */}
            <main className="flex-1 flex flex-col overflow-hidden">
                <header className="bg-white border-b border-gray-200 px-8 py-4">
                    <div className="flex items-center justify-between">
                        {/* Izquierda: Título y contador de rendiciones */}
                        <div>
                            <h2 className="text-2xl text-gray-900 font-semibold">
                                {activeView === 'dashboard' ? 'Auditoría de Boletas' : 'Calendario de Egresos'}
                            </h2>
                            <p className="text-sm text-gray-500 mt-1">
                                {filteredExpenses.length} rendiciones registradas en este filtro
                            </p>
                        </div>
                        
                        {/* Derecha: Botón PDF, Monto Total y Botón de Cerrar Sesión */}
                        <div className="flex items-center gap-6">
                            
                            {/* Menú de Exportación PDF */}
                            {filteredExpenses.length > 0 && (
                                <DropdownMenu>
                                    <DropdownMenuTrigger asChild>
                                        <Button variant="outline" className="gap-2 text-cyan-700 border-cyan-200 hover:bg-cyan-50">
                                            <Download className="h-4 w-4" />
                                            Exportar Reporte PDF
                                        </Button>
                                    </DropdownMenuTrigger>
                                    <DropdownMenuContent align="end" className="w-64 bg-white rounded-md shadow-xl border border-gray-200 p-1 z-50">
                                        <DropdownMenuItem
                                            className="flex items-center cursor-pointer hover:bg-gray-100 p-2 rounded text-sm text-gray-700"
                                            onClick={() => downloadMultipleExpensesPDF(filteredExpenses, 'Reporte de Boletas Filtradas')}
                                        >
                                            <FileDown className="h-4 w-4 mr-3 text-cyan-600" />
                                            Descargar vistas ({filteredExpenses.length})
                                        </DropdownMenuItem>
                                        <DropdownMenuSeparator className="bg-gray-200 my-1" />
                                        <DropdownMenuItem
                                            className="flex items-center cursor-pointer hover:bg-gray-100 p-2 rounded text-sm text-gray-700"
                                            onClick={() => downloadMultipleExpensesPDF(expenses, 'Reporte de Auditoría Total')}
                                        >
                                            <Receipt className="h-4 w-4 mr-3 text-cyan-600" />
                                            Descargar historial completo ({expenses.length})
                                        </DropdownMenuItem>
                                    </DropdownMenuContent>
                                </DropdownMenu>
                            )}
                            
                            {/* Total Desembolsado */}
                            <div className="text-right border-l border-gray-200 pl-6">
                                <p className="text-sm text-gray-500 font-medium">Total Desembolsado</p>
                                <p className="text-2xl font-bold text-cyan-600">${totalAmount.toLocaleString('es-CL')}</p>
                            </div>

                            {/* NUEVO: Botón Cerrar Sesión */}
                            <div className="pl-2">
                                {/* NUEVO: Botón Cerrar Sesión (Estilo unificado) */}
                            <div className="pl-2">
                                <button 
                                    onClick={handleCerrarSesion}
                                    className="bg-red-500 hover:bg-red-600 text-white text-sm font-semibold py-2 px-4 rounded-full transition-colors shadow-md"
                                >
                                    Cerrar Sesión
                                </button>
                            </div>
                            </div>

                        </div>
                    </div>
                </header>

                <div className="flex-1 overflow-auto p-8">
                    {activeView === 'dashboard' ? (
                        <div className="space-y-6">
                            {/* Tarjetas de Indicadores Clave */}
                            <div className="grid grid-cols-4 gap-4">
                                <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
                                    <div className="flex items-center justify-between">
                                        <div>
                                            <p className="text-sm text-gray-500 font-bold">Total Boletas</p>
                                            <p className="text-3xl mt-2 font-semibold text-gray-900">{filteredExpenses.length}</p>
                                        </div>
                                        <div className="bg-cyan-100 rounded-full p-3">
                                            <Receipt className="h-6 w-6 text-cyan-600" />
                                        </div>
                                    </div>
                                </div>

                                <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
                                    <div className="flex items-center justify-between">
                                        <div>
                                            <p className="text-sm text-gray-500 font-bold">Monto Filtrado</p>
                                            <p className="text-3xl mt-2 font-bold text-cyan-600">
                                                ${(totalAmount / 1000).toFixed(1)}k
                                            </p>
                                        </div>
                                        <div className="bg-green-100 rounded-full p-3">
                                            <TrendingDown className="h-6 w-6 text-green-600" />
                                        </div>
                                    </div>
                                </div>

                                <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
                                    <div className="flex items-center justify-between">
                                        <div>
                                            <p className="text-sm text-gray-500 font-bold">Gasto Promedio</p>
                                            <p className="text-3xl mt-2 font-semibold text-gray-900">
                                                ${filteredExpenses.length > 0 ? Math.round(totalAmount / filteredExpenses.length).toLocaleString('es-CL') : 0}
                                            </p>
                                        </div>
                                        <div className="bg-blue-100 rounded-full p-3">
                                            <Receipt className="h-6 w-6 text-blue-600" />
                                        </div>
                                    </div>
                                </div>

                                <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
                                    <div className="flex items-center justify-between">
                                        <div>
                                            <p className="text-sm text-gray-500 font-bold">Por Revisar</p>
                                            <p className="text-3xl mt-2 font-bold text-amber-600">{totalPendientes}</p>
                                        </div>
                                        <div className="bg-amber-100 rounded-full p-3">
                                            <Clock className="h-6 w-6 text-amber-600" />
                                        </div>
                                    </div>
                                </div>
                            </div>

                            {/* Panel de Filtros */}
                            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
                                <div className="flex items-center gap-4">
                                    <div className="flex items-center gap-2 flex-1">
                                        <Filter className="h-5 w-5 text-gray-400" />
                                        <span className="text-sm text-gray-600 font-medium">Filtros de Auditoría:</span>
                                        {activeFiltersCount > 0 && (
                                            <Badge className="bg-cyan-100 text-cyan-700">
                                                {activeFiltersCount} activos
                                            </Badge>
                                        )}
                                    </div>
                                    {activeFiltersCount > 0 && (
                                        <Button
                                            variant="ghost"
                                            size="sm"
                                            onClick={handleClearFilters}
                                            className="text-gray-600 hover:text-gray-900"
                                        >
                                            Limpiar filtros
                                        </Button>
                                    )}
                                </div>

                                <div className="grid grid-cols-4 gap-4 mt-4">
                                    <div className="relative">
                                        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
                                        <Input
                                            type="text"
                                            placeholder="Buscar por concepto..."
                                            value={searchTerm}
                                            onChange={(e) => setSearchTerm(e.target.value)}
                                            className="pl-10 pr-10 bg-white"
                                        />
                                        {searchTerm && (
                                            <button
                                                onClick={() => setSearchTerm('')}
                                                className="absolute right-3 top-1/2 -translate-y-1/2"
                                            >
                                                <X className="h-4 w-4 text-gray-400 hover:text-gray-600" />
                                            </button>
                                        )}
                                    </div>

                                    <Select value={workerFilter} onValueChange={setWorkerFilter}>
                                        <SelectTrigger className='bg-white'>
                                            <SelectValue placeholder="Filtrar por Operario" />
                                        </SelectTrigger>
                                        <SelectContent className='bg-white border border-gray-200 shadow-md'>
                                            <SelectItem value="all">Todos los operarios</SelectItem>
                                            {workersList.map((worker) => (
                                                <SelectItem key={worker.id} value={worker.id}>
                                                    {worker.name}
                                                </SelectItem>
                                            ))}
                                        </SelectContent>
                                    </Select>

                                    <Select value={dateFilter} onValueChange={setDateFilter}>
                                        <SelectTrigger className='bg-white'>
                                            <SelectValue placeholder="Período" />
                                        </SelectTrigger>
                                        <SelectContent className='bg-white border border-gray-200 shadow-md'>
                                            <SelectItem value="all">Todos los períodos</SelectItem>
                                            <SelectItem value="today">Hoy</SelectItem>
                                            <SelectItem value="week">Última semana</SelectItem>
                                            <SelectItem value="month">Último mes</SelectItem>
                                            <SelectItem value="3months">Últimos 3 meses</SelectItem>
                                        </SelectContent>
                                    </Select>

                                    <Select value={amountFilter} onValueChange={setAmountFilter}>
                                        <SelectTrigger className='bg-white'>
                                            <SelectValue placeholder="Rango de monto" />
                                        </SelectTrigger>
                                        <SelectContent className='bg-white border border-gray-200 shadow-md'>
                                            <SelectItem value="all">Todos los montos</SelectItem>
                                            <SelectItem value="0-5000">$0 - $5.000</SelectItem>
                                            <SelectItem value="5000-10000">$5.000 - $10.000</SelectItem>
                                            <SelectItem value="10000-20000">$10.000 - $20.000</SelectItem>
                                            <SelectItem value="20000-50000">$20.000 - $50.000</SelectItem>
                                            <SelectItem value="50000+">$50.000+</SelectItem>
                                        </SelectContent>
                                    </Select>
                                </div>
                            </div>

                            {/* Tabla de Rendiciones */}
                            <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
                                <Table>
                                    <TableHeader>
                                        <TableRow className="bg-gray-50">
                                            <TableHead className="w-[80px] text-center text-xs font-semibold text-gray-500 uppercase tracking-wider">Foto</TableHead>
                                            <TableHead className="w-[20%] text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Operario</TableHead>
                                            <TableHead className="w-[25%] text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Descripción / Concepto</TableHead>
                                            <TableHead className="w-[15%] text-right text-xs font-semibold text-gray-500 uppercase tracking-wider">Monto</TableHead>
                                            <TableHead className="w-[15%] text-center text-xs font-semibold text-gray-500 uppercase tracking-wider">Estado</TableHead>
                                            <TableHead className="w-[15%] text-center text-xs font-semibold text-gray-500 uppercase tracking-wider">Fecha de Rendición</TableHead>
                                            <TableHead className="w-[100px] text-center text-xs font-semibold text-gray-500 uppercase tracking-wider">Acción</TableHead>
                                        </TableRow>
                                    </TableHeader>
                                    <TableBody>
                                        {filteredExpenses.length === 0 ? (
                                            <TableRow>
                                                <TableCell colSpan={7} className="text-center py-12">
                                                    <div className="flex flex-col items-center text-gray-400">
                                                        <Receipt className="h-16 w-16 mb-4" />
                                                        <p className="font-medium">No hay boletas registradas en este período</p>
                                                    </div>
                                                </TableCell>
                                            </TableRow>
                                        ) : (
                                            filteredExpenses.map((expense) => (
                                                <TableRow
                                                    key={expense.id}
                                                    className="cursor-pointer hover:bg-cyan-50/50"
                                                    onClick={() => handleExpenseClick(expense)}
                                                >
                                                    <TableCell onClick={(e) => e.stopPropagation()}>
                                                        <img
                                                            src={expense.photo}
                                                            alt="Boleta"
                                                            className="w-12 h-12 object-cover rounded border border-gray-100 shadow-sm"
                                                        />
                                                    </TableCell>
                                                    <TableCell>
                                                        <span className="font-medium text-gray-800">{expense.workerName}</span>
                                                    </TableCell>
                                                    <TableCell className="font-medium text-gray-700">{expense.concept}</TableCell>
                                                    <TableCell className="text-right font-semibold text-cyan-600">
                                                        ${expense.amount.toLocaleString('es-CL')}
                                                    </TableCell>
                                                    <TableCell className="text-center">
                                                        <Badge className={
                                                            expense.estado === 'aprobado' ? 'bg-green-100 text-green-700 hover:bg-green-100 border-none' :
                                                            expense.estado === 'rechazado' ? 'bg-red-100 text-red-700 hover:bg-red-100 border-none' :
                                                            'bg-amber-100 text-amber-700 hover:bg-amber-100 border-none'
                                                        }>
                                                            {expense.estado.toUpperCase()}
                                                        </Badge>
                                                    </TableCell>
                                                    <TableCell className="text-gray-600 text-center text-xs">
                                                        {formatDate(expense.date)}
                                                    </TableCell>
                                                    <TableCell>
                                                        <Button
                                                            variant="outline"
                                                            size="sm"
                                                            className="border-cyan-200 text-cyan-700 hover:bg-cyan-50"
                                                            onClick={(e) => {
                                                                e.stopPropagation();
                                                                handleExpenseClick(expense);
                                                            }}
                                                        >
                                                            Auditar
                                                        </Button>
                                                    </TableCell>
                                                </TableRow>
                                            ))
                                        )}
                                    </TableBody>
                                </Table>
                            </div>
                        </div>
                    ) : (
                        <div>
                            <AdminCalendar
                                expenses={filteredExpenses}
                                onExpenseClick={handleExpenseClick}
                            />
                        </div>
                    )}
                </div>
            </main>

            {/* Modal de Detalle */}
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