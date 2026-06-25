interface DataTableProps {
  columns: string[];
  rows: Record<string, unknown>[];
}

export function DataTable({ columns, rows }: DataTableProps) {
  if (!rows.length) return null;

  return (
    <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
      <div className="px-5 py-3 border-b border-gray-100">
        <h3 className="text-sm font-semibold text-gray-700">Données</h3>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-gray-50">
              {columns.map((col) => (
                <th
                  key={col}
                  className="px-4 py-2.5 text-left font-medium text-gray-600 whitespace-nowrap"
                >
                  {col}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.slice(0, 50).map((row, i) => (
              <tr
                key={i}
                className="border-t border-gray-50 hover:bg-blue-50/30 transition-colors"
              >
                {columns.map((col) => (
                  <td key={col} className="px-4 py-2 text-gray-700 whitespace-nowrap">
                    {row[col] !== null && row[col] !== undefined
                      ? String(row[col])
                      : '—'}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {rows.length > 50 && (
        <div className="px-5 py-2 text-xs text-gray-400 border-t border-gray-100">
          Affichage de 50 lignes sur {rows.length}
        </div>
      )}
    </div>
  );
}
