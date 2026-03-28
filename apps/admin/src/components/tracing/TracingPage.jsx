import React, { useState, useEffect, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { tracingApi } from '../../services'
import { RefreshIcon, SearchIcon, FilterIcon } from '../common/Icons'
import TraceList from './TraceList'
import TraceDetailPanel from './TraceDetailPanel'
import './Tracing.css'

const TracingPage = () => {
  const [stats, setStats] = useState(null)
  const [traces, setTraces] = useState([])
  const [total, setTotal] = useState(0)
  const [isLoading, setIsLoading] = useState(true)
  const [isRefreshing, setIsRefreshing] = useState(false)
  const [error, setError] = useState(null)
  const [traceError, setTraceError] = useState(null)
  const [selectedTrace, setSelectedTrace] = useState(null)
  const [nameFilter, setNameFilter] = useState('')
  const [appliedNameFilter, setAppliedNameFilter] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [offset, setOffset] = useState(0)
  const limit = 25

  const loadStats = useCallback(async () => {
    try {
      const response = await tracingApi.getStats(7)
      setStats(response.data)
    } catch (err) {
      console.error('Failed to load tracing stats:', err)
    }
  }, [])

  const loadTraces = useCallback(async (showLoading = true) => {
    if (showLoading) {
      setIsLoading(true)
    } else {
      setIsRefreshing(true)
    }
    setError(null)

    try {
      const params = {
        limit,
        offset,
        name_filter: appliedNameFilter || undefined,
        status: statusFilter || undefined,
      }
      const response = await tracingApi.getTraces(params)
      setTraces(response.data.traces || [])
      setTotal(response.data.total || 0)
    } catch (err) {
      console.error('Failed to load traces:', err)
      setError(err.response?.data?.detail || 'Failed to load traces')
    } finally {
      setIsLoading(false)
      setIsRefreshing(false)
    }
  }, [offset, appliedNameFilter, statusFilter])

  useEffect(() => {
    loadStats()
    loadTraces()
  }, [loadStats, loadTraces])

  const handleRefresh = () => {
    loadStats()
    loadTraces(false)
  }

  const handleFilterChange = (e) => {
    setNameFilter(e.target.value)
  }

  const handleFilterKeyPress = (e) => {
    if (e.key === 'Enter') {
      setOffset(0)
      setAppliedNameFilter(nameFilter)
    }
  }

  const handleSearchClick = () => {
    setOffset(0)
    setAppliedNameFilter(nameFilter)
  }

  const handleStatusFilterChange = (e) => {
    setStatusFilter(e.target.value)
    setOffset(0)
  }

  const handlePrevPage = () => {
    setOffset(Math.max(0, offset - limit))
  }

  const handleNextPage = () => {
    if (offset + limit < total) {
      setOffset(offset + limit)
    }
  }

  const handleSelectTrace = async (trace) => {
    setTraceError(null)
    try {
      const response = await tracingApi.getTrace(trace.id)
      setSelectedTrace(response.data)
    } catch (err) {
      console.error('Failed to load trace details:', err)
      const errorMessage = err.response?.status === 404
        ? 'Trace not found or does not belong to your organization.'
        : err.response?.data?.detail || 'Failed to load trace details.'
      setTraceError(errorMessage)
      setTimeout(() => setTraceError(null), 5000)
    }
  }

  const formatNumber = (num) => {
    if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M'
    if (num >= 1000) return (num / 1000).toFixed(1) + 'K'
    return num?.toString() || '0'
  }

  const statsCards = stats ? [
    { label: 'Total Traces', value: formatNumber(stats.total_traces) },
    { label: 'Traces Today', value: formatNumber(stats.traces_today) },
    { label: 'This Week', value: formatNumber(stats.traces_this_week) },
    { label: 'Errors', value: formatNumber(stats.error_count), type: 'error' },
    { label: 'Avg Latency', value: `${stats.avg_latency_ms?.toFixed(0) || 0}ms` },
  ] : []

  return (
    <div className={`tracing-page ${selectedTrace ? 'with-panel' : ''}`}>
      <div className="tracing-main">
        <motion.div 
          className="tracing-header"
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4 }}
        >
          <div className="tracing-header-content">
            <h2>
              <span className="icon">📊</span>
              Traces & Logs
            </h2>
            <p>Monitor and analyze your application traces</p>
          </div>
        </motion.div>

        {stats && (
          <div className="tracing-stats-grid">
            {statsCards.map((stat, index) => (
              <motion.div
                key={stat.label}
                className={`tracing-stat-card ${stat.type || ''}`}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.3, delay: index * 0.05 }}
              >
                <div className="stat-value">{stat.value}</div>
                <div className="stat-label">{stat.label}</div>
              </motion.div>
            ))}
          </div>
        )}

        <div className="tracing-filters">
          <div className="filter-search-group">
            <SearchIcon size={16} className="search-icon" />
            <input
              type="text"
              className="filter-input"
              placeholder="Search by trace name..."
              value={nameFilter}
              onChange={handleFilterChange}
              onKeyPress={handleFilterKeyPress}
            />
            <button 
              className="search-btn"
              onClick={handleSearchClick}
              title="Search"
            >
              Search
            </button>
          </div>
          <div className="filter-group">
            <FilterIcon size={16} />
            <select 
              className="status-filter"
              value={statusFilter}
              onChange={handleStatusFilterChange}
            >
              <option value="">All Status</option>
              <option value="success">Success</option>
              <option value="error">Error</option>
            </select>
          </div>
          <button 
            className="refresh-btn" 
            onClick={handleRefresh}
            disabled={isRefreshing}
          >
            <RefreshIcon size={16} className={isRefreshing ? 'spinning' : ''} />
            Refresh
          </button>
        </div>

        {error && (
          <div className="tracing-empty">
            <div className="empty-icon">⚠️</div>
            <h4>Error Loading Traces</h4>
            <p>{error}</p>
          </div>
        )}

        {!error && (
          <TraceList
            traces={traces}
            total={total}
            limit={limit}
            offset={offset}
            isLoading={isLoading}
            onSelectTrace={handleSelectTrace}
            onPrevPage={handlePrevPage}
            onNextPage={handleNextPage}
            selectedTraceId={selectedTrace?.id}
          />
        )}
      </div>

      <AnimatePresence>
        {selectedTrace && (
          <TraceDetailPanel
            trace={selectedTrace}
            onClose={() => setSelectedTrace(null)}
          />
        )}
      </AnimatePresence>

      <AnimatePresence>
        {traceError && (
          <motion.div 
            className="trace-error-toast"
            initial={{ opacity: 0, y: 50 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 50 }}
            transition={{ duration: 0.2 }}
          >
            <span className="toast-icon">⚠️</span>
            <span className="toast-message">{traceError}</span>
            <button 
              className="toast-close"
              onClick={() => setTraceError(null)}
            >
              ×
            </button>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

export default TracingPage
