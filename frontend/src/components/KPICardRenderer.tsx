import { AlertCircle } from 'lucide-react';

export default function KPICardRenderer({ data }: { data: any }) {
  if (!data) return null;

  return (
    <div className="bg-blue-50 border border-blue-100 rounded-lg p-4 flex flex-col min-w-[200px]">
      <div className="text-sm font-medium text-blue-800 uppercase tracking-wide">
        {data.kpi_name}
      </div>
      <div className="mt-2 flex items-baseline">
        <span className="text-3xl font-bold text-blue-900">
          {data.value !== null ? data.value : 'N/A'}
        </span>
        {data.unit && (
          <span className="ml-1 text-sm font-medium text-blue-700">{data.unit}</span>
        )}
      </div>
      
      <div className="mt-3 flex flex-wrap gap-2 text-xs text-blue-700">
        {data.line && <span className="bg-white px-2 py-1 rounded shadow-sm border border-blue-100">Line: {data.line}</span>}
        {data.shift && <span className="bg-white px-2 py-1 rounded shadow-sm border border-blue-100">Shift: {data.shift}</span>}
        {data.period && <span className="bg-white px-2 py-1 rounded shadow-sm border border-blue-100">Period: {data.period}</span>}
      </div>

      {!data.is_formula_confirmed && (
        <div className="mt-4 flex items-start space-x-2 text-xs text-orange-700 bg-orange-50 p-2 rounded border border-orange-200">
          <AlertCircle size={14} className="mt-0.5 flex-shrink-0" />
          <span>{data.formula_note}</span>
        </div>
      )}
    </div>
  );
}
