import React from 'react'
import {
  BarChart,
  Bar,
  LineChart,
  Line,
  PieChart,
  Pie,
  AreaChart,
  Area,
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  Cell
} from 'recharts'
import './ChartRenderer.css'

const CHART_COLORS = [
  '#10a37f',
  '#5436DA',
  '#FF6B6B',
  '#4ECDC4',
  '#FFE66D',
  '#95E1D3',
  '#F38181',
  '#AA96DA',
  '#FCBAD3',
  '#A8D8EA'
]

function CustomTooltip({ active, payload, label }) {
  if (!active || !payload || !payload.length) return null

  return (
    <div className="chart-tooltip">
      {label && <p className="chart-tooltip-label">{label}</p>}
      {payload.map((entry, index) => (
        <p key={index} className="chart-tooltip-value" style={{ color: entry.color }}>
          {entry.name}: {typeof entry.value === 'number' ? entry.value.toLocaleString() : entry.value}
        </p>
      ))}
    </div>
  )
}

function BarChartComponent({ data, xKey, yKeys, colors }) {
  const keys = Array.isArray(yKeys) ? yKeys : [yKeys || 'value']
  
  return (
    <ResponsiveContainer width="100%" height={300}>
      <BarChart data={data} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#e0e0e0" />
        <XAxis dataKey={xKey || 'name'} tick={{ fill: '#6e6e80' }} />
        <YAxis tick={{ fill: '#6e6e80' }} />
        <Tooltip content={<CustomTooltip />} />
        <Legend />
        {keys.map((key, index) => (
          <Bar
            key={key}
            dataKey={key}
            fill={colors?.[index] || CHART_COLORS[index % CHART_COLORS.length]}
            radius={[4, 4, 0, 0]}
          />
        ))}
      </BarChart>
    </ResponsiveContainer>
  )
}

function LineChartComponent({ data, xKey, yKeys, colors }) {
  const keys = Array.isArray(yKeys) ? yKeys : [yKeys || 'value']
  
  return (
    <ResponsiveContainer width="100%" height={300}>
      <LineChart data={data} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#e0e0e0" />
        <XAxis dataKey={xKey || 'name'} tick={{ fill: '#6e6e80' }} />
        <YAxis tick={{ fill: '#6e6e80' }} />
        <Tooltip content={<CustomTooltip />} />
        <Legend />
        {keys.map((key, index) => (
          <Line
            key={key}
            type="monotone"
            dataKey={key}
            stroke={colors?.[index] || CHART_COLORS[index % CHART_COLORS.length]}
            strokeWidth={2}
            dot={{ fill: colors?.[index] || CHART_COLORS[index % CHART_COLORS.length], strokeWidth: 2 }}
            activeDot={{ r: 6 }}
          />
        ))}
      </LineChart>
    </ResponsiveContainer>
  )
}

function PieChartComponent({ data, dataKey, nameKey, colors }) {
  return (
    <ResponsiveContainer width="100%" height={300}>
      <PieChart>
        <Pie
          data={data}
          dataKey={dataKey || 'value'}
          nameKey={nameKey || 'name'}
          cx="50%"
          cy="50%"
          outerRadius={100}
          label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}
          labelLine={{ stroke: '#6e6e80' }}
        >
          {data.map((entry, index) => (
            <Cell
              key={`cell-${index}`}
              fill={colors?.[index] || CHART_COLORS[index % CHART_COLORS.length]}
            />
          ))}
        </Pie>
        <Tooltip content={<CustomTooltip />} />
        <Legend />
      </PieChart>
    </ResponsiveContainer>
  )
}

function AreaChartComponent({ data, xKey, yKeys, colors }) {
  const keys = Array.isArray(yKeys) ? yKeys : [yKeys || 'value']
  
  return (
    <ResponsiveContainer width="100%" height={300}>
      <AreaChart data={data} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#e0e0e0" />
        <XAxis dataKey={xKey || 'name'} tick={{ fill: '#6e6e80' }} />
        <YAxis tick={{ fill: '#6e6e80' }} />
        <Tooltip content={<CustomTooltip />} />
        <Legend />
        {keys.map((key, index) => (
          <Area
            key={key}
            type="monotone"
            dataKey={key}
            stroke={colors?.[index] || CHART_COLORS[index % CHART_COLORS.length]}
            fill={colors?.[index] || CHART_COLORS[index % CHART_COLORS.length]}
            fillOpacity={0.3}
            strokeWidth={2}
          />
        ))}
      </AreaChart>
    </ResponsiveContainer>
  )
}

function ScatterChartComponent({ data, xKey, yKey, colors }) {
  return (
    <ResponsiveContainer width="100%" height={300}>
      <ScatterChart margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#e0e0e0" />
        <XAxis dataKey={xKey || 'x'} name={xKey || 'x'} tick={{ fill: '#6e6e80' }} />
        <YAxis dataKey={yKey || 'y'} name={yKey || 'y'} tick={{ fill: '#6e6e80' }} />
        <Tooltip content={<CustomTooltip />} cursor={{ strokeDasharray: '3 3' }} />
        <Legend />
        <Scatter
          name="Data"
          data={data}
          fill={colors?.[0] || CHART_COLORS[0]}
        />
      </ScatterChart>
    </ResponsiveContainer>
  )
}

export function ChartRenderer({ config }) {
  if (!config || !config.data) {
    return <div className="chart-error">No chart data provided</div>
  }

  const { chartType, title, data, xKey, yKey, yKeys, nameKey, dataKey, colors } = config

  const renderChart = () => {
    switch (chartType?.toLowerCase()) {
      case 'bar':
        return <BarChartComponent data={data} xKey={xKey} yKeys={yKeys || yKey} colors={colors} />
      case 'line':
        return <LineChartComponent data={data} xKey={xKey} yKeys={yKeys || yKey} colors={colors} />
      case 'pie':
        return <PieChartComponent data={data} dataKey={dataKey || yKey} nameKey={nameKey || xKey} colors={colors} />
      case 'area':
        return <AreaChartComponent data={data} xKey={xKey} yKeys={yKeys || yKey} colors={colors} />
      case 'scatter':
        return <ScatterChartComponent data={data} xKey={xKey} yKey={yKey} colors={colors} />
      default:
        return <BarChartComponent data={data} xKey={xKey} yKeys={yKeys || yKey} colors={colors} />
    }
  }

  return (
    <div className="chart-container">
      {title && <h3 className="chart-title">{title}</h3>}
      {renderChart()}
    </div>
  )
}
