import React, { useState, useEffect } from 'react'
import { billingApi } from '../../services'
import {
  BillingIcon,
  CalendarIcon,
  FileTextIcon,
  DownloadIcon,
  ActivityIcon,
  AgentIcon,
  DatabaseIcon,
  TokenIcon,
  OrganizationIcon,
  WorkspacesIcon,
  TeamsIcon,
  CheckIcon,
} from '../common'
import './Billing.css'

const Billing = ({ organizations = [], workspaces = [], teams = [], currentOrganization = null }) => {
  const [selectedOrg, setSelectedOrg] = useState(currentOrganization)
  const [plans, setPlans] = useState([])
  const [subscription, setSubscription] = useState(null)
  const [usage, setUsage] = useState([])
  const [invoices, setInvoices] = useState([])
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState('overview')

  useEffect(() => {
    loadPlans()
  }, [])

  useEffect(() => {
    if (currentOrganization && !selectedOrg) {
      setSelectedOrg(currentOrganization)
    }
  }, [currentOrganization, selectedOrg])

  useEffect(() => {
    if (selectedOrg) {
      loadBillingData()
    }
  }, [selectedOrg])

  const loadPlans = async () => {
    try {
      const response = await billingApi.getPlans()
      setPlans(response.data)
    } catch (err) {
      console.error('Failed to load plans:', err)
    }
  }

  const loadBillingData = async () => {
    if (!selectedOrg) return
    setLoading(true)
    try {
      const [subRes, usageRes, invoicesRes] = await Promise.all([
        billingApi.getSubscription(selectedOrg.id),
        billingApi.getUsage(selectedOrg.id),
        billingApi.getInvoices(selectedOrg.id),
      ])
      setSubscription(subRes.data)
      setUsage(usageRes.data)
      setInvoices(invoicesRes.data)
    } catch (err) {
      console.error('Failed to load billing data:', err)
    } finally {
      setLoading(false)
    }
  }

  const handlePlanChange = async (planId) => {
    if (!selectedOrg) return
    try {
      await billingApi.updateSubscription(selectedOrg.id, { plan: planId })
      loadBillingData()
    } catch (err) {
      console.error('Failed to update plan:', err)
    }
  }

  const formatCurrency = (cents, currency = 'USD') => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency,
      minimumFractionDigits: 0,
    }).format(cents / 100)
  }

  const formatDate = (dateStr) => {
    return new Date(dateStr).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    })
  }

  const getCurrentPlan = () => {
    if (!subscription) return plans.find(p => p.id === 'free')
    return plans.find(p => p.id === subscription.plan) || plans.find(p => p.id === 'free')
  }

  const getUsageTypeLabel = (type) => {
    const labels = {
      api_calls: 'API Calls',
      agent_runs: 'Agent Executions',
      storage: 'Storage',
      tokens: 'AI Tokens',
    }
    return labels[type] || type
  }

  const getUsageTypeIcon = (type) => {
    const icons = {
      api_calls: <ActivityIcon size={20} />,
      agent_runs: <AgentIcon size={20} />,
      storage: <DatabaseIcon size={20} />,
      tokens: <TokenIcon size={20} />,
    }
    return icons[type] || icons.api_calls
  }

  const currentPlan = getCurrentPlan()

  return (
    <div className="billing-container">
      <div className="billing-header">
        <div className="billing-header-left">
          <h2>Billing & Usage</h2>
          <p>Manage your subscription and monitor usage</p>
        </div>
        {currentOrganization && (
          <div className="org-info" style={{ fontSize: '0.9rem', color: '#6b7280' }}>
            <strong>Organization:</strong> {currentOrganization.name}
          </div>
        )}
      </div>

      <div className="billing-tabs">
        <button 
          className={`billing-tab ${activeTab === 'overview' ? 'active' : ''}`}
          onClick={() => setActiveTab('overview')}
        >
          Overview
        </button>
        <button 
          className={`billing-tab ${activeTab === 'plans' ? 'active' : ''}`}
          onClick={() => setActiveTab('plans')}
        >
          Plans
        </button>
        <button 
          className={`billing-tab ${activeTab === 'usage' ? 'active' : ''}`}
          onClick={() => setActiveTab('usage')}
        >
          Usage
        </button>
        <button 
          className={`billing-tab ${activeTab === 'invoices' ? 'active' : ''}`}
          onClick={() => setActiveTab('invoices')}
        >
          Invoices
        </button>
      </div>

      {loading ? (
        <div className="billing-loading">
          <div className="loading-spinner"></div>
          <span>Loading billing data...</span>
        </div>
      ) : (
        <>
          {activeTab === 'overview' && (
            <div className="billing-overview">
              <div className="overview-grid">
                <div className="overview-card current-plan-card">
                  <div className="card-icon plan-icon">
                    <BillingIcon size={24} />
                  </div>
                  <div className="card-content">
                    <span className="card-label">Current Plan</span>
                    <span className="card-value plan-name">{currentPlan?.name || 'Free'}</span>
                    <span className="card-subtext">
                      {currentPlan?.price === 0 ? 'Free forever' : `${formatCurrency(currentPlan?.price || 0)}/month`}
                    </span>
                  </div>
                  <button className="btn-outline" onClick={() => setActiveTab('plans')}>
                    {currentPlan?.id === 'free' ? 'Upgrade' : 'Change Plan'}
                  </button>
                </div>

                <div className="overview-card billing-period-card">
                  <div className="card-icon period-icon">
                    <CalendarIcon size={24} />
                  </div>
                  <div className="card-content">
                    <span className="card-label">Billing Period</span>
                    <span className="card-value">
                      {subscription ? formatDate(subscription.current_period_start) : 'N/A'}
                    </span>
                    <span className="card-subtext">
                      to {subscription ? formatDate(subscription.current_period_end) : 'N/A'}
                    </span>
                  </div>
                </div>

                <div className="overview-card next-invoice-card">
                  <div className="card-icon invoice-icon">
                    <FileTextIcon size={24} />
                  </div>
                  <div className="card-content">
                    <span className="card-label">Next Invoice</span>
                    <span className="card-value">{formatCurrency(currentPlan?.price || 0)}</span>
                    <span className="card-subtext">
                      Due {subscription ? formatDate(subscription.current_period_end) : 'N/A'}
                    </span>
                  </div>
                </div>

                <div className="overview-card payment-method-card">
                  <div className="card-icon payment-icon">
                    <BillingIcon size={24} />
                  </div>
                  <div className="card-content">
                    <span className="card-label">Payment Method</span>
                    <span className="card-value">•••• 4242</span>
                    <span className="card-subtext">Expires 12/2026</span>
                  </div>
                  <button className="btn-outline">Update</button>
                </div>
              </div>

              <div className="usage-summary-section">
                <h3>Resource Usage</h3>
                <div className="resource-usage-grid">
                  <div className="resource-usage-item">
                    <div className="resource-icon" style={{ background: 'rgba(99, 102, 241, 0.1)', color: '#6366f1' }}>
                      <OrganizationIcon size={20} />
                    </div>
                    <div className="resource-info">
                      <span className="resource-label">Organizations</span>
                      <span className="resource-count">{organizations.length} / {currentPlan?.limits?.organizations === -1 ? '∞' : currentPlan?.limits?.organizations || 1}</span>
                    </div>
                    <div className="resource-bar">
                      <div 
                        className="resource-fill"
                        style={{ 
                          width: currentPlan?.limits?.organizations === -1 ? '10%' : `${Math.min((organizations.length / (currentPlan?.limits?.organizations || 1)) * 100, 100)}%`,
                          background: organizations.length >= (currentPlan?.limits?.organizations || 1) && currentPlan?.limits?.organizations !== -1 ? '#ef4444' : '#6366f1'
                        }}
                      />
                    </div>
                  </div>
                  <div className="resource-usage-item">
                    <div className="resource-icon" style={{ background: 'rgba(16, 185, 129, 0.1)', color: '#10b981' }}>
                      <WorkspacesIcon size={20} />
                    </div>
                    <div className="resource-info">
                      <span className="resource-label">Workspaces</span>
                      <span className="resource-count">{workspaces.length} / {currentPlan?.limits?.workspaces === -1 ? '∞' : currentPlan?.limits?.workspaces || 2}</span>
                    </div>
                    <div className="resource-bar">
                      <div 
                        className="resource-fill"
                        style={{ 
                          width: currentPlan?.limits?.workspaces === -1 ? '10%' : `${Math.min((workspaces.length / (currentPlan?.limits?.workspaces || 2)) * 100, 100)}%`,
                          background: workspaces.length >= (currentPlan?.limits?.workspaces || 2) && currentPlan?.limits?.workspaces !== -1 ? '#ef4444' : '#10b981'
                        }}
                      />
                    </div>
                  </div>
                  <div className="resource-usage-item">
                    <div className="resource-icon" style={{ background: 'rgba(139, 92, 246, 0.1)', color: '#8b5cf6' }}>
                      <TeamsIcon size={20} />
                    </div>
                    <div className="resource-info">
                      <span className="resource-label">Teams</span>
                      <span className="resource-count">{teams.length} / {currentPlan?.limits?.teams === -1 ? '∞' : currentPlan?.limits?.teams || 1}</span>
                    </div>
                    <div className="resource-bar">
                      <div 
                        className="resource-fill"
                        style={{ 
                          width: currentPlan?.limits?.teams === -1 ? '10%' : `${Math.min((teams.length / (currentPlan?.limits?.teams || 1)) * 100, 100)}%`,
                          background: teams.length >= (currentPlan?.limits?.teams || 1) && currentPlan?.limits?.teams !== -1 ? '#ef4444' : '#8b5cf6'
                        }}
                      />
                    </div>
                  </div>
                </div>
              </div>

              <div className="usage-summary-section">
                <h3>API Usage</h3>
                <div className="usage-bars">
                  {usage.map(u => (
                    <div key={u.usage_type} className="usage-bar-item">
                      <div className="usage-bar-header">
                        <div className="usage-bar-label">
                          {getUsageTypeIcon(u.usage_type)}
                          <span>{getUsageTypeLabel(u.usage_type)}</span>
                        </div>
                        <span className="usage-bar-value">
                          {u.total_quantity.toLocaleString()} 
                          {u.percentage_of_limit > 0 && ` / ${Math.round(u.total_quantity / (u.percentage_of_limit / 100)).toLocaleString()}`}
                        </span>
                      </div>
                      <div className="usage-bar-track">
                        <div 
                          className={`usage-bar-fill ${u.percentage_of_limit > 80 ? 'warning' : ''} ${u.percentage_of_limit >= 100 ? 'danger' : ''}`}
                          style={{ width: `${Math.min(u.percentage_of_limit, 100)}%` }}
                        />
                      </div>
                      <span className="usage-bar-percentage">{u.percentage_of_limit.toFixed(1)}% used</span>
                    </div>
                  ))}
                  {usage.length === 0 && (
                    <div className="empty-usage">
                      <p>No API usage data yet. Usage will appear here as you use JarvisX services.</p>
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}

          {activeTab === 'plans' && (
            <div className="billing-plans">
              <div className="plans-grid">
                {plans.map(plan => (
                  <div 
                    key={plan.id} 
                    className={`plan-card ${plan.is_popular ? 'popular' : ''} ${subscription?.plan === plan.id ? 'current' : ''}`}
                  >
                    {plan.is_popular && <div className="popular-badge">Most Popular</div>}
                    {subscription?.plan === plan.id && <div className="current-badge">Current Plan</div>}
                    <h3 className="plan-name">{plan.name}</h3>
                    <div className="plan-price">
                      {plan.price === 0 ? (
                        <>
                          <span className="price-amount">Free</span>
                          <span className="price-period">forever</span>
                        </>
                      ) : plan.id === 'enterprise' ? (
                        <>
                          <span className="price-amount">Custom</span>
                          <span className="price-period">contact us</span>
                        </>
                      ) : (
                        <>
                          <span className="price-amount">{formatCurrency(plan.price)}</span>
                          <span className="price-period">/{plan.interval}</span>
                        </>
                      )}
                    </div>
                    <ul className="plan-features">
                      {plan.features.map((feature, idx) => (
                        <li key={idx}>
                          <CheckIcon size={16} />
                          {feature}
                        </li>
                      ))}
                    </ul>
                    <button 
                      className={`plan-btn ${subscription?.plan === plan.id ? 'btn-current' : plan.is_popular ? 'btn-primary' : 'btn-secondary'}`}
                      onClick={() => plan.id !== 'enterprise' && handlePlanChange(plan.id)}
                      disabled={subscription?.plan === plan.id}
                    >
                      {subscription?.plan === plan.id ? 'Current Plan' : plan.id === 'enterprise' ? 'Contact Sales' : 'Select Plan'}
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}

          {activeTab === 'usage' && (
            <div className="billing-usage">
              <div className="usage-detail-grid">
                {usage.map(u => (
                  <div key={u.usage_type} className="usage-detail-card">
                    <div className="usage-detail-header">
                      <div className="usage-detail-icon">{getUsageTypeIcon(u.usage_type)}</div>
                      <div className="usage-detail-info">
                        <h4>{getUsageTypeLabel(u.usage_type)}</h4>
                        <span className="usage-period">Current billing period</span>
                      </div>
                    </div>
                    <div className="usage-detail-stats">
                      <div className="usage-stat">
                        <span className="stat-value">{u.total_quantity.toLocaleString()}</span>
                        <span className="stat-label">Used</span>
                      </div>
                      <div className="usage-stat">
                        <span className="stat-value">{u.percentage_of_limit.toFixed(1)}%</span>
                        <span className="stat-label">Of Limit</span>
                      </div>
                      <div className="usage-stat">
                        <span className="stat-value">{formatCurrency(u.total_cost)}</span>
                        <span className="stat-label">Cost</span>
                      </div>
                    </div>
                    <div className="usage-detail-bar">
                      <div 
                        className={`usage-detail-fill ${u.percentage_of_limit > 80 ? 'warning' : ''} ${u.percentage_of_limit >= 100 ? 'danger' : ''}`}
                        style={{ width: `${Math.min(u.percentage_of_limit, 100)}%` }}
                      />
                    </div>
                  </div>
                ))}
                {usage.length === 0 && (
                  <div className="empty-usage-detail">
                    <ActivityIcon size={48} />
                    <h4>No Usage Data</h4>
                    <p>Usage metrics will appear here once you start using JarvisX services.</p>
                  </div>
                )}
              </div>
            </div>
          )}

          {activeTab === 'invoices' && (
            <div className="billing-invoices">
              {invoices.length > 0 ? (
                <table className="invoices-table">
                  <thead>
                    <tr>
                      <th>Invoice</th>
                      <th>Period</th>
                      <th>Amount</th>
                      <th>Status</th>
                      <th>Date</th>
                      <th></th>
                    </tr>
                  </thead>
                  <tbody>
                    {invoices.map(inv => (
                      <tr key={inv.id}>
                        <td className="invoice-number">{inv.invoice_number}</td>
                        <td>{formatDate(inv.period_start)} - {formatDate(inv.period_end)}</td>
                        <td className="invoice-amount">{formatCurrency(inv.total, inv.currency)}</td>
                        <td>
                          <span className={`invoice-status ${inv.status}`}>
                            {inv.status.charAt(0).toUpperCase() + inv.status.slice(1)}
                          </span>
                        </td>
                        <td>{formatDate(inv.created_at)}</td>
                        <td>
                          <button className="btn-icon-sm" title="Download">
                            <DownloadIcon size={16} />
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : (
                <div className="empty-invoices">
                  <FileTextIcon size={48} />
                  <h4>No Invoices Yet</h4>
                  <p>Your invoices will appear here once you have billing activity.</p>
                </div>
              )}
            </div>
          )}
        </>
      )}
    </div>
  )
}

export default Billing
