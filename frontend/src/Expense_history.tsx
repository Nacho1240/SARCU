import { Receipt, Calendar, CheckCircle, XCircle, Clock } from 'lucide-react';

// 1. ACTUALIZAMOS LA INTERFAZ PARA QUE COINCIDA CON EL RESTO DE LA APP
interface Expense {
  id: string;
  concept: string;
  amount: number;
  photo: string;
  date: Date;
  estado: 'pendiente' | 'aprobado' | 'rechazado';
}

interface ExpenseHistoryProps {
  expenses: Expense[];
  onExpenseClick: (expense: Expense) => void;
}

export function ExpenseHistory({ expenses, onExpenseClick }: ExpenseHistoryProps) {
  const formatDate = (date: Date) => {
    return new Intl.DateTimeFormat('es-CL', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    }).format(date);
  };

  if (expenses.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-gray-400">
        <Receipt className="h-16 w-16 mb-4" />
        <p>No hay gastos reportados</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {expenses.map((expense) => (
        <button
          key={expense.id}
          onClick={() => onExpenseClick(expense)}
          className="w-full bg-white rounded-lg p-4 shadow-sm hover:shadow-md transition-shadow text-left border border-cyan-100 hover:border-cyan-300 relative"
        >
          {/* Indicador visual de estado para el Operario */}
          <div className="absolute top-4 right-4">
             {expense.estado === 'aprobado' && <CheckCircle className="h-5 w-5 text-green-500" />}
             {expense.estado === 'rechazado' && <XCircle className="h-5 w-5 text-red-500" />}
             {expense.estado === 'pendiente' && <Clock className="h-5 w-5 text-amber-500" />}
          </div>

          <div className="flex gap-3">
            <img
              src={expense.photo}
              alt="Boleta"
              className="w-16 h-16 object-cover rounded"
            />
            <div className="flex-1 min-w-0 pr-8">
              <p className="font-semibold text-gray-900 truncate">{expense.concept}</p>
              <p className="text-lg text-cyan-600 mt-1">
                -${expense.amount.toLocaleString('es-CL')}
              </p>
              <div className="flex items-center gap-1 text-xs text-gray-500 mt-2">
                <Calendar className="h-3 w-3" />
                <span>{formatDate(expense.date)}</span>
                <span className="mx-1">•</span>
                <span className="capitalize">{expense.estado}</span>
              </div>
            </div>
          </div>
        </button>
      ))}
    </div>
  );
}