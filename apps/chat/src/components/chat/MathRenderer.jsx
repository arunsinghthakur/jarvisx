import React, { useEffect, useRef } from 'react'
import katex from 'katex'
import 'katex/dist/katex.min.css'

export function MathRenderer({ math, display = false, className = '' }) {
  const containerRef = useRef(null)

  useEffect(() => {
    if (containerRef.current && math) {
      try {
        katex.render(math, containerRef.current, {
          displayMode: display,
          throwOnError: false,
          errorColor: '#cc3333',
          trust: true,
          strict: false,
          macros: {
            '\\R': '\\mathbb{R}',
            '\\N': '\\mathbb{N}',
            '\\Z': '\\mathbb{Z}',
            '\\Q': '\\mathbb{Q}',
            '\\C': '\\mathbb{C}',
          }
        })
      } catch (error) {
        console.error('KaTeX render error:', error)
        containerRef.current.textContent = math
      }
    }
  }, [math, display])

  if (!math) return null

  return (
    <span
      ref={containerRef}
      className={`math-renderer ${display ? 'math-display' : 'math-inline'} ${className}`}
    />
  )
}

export function InlineMath({ math }) {
  return <MathRenderer math={math} display={false} />
}

export function BlockMath({ math }) {
  return (
    <div className="math-block-container">
      <MathRenderer math={math} display={true} />
    </div>
  )
}

export function parseMathContent(text) {
  if (!text || typeof text !== 'string') return [{ type: 'text', content: text || '' }]

  const parts = []
  let lastIndex = 0
  
  const blockMathRegex = /\$\$([\s\S]*?)\$\$/g
  const inlineMathRegex = /\$([^\$\n]+?)\$/g

  const matches = []
  
  let match
  while ((match = blockMathRegex.exec(text)) !== null) {
    matches.push({
      type: 'block',
      content: match[1].trim(),
      start: match.index,
      end: match.index + match[0].length
    })
  }
  
  while ((match = inlineMathRegex.exec(text)) !== null) {
    const isInsideBlock = matches.some(
      m => match.index >= m.start && match.index < m.end
    )
    if (!isInsideBlock) {
      matches.push({
        type: 'inline',
        content: match[1].trim(),
        start: match.index,
        end: match.index + match[0].length
      })
    }
  }
  
  matches.sort((a, b) => a.start - b.start)
  
  for (const m of matches) {
    if (m.start > lastIndex) {
      parts.push({ type: 'text', content: text.slice(lastIndex, m.start) })
    }
    parts.push({ type: m.type === 'block' ? 'blockMath' : 'inlineMath', content: m.content })
    lastIndex = m.end
  }
  
  if (lastIndex < text.length) {
    parts.push({ type: 'text', content: text.slice(lastIndex) })
  }
  
  return parts.length > 0 ? parts : [{ type: 'text', content: text }]
}
