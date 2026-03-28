import React, { useState, useMemo, useCallback } from 'react'
import './TableRenderer.css'

function SortIcon({ direction }) {
  if (!direction) {
    return (
      <svg className="sort-icon" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="M7 15l5 5 5-5M7 9l5-5 5 5" />
      </svg>
    )
  }
  return direction === 'asc' ? (
    <svg className="sort-icon active" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M7 15l5 5 5-5" />
    </svg>
  ) : (
    <svg className="sort-icon active" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M7 9l5-5 5 5" />
    </svg>
  )
}

function SearchIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <circle cx="11" cy="11" r="8" />
      <path d="M21 21l-4.35-4.35" />
    </svg>
  )
}

function DownloadIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M7 10l5 5 5-5M12 15V3" />
    </svg>
  )
}

function CopyIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
      <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
    </svg>
  )
}

export function TableRenderer({ config }) {
  const [sortConfig, setSortConfig] = useState({ key: null, direction: null })
  const [searchTerm, setSearchTerm] = useState('')
  const [currentPage, setCurrentPage] = useState(1)
  const [rowsPerPage, setRowsPerPage] = useState(10)
  const [copied, setCopied] = useState(false)

  const { title, columns, rows, sortable = true, exportable = true, searchable = true } = config || {}

  const normalizedData = useMemo(() => {
    if (!columns || !rows) return []
    return rows.map((row, rowIndex) => {
      if (Array.isArray(row)) {
        const obj = { _rowIndex: rowIndex }
        columns.forEach((col, colIndex) => {
          obj[col] = row[colIndex]
        })
        return obj
      }
      return { ...row, _rowIndex: rowIndex }
    })
  }, [columns, rows])

  const filteredData = useMemo(() => {
    if (!searchTerm) return normalizedData
    const term = searchTerm.toLowerCase()
    return normalizedData.filter(row =>
      columns.some(col => {
        const value = row[col]
        return value != null && String(value).toLowerCase().includes(term)
      })
    )
  }, [normalizedData, searchTerm, columns])

  const sortedData = useMemo(() => {
    if (!sortConfig.key || !sortConfig.direction) return filteredData
    return [...filteredData].sort((a, b) => {
      const aVal = a[sortConfig.key]
      const bVal = b[sortConfig.key]
      if (aVal == null) return 1
      if (bVal == null) return -1
      if (typeof aVal === 'number' && typeof bVal === 'number') {
        return sortConfig.direction === 'asc' ? aVal - bVal : bVal - aVal
      }
      const aStr = String(aVal).toLowerCase()
      const bStr = String(bVal).toLowerCase()
      if (aStr < bStr) return sortConfig.direction === 'asc' ? -1 : 1
      if (aStr > bStr) return sortConfig.direction === 'asc' ? 1 : -1
      return 0
    })
  }, [filteredData, sortConfig])

  const totalPages = Math.ceil(sortedData.length / rowsPerPage)
  const paginatedData = useMemo(() => {
    const start = (currentPage - 1) * rowsPerPage
    return sortedData.slice(start, start + rowsPerPage)
  }, [sortedData, currentPage, rowsPerPage])

  const handleSort = useCallback((column) => {
    if (!sortable) return
    setSortConfig(prev => {
      if (prev.key === column) {
        if (prev.direction === 'asc') return { key: column, direction: 'desc' }
        if (prev.direction === 'desc') return { key: null, direction: null }
      }
      return { key: column, direction: 'asc' }
    })
  }, [sortable])

  const exportToCSV = useCallback(() => {
    const csvRows = [columns.join(',')]
    sortedData.forEach(row => {
      const values = columns.map(col => {
        const val = row[col]
        if (val == null) return ''
        const str = String(val)
        if (str.includes(',') || str.includes('"') || str.includes('\n')) {
          return `"${str.replace(/"/g, '""')}"`
        }
        return str
      })
      csvRows.push(values.join(','))
    })
    const csvContent = csvRows.join('\n')
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `${title || 'table'}_export.csv`
    link.click()
    URL.revokeObjectURL(url)
  }, [columns, sortedData, title])

  const copyToClipboard = useCallback(async () => {
    const text = [columns.join('\t')]
    sortedData.forEach(row => {
      const values = columns.map(col => row[col] ?? '')
      text.push(values.join('\t'))
    })
    try {
      await navigator.clipboard.writeText(text.join('\n'))
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch (err) {
      console.error('Failed to copy:', err)
    }
  }, [columns, sortedData])

  if (!columns || !rows) {
    return <div className="table-error">No table data provided</div>
  }

  return (
    <div className="table-container">
      {title && <h3 className="table-title">{title}</h3>}
      
      <div className="table-toolbar">
        {searchable && (
          <div className="table-search">
            <SearchIcon />
            <input
              type="text"
              placeholder="Search..."
              value={searchTerm}
              onChange={(e) => {
                setSearchTerm(e.target.value)
                setCurrentPage(1)
              }}
            />
          </div>
        )}
        
        <div className="table-actions">
          {exportable && (
            <>
              <button className="table-action-btn" onClick={copyToClipboard} title="Copy to clipboard">
                <CopyIcon />
                {copied ? 'Copied!' : 'Copy'}
              </button>
              <button className="table-action-btn" onClick={exportToCSV} title="Export to CSV">
                <DownloadIcon />
                Export CSV
              </button>
            </>
          )}
        </div>
      </div>

      <div className="table-wrapper">
        <table className="data-table">
          <thead>
            <tr>
              {columns.map((col, index) => (
                <th
                  key={index}
                  onClick={() => handleSort(col)}
                  className={sortable ? 'sortable' : ''}
                >
                  <span className="th-content">
                    {col}
                    {sortable && (
                      <SortIcon direction={sortConfig.key === col ? sortConfig.direction : null} />
                    )}
                  </span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {paginatedData.length === 0 ? (
              <tr>
                <td colSpan={columns.length} className="no-data">
                  {searchTerm ? 'No matching results' : 'No data available'}
                </td>
              </tr>
            ) : (
              paginatedData.map((row, rowIndex) => (
                <tr key={row._rowIndex ?? rowIndex}>
                  {columns.map((col, colIndex) => (
                    <td key={colIndex}>
                      {row[col] != null ? String(row[col]) : ''}
                    </td>
                  ))}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {sortedData.length > 10 && (
        <div className="table-pagination">
          <div className="pagination-info">
            Showing {((currentPage - 1) * rowsPerPage) + 1} to {Math.min(currentPage * rowsPerPage, sortedData.length)} of {sortedData.length} rows
          </div>
          
          <div className="pagination-controls">
            <select
              value={rowsPerPage}
              onChange={(e) => {
                setRowsPerPage(Number(e.target.value))
                setCurrentPage(1)
              }}
              className="rows-select"
            >
              <option value={10}>10 rows</option>
              <option value={25}>25 rows</option>
              <option value={50}>50 rows</option>
              <option value={100}>100 rows</option>
            </select>
            
            <div className="pagination-buttons">
              <button
                onClick={() => setCurrentPage(1)}
                disabled={currentPage === 1}
                className="pagination-btn"
              >
                First
              </button>
              <button
                onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                disabled={currentPage === 1}
                className="pagination-btn"
              >
                Prev
              </button>
              <span className="page-indicator">
                Page {currentPage} of {totalPages}
              </span>
              <button
                onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
                disabled={currentPage === totalPages}
                className="pagination-btn"
              >
                Next
              </button>
              <button
                onClick={() => setCurrentPage(totalPages)}
                disabled={currentPage === totalPages}
                className="pagination-btn"
              >
                Last
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
