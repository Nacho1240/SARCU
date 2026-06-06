import { useState } from 'react';
import { X, Calendar, Receipt, Download, CheckCircle, XCircle } from 'lucide-react';
import { Button } from './button';
import {
    Dialog,
    DialogContent,
    DialogHeader,
    DialogTitle,
} from './dialog';
import { downloadSingleExpensePDF } from './pdf-generator';

const GATEWAY_URL = import.meta.env.VITE_GATEWAY_URL || 'http://localhost:8000';

export interface Expense {
    id: string;
    workerId?: string;
    workerName?: string;
    concept: string;
    amount: number;
    photo: string;
    date: Date;
    estado: 'pendiente' | 'aprobado' | 'rechazado';
}

interface ExpenseDetailModalProps {
    expense: Expense | null;
    open: boolean;
    onClose: () => void;
}

export function ExpenseDetailModal({ expense, open, onClose }: ExpenseDetailModalProps) {
    const [isProcessing, setIsProcessing] = useState(false);

    if (!expense) return null;

    const formatDate = (date: Date) => {
        return new Intl.DateTimeFormat('es-CL', {
            weekday: 'long',
            day: '2-digit',
            month: 'long',
            year: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
        }).format(date);
    };

    const handleDownloadPDF = async () => {
        const expenseWithDefaults = {
            ...expense,
            workerId: expense.workerId || '1',
            workerName: expense.workerName || 'Trabajador',
        };
        await downloadSingleExpensePDF(expenseWithDefaults);
    };

    const handleCambiarEstado = async (nuevoEstado: 'aprobado' | 'rechazado') => {
        try {
            setIsProcessing(true);
            const token = localStorage.getItem('scg_token');
            
            let motivo = "";
            if (nuevoEstado === 'rechazado') {
                motivo = window.prompt("Ingresa el motivo del rechazo:") || "";
                if (!motivo.trim()) {
                    setIsProcessing(false);
                    return; // Si el usuario cancela, detenemos el proceso
                }
            }

            const res = await fetch(`${GATEWAY_URL}/gastos/${expense.id}/estado`, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ token, estado: nuevoEstado, motivo })
            });

            const data = await res.json();
            if (data.status === 'ok') {
                alert(`Gasto ${nuevoEstado} exitosamente.`);
                window.location.reload(); // Recarga la vista para ver los balances actualizados
            } else {
                alert(`Error: ${data.mensaje}`);
            }
        } catch (err) {
            alert("Error de conexión con el servidor.");
        } finally {
            setIsProcessing(false);
        }
    };

    return (
        <Dialog open={open} onOpenChange={onClose}>
            <DialogContent className="max-w-md bg-white rounded-xl shadow-xl border-none">
                <DialogHeader>
                    <DialogTitle>Detalles del Gasto</DialogTitle>
                </DialogHeader>
                <div className="space-y-4">
                    {/* Photo */}
                    <div>
                        <img
                            src={expense.photo}
                            alt="Boleta"
                            className="w-full h-64 object-cover rounded-lg"
                        />
                    </div>

                    {/* Details */}
                    <div className="space-y-3">
                        <div>
                            <div className="flex items-center gap-2 text-sm text-gray-600 mb-1">
                                <Receipt className="h-4 w-4" />
                                <span>Descripción</span>
                            </div>
                            <p className="text-gray-900">{expense.concept}</p>
                        </div>

                        <div>
                            <div className="text-sm text-gray-600 mb-1">Monto</div>
                            <p className="text-2xl text-cyan-600">
                                ${expense.amount.toLocaleString('es-CL')}
                            </p>
                        </div>

                        <div>
                            <div className="flex items-center gap-2 text-sm text-gray-600 mb-1">
                                <Calendar className="h-4 w-4" />
                                <span>Fecha</span>
                            </div>
                            <p className="text-gray-900 capitalize">{formatDate(expense.date)}</p>
                        </div>
                    </div>

                    {/* Botones de Auditoría si el gasto está pendiente */}
                    {expense.estado === 'pendiente' && (
                        <div className="flex gap-2 mt-4 pt-4 border-t border-gray-100">
                            <Button 
                                onClick={() => handleCambiarEstado('aprobado')} 
                                disabled={isProcessing}
                                className="flex-1 bg-green-600 hover:bg-green-700 text-white"
                            >
                                <CheckCircle className="h-4 w-4 mr-2" /> Aprobar
                            </Button>
                            <Button 
                                onClick={() => handleCambiarEstado('rechazado')} 
                                disabled={isProcessing}
                                variant="destructive" 
                                className="flex-1"
                            >
                                <XCircle className="h-4 w-4 mr-2" /> Rechazar
                            </Button>
                        </div>
                    )}

                    <div className="flex gap-2 mt-4">
                        <Button onClick={handleDownloadPDF} variant="outline" className="flex-1 text-cyan-800 border-cyan-200 hover:bg-cyan-50">
                            <Download className="h-4 w-4 mr-2" />
                            Descargar PDF
                        </Button>
                        <Button onClick={onClose} variant="outline" className="flex-1 border-gray-200 hover:bg-gray-50">
                            <X className="h-4 w-4 mr-2" />
                            Cerrar
                        </Button>
                    </div>
                </div>
            </DialogContent>
        </Dialog>
    );
}