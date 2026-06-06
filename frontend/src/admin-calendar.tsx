import { useState, useMemo } from 'react';
import { ChevronLeft, ChevronRight, Receipt, User, Download } from 'lucide-react';
import { Button } from './button';
import { Badge } from './badge';
import { downloadMultipleExpensesPDF } from './pdf-generator';

interface Expense {
    id: string;
    concept: string;
    amount: number;
    photo: string;
    date: Date;
    workerName?: string;
    estado: 'pendiente' | 'aprobado' | 'rechazado'; // <--- AGREGA ESTA LÍNEA
}

interface AdminCalendarProps {
    expenses: Expense[];
    onExpenseClick: (expense: Expense) => void;
}

export function AdminCalendar({ expenses, onExpenseClick }: AdminCalendarProps) {
    const [currentDate, setCurrentDate] = useState(new Date());
    const [selectedDay, setSelectedDay] = useState<number | null>(null);
    const [isDownloading, setIsDownloading] = useState(false);

    const expensesByDay = useMemo(() => {
        const map = new Map<number, Expense[]>();
        expenses.forEach((expense) => {
            const expDate = new Date(expense.date);
            if (
                expDate.getMonth() === currentDate.getMonth() &&
                expDate.getFullYear() === currentDate.getFullYear()
            ) {
                const day = expDate.getDate();
                if (!map.has(day)) {
                    map.set(day, []);
                }
                map.get(day)!.push(expense);
            }
        });
        return map;
    }, [expenses, currentDate]);

    const getDaysInMonth = (date: Date) => {
        const year = date.getFullYear();
        const month = date.getMonth();
        return new Date(year, month + 1, 0).getDate();
    };

    const getFirstDayOfMonth = (date: Date) => {
        const year = date.getFullYear();
        const month = date.getMonth();
        const firstDay = new Date(year, month, 1).getDay();
        return firstDay === 0 ? 6 : firstDay - 1;
    };

    const previousMonth = () => {
        setCurrentDate(new Date(currentDate.getFullYear(), currentDate.getMonth() - 1, 1));
        setSelectedDay(null);
    };

    const nextMonth = () => {
        setCurrentDate(new Date(currentDate.getFullYear(), currentDate.getMonth() + 1, 1));
        setSelectedDay(null);
    };

    const monthName = currentDate.toLocaleDateString('es-CL', { month: 'long', year: 'numeric' });
    const daysInMonth = getDaysInMonth(currentDate);
    const firstDay = getFirstDayOfMonth(currentDate);

    const days = [];
    for (let i = 0; i < firstDay; i++) {
        days.push(null);
    }
    for (let i = 1; i <= daysInMonth; i++) {
        days.push(i);
    }

    const weekDays = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo'];

    const selectedDayExpenses = selectedDay ? expensesByDay.get(selectedDay) || [] : [];

    const formatDate = (date: Date) => {
        return new Intl.DateTimeFormat('es-CL', {
            day: '2-digit',
            month: 'short',
            hour: '2-digit',
            minute: '2-digit',
        }).format(date);
    };

    const monthExpenses = expenses.filter((exp) => {
        const expDate = new Date(exp.date);
        return (
            expDate.getMonth() === currentDate.getMonth() &&
            expDate.getFullYear() === currentDate.getFullYear()
        );
    });

    const monthTotalAmount = monthExpenses.reduce((sum, exp) => sum + exp.amount, 0);

    const handleDownload = async (type: 'day' | 'week' | 'month') => {
        setIsDownloading(true);
        try {
            let expensesToDownload: Expense[] = [];
            let title = '';

            if (type === 'day' && selectedDay) {
                expensesToDownload = selectedDayExpenses;
                title = `Día ${selectedDay} de ${monthName}`;
            } else if (type === 'week' && selectedDay) {
                const date = new Date(currentDate.getFullYear(), currentDate.getMonth(), selectedDay);
                const dayOfWeek = date.getDay() || 7;
                const monday = new Date(date);
                monday.setDate(date.getDate() - dayOfWeek + 1);
                const sunday = new Date(date);
                sunday.setDate(date.getDate() - dayOfWeek + 7);

                expensesToDownload = expenses.filter(exp => {
                    const d = new Date(exp.date);
                    const expDateOnly = new Date(d.getFullYear(), d.getMonth(), d.getDate());
                    const monOnly = new Date(monday.getFullYear(), monday.getMonth(), monday.getDate());
                    const sunOnly = new Date(sunday.getFullYear(), sunday.getMonth(), sunday.getDate());
                    return expDateOnly >= monOnly && expDateOnly <= sunOnly;
                });
                title = `Semana del ${monday.getDate()} al ${sunday.getDate()} de ${monthName}`;
            } else if (type === 'month') {
                expensesToDownload = monthExpenses;
                title = `Mes de ${monthName}`;
            }

            if (expensesToDownload.length > 0) {
                await downloadMultipleExpensesPDF(expensesToDownload, title);
            }
        } finally {
            setIsDownloading(false);
        }
    };

    return (
        <div className="grid grid-cols-3 gap-6">
            <div className="col-span-2 bg-white rounded-xl shadow-sm border border-gray-200 p-6">
                <div className="flex items-center justify-between mb-6">
                    <h3 className="text-xl font-semibold text-gray-900 capitalize">{monthName}</h3>
                    <div className="flex gap-2">
                        <Button variant="outline" size="sm" onClick={previousMonth}>
                            <ChevronLeft className="h-4 w-4" />
                        </Button>
                        <Button variant="outline" size="sm" onClick={nextMonth}>
                            <ChevronRight className="h-4 w-4" />
                        </Button>
                    </div>
                </div>

                <div className="space-y-2">
                    <div className="grid grid-cols-7 gap-2">
                        {weekDays.map((day) => (
                            <div
                                key={day}
                                className="text-center text-sm font-medium text-gray-500 p-3"
                            >
                                {day}
                            </div>
                        ))}
                    </div>

                    <div className="grid grid-cols-7 gap-2">
                        {days.map((day, index) => {
                            if (day === null) {
                                return <div key={`empty-${index}`} className="aspect-square" />;
                            }

                            const dayExpenses = expensesByDay.get(day) || [];
                            const totalAmount = dayExpenses.reduce((sum, exp) => sum + exp.amount, 0);
                            const isToday =
                                day === new Date().getDate() &&
                                currentDate.getMonth() === new Date().getMonth() &&
                                currentDate.getFullYear() === new Date().getFullYear();
                            const isSelected = day === selectedDay;

                            return (
                                <button
                                    key={day}
                                    onClick={() => setSelectedDay(day)}
                                    className={`aspect-square border-2 rounded-lg p-3 transition-all flex flex-col items-start justify-between ${isSelected
                                            ? 'border-cyan-500 bg-cyan-50 shadow-md ring-2 ring-cyan-500/20'
                                            : isToday
                                                ? 'border-cyan-300 bg-cyan-50/50'
                                                : 'border-gray-100 hover:border-cyan-300 hover:bg-gray-50'
                                        } ${dayExpenses.length > 0 ? 'cursor-pointer' : 'cursor-default'}`}
                                >
                                    <span className={`text-sm font-medium ${isToday ? 'text-cyan-700' : 'text-gray-700'}`}>
                                        {day}
                                    </span>
                                    {dayExpenses.length > 0 && (
                                        <div className="w-full flex flex-col gap-1 items-start mt-1">
                                            <Badge className="bg-cyan-600 hover:bg-cyan-700 text-white px-1.5 py-0 text-[10px] w-full justify-center">
                                                {dayExpenses.length} {dayExpenses.length === 1 ? 'gasto' : 'gastos'}
                                            </Badge>
                                            <span className="text-[11px] font-semibold text-cyan-700 w-full text-center">
                                                ${(totalAmount / 1000).toFixed(1)}k
                                            </span>
                                        </div>
                                    )}
                                </button>
                            );
                        })}
                    </div>
                </div>

                <div className="mt-6 pt-6 border-t border-gray-200">
                    <div className="grid grid-cols-2 gap-4">
                        <div>
                            <p className="text-sm text-gray-500">Gastos este mes</p>
                            <p className="text-2xl font-bold text-gray-900 mt-1">
                                {monthExpenses.length}
                            </p>
                        </div>
                        <div>
                            <p className="text-sm text-gray-500">Total del mes</p>
                            <p className="text-2xl font-bold text-cyan-600 mt-1">
                                ${monthTotalAmount.toLocaleString('es-CL')}
                            </p>
                        </div>
                    </div>
                </div>
            </div>

            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 flex flex-col h-full">
                <div className="mb-4 pb-4 border-b border-gray-100 flex flex-col gap-3">
                    <h4 className="font-semibold text-gray-900">
                        {selectedDay
                            ? `Gastos del día ${selectedDay}`
                            : 'Detalle de gastos'}
                    </h4>
                    <div className="flex gap-2">
                        <Button
                            variant="outline"
                            size="sm"
                            className="text-xs flex-1 px-2 text-cyan-600 border-cyan-200 hover:bg-cyan-50 hover:text-cyan-700 hover:border-cyan-300 transition-colors disabled:opacity-50"
                            disabled={!selectedDay || selectedDayExpenses.length === 0 || isDownloading}
                            onClick={() => handleDownload('day')}
                        >
                            <Download className="h-3 w-3 mr-1" /> Día
                        </Button>
                        <Button
                            variant="outline"
                            size="sm"
                            className="text-xs flex-1 px-2 text-cyan-600 border-cyan-200 hover:bg-cyan-50 hover:text-cyan-700 hover:border-cyan-300 transition-colors disabled:opacity-50"
                            disabled={!selectedDay || isDownloading}
                            onClick={() => handleDownload('week')}
                        >
                            <Download className="h-3 w-3 mr-1" /> Sem
                        </Button>
                        <Button
                            variant="outline"
                            size="sm"
                            
                            className="text-xs flex-1 px-2 bg-cyan-100 hover:bg-cyan-200 text-cyan-800 border-cyan-300 font-medium transition-colors disabled:opacity-50 disabled:bg-cyan-50"
                            disabled={monthExpenses.length === 0 || isDownloading}
                            onClick={() => handleDownload('month')}
                        >
                            <Download className="h-3 w-3 mr-1" /> Mes
                        </Button>
                    </div>
                </div>

                <div className="flex-1 overflow-y-auto pr-2 custom-scrollbar">
                    {selectedDay && selectedDayExpenses.length > 0 ? (
                        <div className="space-y-3">
                            {selectedDayExpenses.map((expense) => (
                                <button
                                    key={expense.id}
                                    onClick={() => onExpenseClick(expense)}
                                    className="w-full bg-white hover:bg-cyan-50/50 rounded-xl p-3 text-left border border-gray-200 hover:border-cyan-300 transition-all shadow-sm hover:shadow group"
                                >
                                    <div className="flex gap-3">
                                        <img
                                            src={expense.photo}
                                            alt="Boleta"
                                            className="w-14 h-14 object-cover rounded-lg border border-gray-100"
                                        />
                                        <div className="flex-1 min-w-0 flex flex-col justify-center">
                                            <p className="text-sm font-semibold text-gray-900 truncate">
                                                {expense.concept}
                                            </p>
                                            <div className="flex items-center gap-1.5 mt-0.5">
                                                <User className="h-3 w-3 text-gray-400" />
                                                <p className="text-xs text-gray-500 truncate">
                                                    {expense.workerName || 'Desconocido'}
                                                </p>
                                            </div>
                                            <div className="flex items-center justify-between mt-1.5">
                                                <p className="text-sm font-bold text-cyan-600">
                                                    ${expense.amount.toLocaleString('es-CL')}
                                                </p>
                                                <p className="text-[10px] text-gray-400 font-medium">
                                                    {formatDate(expense.date)}
                                                </p>
                                            </div>
                                        </div>
                                    </div>
                                </button>
                            ))}

                            <div className="mt-4 pt-4 border-t border-gray-100">
                                <div className="flex justify-between items-center bg-gray-50 p-3 rounded-lg border border-gray-200">
                                    <span className="text-sm text-gray-600 font-medium">Total del día</span>
                                    <span className="text-lg font-bold text-cyan-600">
                                        ${selectedDayExpenses.reduce((sum, exp) => sum + exp.amount, 0).toLocaleString('es-CL')}
                                    </span>
                                </div>
                            </div>
                        </div>
                    ) : selectedDay ? (
                        <div className="flex flex-col items-center justify-center h-full text-gray-400 space-y-3">
                            <div className="bg-gray-50 p-4 rounded-full">
                                <Receipt className="h-8 w-8 text-gray-300" />
                            </div>
                            <p className="text-sm text-center font-medium">No hay gastos registrados</p>
                        </div>
                    ) : (
                        <div className="flex flex-col items-center justify-center h-full text-gray-400 space-y-3">
                            <div className="bg-cyan-50 p-4 rounded-full">
                                <Receipt className="h-8 w-8 text-cyan-300" />
                            </div>
                            <p className="text-sm text-center font-medium text-gray-500">Selecciona un día en el calendario</p>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}