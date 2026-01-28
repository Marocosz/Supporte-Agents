// frontend/src/components/TrackingTable.tsx
import React from 'react';
import type { DatabaseRow } from '../types/bi.types'; 

interface TrackingTableProps {
  // Tipagem forte: Array de registros do banco (sem any)
  data: DatabaseRow[];
}

// Aceita a união de tipos primitivos possíveis em uma célula de banco
const getStatusColor = (status: string | number | boolean | null | undefined) => {
  const s = String(status || '').toUpperCase();
  if (s.includes('EXPEDIDO')) return 'bg-green-100 text-green-800';
  if (s.includes('BLOQUEADO') || s.includes('CANCELADO')) return 'bg-red-100 text-red-800';
  if (s.includes('SEPARAÇÃO') || s.includes('ONDA')) return 'bg-yellow-100 text-yellow-800';
  return 'bg-gray-100 text-gray-800';
};

export const TrackingTable: React.FC<TrackingTableProps> = ({ data }) => {
  if (!data || data.length === 0) return null;

  const columns = Object.keys(data[0]);

  return (
    <div className="overflow-x-auto rounded-lg border border-gray-200 shadow-sm mt-3">
      <table className="min-w-full divide-y divide-gray-200 text-sm">
        <thead className="bg-gray-50">
          <tr>
            {columns.map((col) => (
              <th key={col} className="px-4 py-3 text-left font-medium text-gray-500 uppercase tracking-wider">
                {col.replace('_', ' ')}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="bg-white divide-y divide-gray-200">
          {data.map((row, idx) => (
            <tr key={idx} className="hover:bg-gray-50">
              {columns.map((col) => (
                <td key={`${idx}-${col}`} className="px-4 py-3 whitespace-nowrap text-gray-700">
                  {col === 'STA_NOTA' ? (
                    <span className={`px-2 py-1 rounded-full text-xs font-semibold ${getStatusColor(row[col])}`}>
                      {/* String() converte null/undefined/boolean para texto seguro */}
                      {String(row[col] || '')}
                    </span>
                  ) : (
                    String(row[col] ?? '-')
                  )}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};