import { Button } from '../ui'

export function PaginationControls({
  page,
  totalPages,
  pageSize,
  onPageChange,
  onPageSizeChange,
}: {
  page: number
  totalPages: number
  pageSize?: number
  onPageChange: (page: number) => void
  onPageSizeChange?: (pageSize: number) => void
}) {
  return (
    <div className="pagination">
      <Button variant="ghost" size="sm" disabled={page <= 1} onClick={() => onPageChange(page - 1)}>
        上一页
      </Button>
      <span>第 {page} / {totalPages} 页</span>
      <Button variant="ghost" size="sm" disabled={page >= totalPages} onClick={() => onPageChange(page + 1)}>
        下一页
      </Button>
      {pageSize && onPageSizeChange ? (
        <label className="pagination-size">
          每页
          <select
            value={pageSize}
            onChange={(event) => {
              onPageChange(1)
              onPageSizeChange(Number(event.target.value))
            }}
          >
            {[10, 20, 50, 100].map((size) => <option key={size} value={size}>{size} 条</option>)}
          </select>
        </label>
      ) : null}
    </div>
  )
}
