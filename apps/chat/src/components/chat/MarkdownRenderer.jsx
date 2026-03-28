import React, { useState, useCallback } from 'react'
import ReactMarkdown from 'react-markdown'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import remarkGfm from 'remark-gfm'
import remarkMath from 'remark-math'
import rehypeRaw from 'rehype-raw'
import rehypeKatex from 'rehype-katex'
import 'katex/dist/katex.min.css'
import { DiagramRenderer, isMermaidCode } from './DiagramRenderer'
import './VoiceChat.css'

const lightTheme = {
  'code[class*="language-"]': {
    color: '#24292e',
    background: 'none',
    fontFamily: "'SFMono-Regular', 'Menlo', 'Monaco', 'Consolas', monospace",
    fontSize: '13px',
    textAlign: 'left',
    whiteSpace: 'pre',
    wordSpacing: 'normal',
    wordBreak: 'normal',
    wordWrap: 'normal',
    lineHeight: '1.6',
    tabSize: 2,
    hyphens: 'none',
  },
  'pre[class*="language-"]': {
    color: '#24292e',
    background: '#f7f7f8',
    fontFamily: "'SFMono-Regular', 'Menlo', 'Monaco', 'Consolas', monospace",
    fontSize: '13px',
    textAlign: 'left',
    whiteSpace: 'pre',
    wordSpacing: 'normal',
    wordBreak: 'normal',
    wordWrap: 'normal',
    lineHeight: '1.6',
    tabSize: 2,
    hyphens: 'none',
    padding: '16px',
    margin: '0',
    overflow: 'auto',
  },
  comment: { color: '#6a737d' },
  prolog: { color: '#6a737d' },
  doctype: { color: '#6a737d' },
  cdata: { color: '#6a737d' },
  punctuation: { color: '#24292e' },
  property: { color: '#005cc5' },
  tag: { color: '#22863a' },
  boolean: { color: '#005cc5' },
  number: { color: '#005cc5' },
  constant: { color: '#005cc5' },
  symbol: { color: '#005cc5' },
  deleted: { color: '#b31d28', background: '#ffeef0' },
  selector: { color: '#6f42c1' },
  'attr-name': { color: '#6f42c1' },
  string: { color: '#032f62' },
  char: { color: '#032f62' },
  builtin: { color: '#005cc5' },
  inserted: { color: '#22863a', background: '#f0fff4' },
  operator: { color: '#d73a49' },
  entity: { color: '#005cc5', cursor: 'help' },
  url: { color: '#032f62' },
  '.language-css .token.string': { color: '#032f62' },
  '.style .token.string': { color: '#032f62' },
  atrule: { color: '#d73a49' },
  'attr-value': { color: '#032f62' },
  keyword: { color: '#d73a49' },
  function: { color: '#6f42c1' },
  'class-name': { color: '#6f42c1' },
  regex: { color: '#032f62' },
  important: { color: '#d73a49', fontWeight: 'bold' },
  variable: { color: '#e36209' },
}

function CopyButton({ text }) {
  const [copied, setCopied] = useState(false)

  const handleCopy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(text)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch (err) {
      console.error('Failed to copy:', err)
    }
  }, [text])

  return (
    <button 
      className={`code-copy-btn ${copied ? 'copied' : ''}`}
      onClick={handleCopy}
      type="button"
    >
      {copied ? (
        <>
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <polyline points="20 6 9 17 4 12"></polyline>
          </svg>
          Copied!
        </>
      ) : (
        <>
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
            <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
          </svg>
          Copy
        </>
      )}
    </button>
  )
}

function CodeBlock({ language, children }) {
  const codeString = String(children).replace(/\n$/, '')
  
  if (language === 'mermaid' || isMermaidCode(codeString)) {
    return (
      <div className="diagram-wrapper">
        <DiagramRenderer code={codeString} />
      </div>
    )
  }
  
  return (
    <div className="code-block-wrapper">
      <div className="code-block-header">
        <span className="code-block-language">{language || 'code'}</span>
        <CopyButton text={codeString} />
      </div>
      <SyntaxHighlighter
        style={lightTheme}
        language={language || 'text'}
        PreTag="div"
        className="code-block"
        customStyle={{
          margin: 0,
          padding: '16px',
          background: '#f7f7f8',
          borderRadius: 0,
        }}
        codeTagProps={{
          style: {
            fontFamily: "'SFMono-Regular', 'Menlo', 'Monaco', 'Consolas', monospace",
            fontSize: '13px',
            lineHeight: '1.6',
          }
        }}
      >
        {codeString}
      </SyntaxHighlighter>
    </div>
  )
}

export function MarkdownRenderer({ content, className = '' }) {
  return (
    <div className={`markdown-content ${className}`}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm, remarkMath]}
        rehypePlugins={[rehypeRaw, rehypeKatex]}
        components={{
          code({ node, inline, className, children, ...props }) {
            const match = /language-(\w+)/.exec(className || '')
            const language = match ? match[1] : ''
            const codeString = String(children).replace(/\n$/, '')
            
            if (!inline) {
              return <CodeBlock language={language}>{codeString}</CodeBlock>
            }
            
            return (
              <code className="inline-code" {...props}>
                {children}
              </code>
            )
          },
          pre({ children }) {
            if (React.isValidElement(children) && children.props?.className?.includes('code-block-wrapper')) {
              return <>{children}</>
            }
            return <>{children}</>
          },
          p({ children }) {
            return <p className="text-paragraph">{children}</p>
          },
          h1({ children }) {
            return <h1 className="text-header text-header-h1">{children}</h1>
          },
          h2({ children }) {
            return <h2 className="text-header text-header-h2">{children}</h2>
          },
          h3({ children }) {
            return <h3 className="text-header text-header-h3">{children}</h3>
          },
          h4({ children }) {
            return <h4 className="text-header text-header-h4">{children}</h4>
          },
          h5({ children }) {
            return <h5 className="text-header text-header-h5">{children}</h5>
          },
          h6({ children }) {
            return <h6 className="text-header text-header-h6">{children}</h6>
          },
          ul({ children }) {
            return <ul className="text-list text-list-unordered">{children}</ul>
          },
          ol({ children }) {
            return <ol className="text-list text-list-ordered">{children}</ol>
          },
          li({ children }) {
            return <li className="text-list-item">{children}</li>
          },
          blockquote({ children }) {
            return <blockquote className="text-blockquote">{children}</blockquote>
          },
          hr() {
            return <hr className="text-hr" />
          },
          table({ children }) {
            return (
              <div className="table-wrapper-inline">
                <table className="text-table">{children}</table>
              </div>
            )
          },
          thead({ children }) {
            return <thead>{children}</thead>
          },
          tbody({ children }) {
            return <tbody>{children}</tbody>
          },
          tr({ children }) {
            return <tr className="text-table-row">{children}</tr>
          },
          th({ children }) {
            return <th className="text-table-header">{children}</th>
          },
          td({ children }) {
            return <td className="text-table-cell">{children}</td>
          },
          a({ href, children }) {
            return (
              <a href={href} target="_blank" rel="noopener noreferrer" className="text-link">
                {children}
              </a>
            )
          },
          strong({ children }) {
            return <strong className="text-bold">{children}</strong>
          },
          em({ children }) {
            return <em className="text-italic">{children}</em>
          }
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  )
}
