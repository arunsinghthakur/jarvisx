import React, { useState, useEffect, useCallback } from 'react'
import { motion } from 'framer-motion'
import { platformApi } from '../../services'
import './Platform.css'

const PlatformBilling = () => {
  const [billingData, setBillingData] = useState(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState(null)

  const loadData = useCallback(async () => {
    setIsLoading(true)
    setError(null)
    try {
      const response = await platformApi.getPlatformBilling()
      setBillingData(response.data)
    } catch (err) {
      console.error('Failed to load platform billing data:', err)
      setError(err.response?.data?.detail || 'Failed to load platform billing data')
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    loadData()
  }, [loadData])

  const formatCurrency = (cents, currency = 'USD') => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency,
      minimumFractionDigits: 0,
    }).format(cents / 100)
  }

  const formatDate = (dateStr) => {
    if (!dateStr) return 'N/A'
    return new Date(dateStr).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    })
  }

  if (error) {
    return (
      <div className="platform-dashboard">
        <div className="platform-error">
          <h2>Access Denied</h2>
          <p>{error}</p>
        </div>
      </div>
    )
  }

  const summary = billingData?.summary || {}
  const subscriptions = billingData?.subscriptions || []
  const planDistribution = billingData?.plan_distribution || []

  return (
    <div className="platform-dashboard">
      <motion.div 
        className="platform-header"
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
      >
        <div className="platform-title">
          <span className="platform-icon">💰</span>
          <h2>Platform Billing</h2>
        </div>
        <p>Aggregate billing and subscription metrics across all tenants</p>
      </motion.div>

      {isLoading ? (
        <div className="platform-loading">
          <div className="loading-spinner" />
          <p>Loading billing data...</p>
        </div>
      ) : (
        <>
          <div className="platform-stats-grid">
            <motion.div
              className="platform-stat-card emerald"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3, delay: 0 }}
            >
              <div className="stat-icon">💵</div>
              <div className="stat-content">
                <div className="stat-value">{formatCurrency(summary.total_mrr || 0)}</div>
                <div className="stat-label">Monthly Recurring Revenue</div>
                <div className="stat-subtext">across all tenants</div>
              </div>
            </motion.div>

            <motion.div
              className="platform-stat-card blue"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3, delay: 0.05 }}
            >
              <div className="stat-icon">📊</div>
              <div className="stat-content">
                <div className="stat-value">{formatCurrency(summary.revenue_30d || 0)}</div>
                <div className="stat-label">Revenue (30 days)</div>
                <div className="stat-subtext">total collected</div>
              </div>
            </motion.div>

            <motion.div
              className="platform-stat-card indigo"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3, delay: 0.1 }}
            >
              <div className="stat-icon">🏢</div>
              <div className="stat-content">
                <div className="stat-value">{summary.total_subscriptions || 0}</div>
                <div className="stat-label">Total Subscriptions</div>
                <div className="stat-subtext">{summary.active_subscriptions || 0} active</div>
              </div>
            </motion.div>

            <motion.div
              className="platform-stat-card amber"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3, delay: 0.15 }}
            >
              <div className="stat-icon">⚠️</div>
              <div className="stat-content">
                <div className="stat-value">{summary.past_due_count || 0}</div>
                <div className="stat-label">Past Due</div>
                <div className="stat-subtext">{formatCurrency(summary.past_due_amount || 0)} outstanding</div>
              </div>
            </motion.div>
          </div>

          <div className="platform-row">
            <motion.div
              className="platform-card"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.4, delay: 0.2 }}
            >
              <div className="card-header">
                <h3>Subscription Distribution</h3>
              </div>
              <div className="card-content">
                <div className="plan-distribution">
                  {planDistribution.length > 0 ? (
                    planDistribution.map((plan, idx) => (
                      <div key={plan.plan} className="plan-dist-item">
                        <div className="plan-dist-info">
                          <span className={`plan-badge ${plan.plan}`}>{plan.plan}</span>
                          <span className="plan-count">{plan.count} organizations</span>
                        </div>
                        <div className="plan-dist-bar">
                          <div 
                            className={`plan-dist-fill ${plan.plan}`}
                            style={{ 
                              width: `${(plan.count / (summary.total_subscriptions || 1)) * 100}%` 
                            }}
                          />
                        </div>
                        <span className="plan-mrr">{formatCurrency(plan.total_mrr || 0)}/mo</span>
                      </div>
                    ))
                  ) : (
                    <p className="no-data">No subscription data available</p>
                  )}
                </div>
              </div>
            </motion.div>
          </div>

          <div className="platform-row">
            <motion.div
              className="platform-card organizations-card"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.4, delay: 0.3 }}
            >
              <div className="card-header">
                <h3>Organization Subscriptions</h3>
              </div>
              <div className="card-content">
                <table className="organizations-table">
                  <thead>
                    <tr>
                      <th>Organization</th>
                      <th>Plan</th>
                      <th>Status</th>
                      <th>MRR</th>
                      <th>Next Billing</th>
                    </tr>
                  </thead>
                  <tbody>
                    {subscriptions.length > 0 ? (
                      subscriptions.map((sub) => (
                        <tr key={sub.organization_id}>
                          <td>
                            <div className="org-name">{sub.organization_name}</div>
                          </td>
                          <td>
                            <span className={`plan-badge ${sub.plan}`}>
                              {sub.plan}
                            </span>
                          </td>
                          <td>
                            <span className={`status-badge ${sub.status}`}>
                              {sub.status}
                            </span>
                          </td>
                          <td>{formatCurrency(sub.mrr || 0)}</td>
                          <td>{formatDate(sub.next_billing_date)}</td>
                        </tr>
                      ))
                    ) : (
                      <tr>
                        <td colSpan="5" style={{ textAlign: 'center', padding: '2rem', color: '#6b7280' }}>
                          No subscription data available
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </motion.div>
          </div>
        </>
      )}
    </div>
  )
}

export default PlatformBilling
