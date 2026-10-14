interface Props {
  cells: number[][]
  peak: number
}

// A sequential blue ramp, light (few) to dark (many), on the dark surface. Counts are shown
// in each cell as well, so the value never depends on colour alone.
function shade(value: number, peak: number): string {
  if (value === 0 || peak === 0) return 'transparent'
  const t = 0.2 + 0.8 * (value / peak)
  return `rgba(111, 155, 255, ${t.toFixed(2)})`
}

/**
 * A grid standing for the room as the camera sees it: the top of the grid is the back of the
 * room (farthest from the camera at the front), left and right match the camera's view.
 */
export function Heatmap({ cells, peak }: Props) {
  const grid = cells.length
  return (
    <div>
      <div className="mb-2 flex items-center justify-between text-xs text-muted">
        <span>Back of room</span>
        <span>Fewer → more</span>
      </div>
      <div
        className="grid gap-1 rounded-xl border border-line bg-canvas p-2"
        style={{ gridTemplateColumns: `repeat(${grid}, minmax(0, 1fr))` }}
        role="img"
        aria-label="Grid of the room showing where the chosen observation happened most; each cell shows its count."
      >
        {cells.flatMap((rowCells, row) =>
          rowCells.map((value, column) => (
            <div
              key={`${row}-${column}`}
              className="flex aspect-square items-center justify-center rounded-md text-xs font-semibold tabular-nums"
              style={{ background: shade(value, peak), color: value > peak * 0.6 ? '#081018' : 'var(--color-muted)' }}
              title={`Row ${row + 1}, column ${column + 1}: ${value}`}
            >
              {value || ''}
            </div>
          )),
        )}
      </div>
      <p className="mt-2 text-center text-xs text-muted">Front of room (camera)</p>
    </div>
  )
}
