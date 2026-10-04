export default function TableRenderer({ data }: { data: any }) {
  if (!data || !data.columns || !data.rows) return null;

  return (
    <div className="overflow-x-auto bg-white border border-gray-200 rounded-lg shadow-sm">
      <table className="min-w-full divide-y divide-gray-200 text-sm">
        <thead className="bg-gray-50">
          <tr>
            {data.columns.map((col: string, i: number) => (
              <th key={i} className="px-4 py-3 text-left font-medium text-gray-500 uppercase tracking-wider">
                {col}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="bg-white divide-y divide-gray-200">
          {data.rows.map((row: any[], i: number) => (
            <tr key={i} className="hover:bg-gray-50">
              {row.map((cell: any, j: number) => (
                <td key={j} className="px-4 py-3 text-gray-700 whitespace-nowrap">
                  {cell !== null ? cell.toString() : '-'}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      {data.total_rows > data.rows.length && (
        <div className="p-3 text-center text-xs text-gray-500 bg-gray-50 border-t border-gray-200">
          Showing {data.rows.length} of {data.total_rows} rows.
        </div>
      )}
    </div>
  );
}
