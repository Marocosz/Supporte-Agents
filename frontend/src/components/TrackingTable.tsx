// frontend/src/components/TrackingTable.tsx
import React from 'react';
import type { DatabaseRow } from '../types/bi.types'; 

interface TrackingTableProps {
  data: DatabaseRow[] | string | any; // Aceita string temporariamente para não quebrar
}

const getStatusColor = (status: string | number | boolean | null | undefined) => {
  const s = String(status || '').toUpperCase();
  if (s.includes('EXPEDIDO')) return 'bg-green-100 text-green-800';
  if (s.includes('BLOQUEADO') || s.includes('CANCELADO')) return 'bg-red-100 text-red-800';
  if (s.includes('SEPARAÇÃO') || s.includes('ONDA')) return 'bg-yellow-100 text-yellow-800';
  return 'bg-gray-100 text-gray-800';
};

export const TrackingTable: React.FC<TrackingTableProps> = ({ data }) => {
  // 1. BLINDAGEM: Se vier nulo/undefined, não renderiza nada
  if (!data) return null;

  let safeData: DatabaseRow[] = [];

  // 2. TRATAMENTO: Tenta converter se for string
  if (Array.isArray(data)) {
    safeData = data;
  } else if (typeof data === 'string') {
    try {
      // Tenta corrigir aspas simples de Python para aspas duplas de JSON (fallback básico)
      // Nota: O ideal é o backend mandar certo, isso é apenas um 'bandage'
      const fixedJson = data.replace(/'/g, '"').replace(/None/g, 'null').replace(/True/g, 'true').replace(/False/g, 'false');
      const parsed = JSON.parse(fixedJson);
      if (Array.isArray(parsed)) safeData = parsed;
    } catch (e) {
      console.error("Erro ao fazer parse dos dados da tabela:", e);
      return (
        <div className="p-3 bg-red-50 text-red-700 text-xs rounded border border-red-200">
          Erro de formato de dados. O backend retornou texto em vez de JSON.
          <br/>Conteúdo bruto: {data.substring(0, 50)}...
        </div>
      );
    }
  }

  // 3. VALIDAÇÃO FINAL: Se ainda não for array ou estiver vazio
  if (!Array.isArray(safeData) || safeData.length === 0) {
    return <div className="text-gray-500 text-sm italic p-2">Nenhum dado estruturado encontrado.</div>;
  }

  const columns = Object.keys(safeData[0]);

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
          {safeData.map((row, idx) => (
            <tr key={idx} className="hover:bg-gray-50">
              {columns.map((col) => (
                <td key={`${idx}-${col}`} className="px-4 py-3 whitespace-nowrap text-gray-700">
                  {col === 'STA_NOTA' ? (
                    <span className={`px-2 py-1 rounded-full text-xs font-semibold ${getStatusColor(row[col])}`}>
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