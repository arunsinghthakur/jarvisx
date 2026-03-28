import React, { useEffect, useRef, useState } from 'react'
import mermaid from 'mermaid'

mermaid.initialize({
  startOnLoad: false,
  theme: 'default',
  securityLevel: 'loose',
  fontFamily: '"Inter", -apple-system, BlinkMacSystemFont, sans-serif',
  themeVariables: {
    primaryColor: '#10a37f',
    primaryTextColor: '#202123',
    primaryBorderColor: '#10a37f',
    lineColor: '#6e6e80',
    secondaryColor: '#f7f7f8',
    tertiaryColor: '#ececf1',
    background: '#ffffff',
    mainBkg: '#ffffff',
    nodeBorder: '#e0e0e0',
    clusterBkg: '#f7f7f8',
    clusterBorder: '#e0e0e0',
    titleColor: '#202123',
    edgeLabelBackground: '#ffffff',
    actorBorder: '#10a37f',
    actorBkg: '#f7f7f8',
    actorTextColor: '#202123',
    actorLineColor: '#6e6e80',
    signalColor: '#202123',
    signalTextColor: '#202123',
    labelBoxBkgColor: '#f7f7f8',
    labelBoxBorderColor: '#e0e0e0',
    labelTextColor: '#202123',
    loopTextColor: '#202123',
    noteBorderColor: '#e0e0e0',
    noteBkgColor: '#fffde7',
    noteTextColor: '#202123',
    activationBorderColor: '#10a37f',
    activationBkgColor: '#e6f3f0',
    sequenceNumberColor: '#ffffff',
  },
  flowchart: {
    htmlLabels: true,
    curve: 'basis',
    padding: 15,
  },
  sequence: {
    diagramMarginX: 50,
    diagramMarginY: 10,
    actorMargin: 50,
    width: 150,
    height: 65,
    boxMargin: 10,
    boxTextMargin: 5,
    noteMargin: 10,
    messageMargin: 35,
    mirrorActors: true,
    bottomMarginAdj: 1,
    useMaxWidth: true,
  },
})

let diagramCounter = 0

export function DiagramRenderer({ code, className = '' }) {
  const containerRef = useRef(null)
  const [error, setError] = useState(null)
  const [svg, setSvg] = useState('')
  const idRef = useRef(`mermaid-${Date.now()}-${++diagramCounter}`)

  useEffect(() => {
    if (!code || !containerRef.current) return

    const renderDiagram = async () => {
      try {
        setError(null)
        const cleanCode = code.trim()
        
        const { svg: renderedSvg } = await mermaid.render(idRef.current, cleanCode)
        setSvg(renderedSvg)
      } catch (err) {
        console.error('Mermaid render error:', err)
        setError(err.message || 'Failed to render diagram')
        setSvg('')
      }
    }

    renderDiagram()
  }, [code])

  if (error) {
    return (
      <div className={`diagram-error ${className}`}>
        <div className="diagram-error-header">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="12" cy="12" r="10" />
            <line x1="12" y1="8" x2="12" y2="12" />
            <line x1="12" y1="16" x2="12.01" y2="16" />
          </svg>
          Diagram Error
        </div>
        <pre className="diagram-error-message">{error}</pre>
        <details className="diagram-error-source">
          <summary>Source Code</summary>
          <pre>{code}</pre>
        </details>
      </div>
    )
  }

  return (
    <div
      ref={containerRef}
      className={`diagram-container ${className}`}
      dangerouslySetInnerHTML={{ __html: svg }}
    />
  )
}

export function isMermaidCode(code) {
  if (!code || typeof code !== 'string') return false
  const trimmed = code.trim().toLowerCase()
  const mermaidKeywords = [
    'graph ',
    'graph\n',
    'flowchart ',
    'flowchart\n',
    'sequencediagram',
    'sequence diagram',
    'classDiagram',
    'class diagram',
    'statediagram',
    'state diagram',
    'erdiagram',
    'er diagram',
    'journey',
    'gantt',
    'pie',
    'gitgraph',
    'mindmap',
    'timeline',
    'quadrantchart',
    'sankey',
    'xychart',
  ]
  return mermaidKeywords.some(keyword => trimmed.startsWith(keyword.toLowerCase()))
}
