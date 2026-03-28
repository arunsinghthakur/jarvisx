const RICH_CONTENT_TYPES = ['chart', 'table', 'file', 'html', 'json', 'code', 'text']

export function parseMessageContent(content) {
  if (!content || typeof content !== 'string') {
    return { type: 'text', content: content || '' }
  }

  const trimmed = content.trim()
  
  if (trimmed.startsWith('{') && trimmed.endsWith('}')) {
    const richContent = tryParseRichContent(trimmed)
    if (richContent) return richContent
  }

  const jsonFromCodeBlock = extractJsonFromCodeBlock(trimmed)
  if (jsonFromCodeBlock) {
    const richContent = tryParseRichContent(jsonFromCodeBlock)
    if (richContent) return richContent
  }

  const embeddedJson = extractEmbeddedJson(trimmed)
  if (embeddedJson) {
    const richContent = tryParseRichContent(embeddedJson)
    if (richContent) return richContent
  }

  return { type: 'text', content: content }
}

function tryParseRichContent(jsonString) {
  try {
    const parsed = JSON.parse(jsonString)
    
    if (parsed.type && RICH_CONTENT_TYPES.includes(parsed.type)) {
      return {
        type: parsed.type,
        content: parsed.content,
        metadata: parsed.metadata || {},
        language: parsed.language || null,
        filename: parsed.filename || null
      }
    }
    
    if (isChartData(parsed)) {
      return {
        type: 'chart',
        content: parsed,
        metadata: {}
      }
    }
    
    if (isTableData(parsed)) {
      return {
        type: 'table',
        content: parsed,
        metadata: {}
      }
    }
    
    if (isFileData(parsed)) {
      return {
        type: 'file',
        content: parsed,
        metadata: {}
      }
    }
  } catch (e) {
  }
  return null
}

function extractJsonFromCodeBlock(content) {
  const jsonBlockMatch = content.match(/```(?:json)?\s*\n?([\s\S]*?)\n?```/)
  if (jsonBlockMatch) {
    const jsonContent = jsonBlockMatch[1].trim()
    if (jsonContent.startsWith('{') && jsonContent.endsWith('}')) {
      return jsonContent
    }
  }
  return null
}

function extractEmbeddedJson(content) {
  const keywordIndex = content.search(/"(?:chartType|columns|filename)"/)
  if (keywordIndex === -1) return null

  let startIndex = content.lastIndexOf('{', keywordIndex)
  while (startIndex >= 0) {
    let depth = 0
    let inString = false
    let escape = false
    for (let i = startIndex; i < content.length; i++) {
      const ch = content[i]
      if (escape) { escape = false; continue }
      if (ch === '\\') { escape = true; continue }
      if (ch === '"' && !escape) { inString = !inString; continue }
      if (inString) continue
      if (ch === '{' || ch === '[') depth++
      else if (ch === '}' || ch === ']') depth--
      if (depth === 0) {
        const candidate = content.substring(startIndex, i + 1)
        try {
          JSON.parse(candidate)
          return candidate
        } catch (e) {
          break
        }
      }
    }
    startIndex = content.lastIndexOf('{', startIndex - 1)
  }
  return null
}

export function isChartData(data) {
  if (!data || typeof data !== 'object') return false
  const hasChartType = typeof data.chartType === 'string'
  const hasData = Array.isArray(data.data)
  return hasChartType && hasData
}

export function isTableData(data) {
  if (!data || typeof data !== 'object') return false
  const hasColumns = Array.isArray(data.columns)
  const hasRows = Array.isArray(data.rows)
  return hasColumns && hasRows
}

export function isFileData(data) {
  if (!data || typeof data !== 'object') return false
  const hasFilename = typeof data.filename === 'string'
  const hasData = typeof data.data === 'string'
  return hasFilename && hasData
}

export function validateChartConfig(config) {
  if (!config) return { valid: false, error: 'No config provided' }
  if (!config.chartType) return { valid: false, error: 'Missing chartType' }
  if (!Array.isArray(config.data)) return { valid: false, error: 'Missing or invalid data array' }
  if (config.data.length === 0) return { valid: false, error: 'Empty data array' }
  return { valid: true }
}

export function validateTableConfig(config) {
  if (!config) return { valid: false, error: 'No config provided' }
  if (!Array.isArray(config.columns)) return { valid: false, error: 'Missing columns array' }
  if (!Array.isArray(config.rows)) return { valid: false, error: 'Missing rows array' }
  return { valid: true }
}

export function validateFileConfig(config) {
  if (!config) return { valid: false, error: 'No config provided' }
  if (!config.filename) return { valid: false, error: 'Missing filename' }
  return { valid: true }
}

export function extractTextFromHtml(html) {
  if (!html) return ''
  
  const div = document.createElement('div')
  div.innerHTML = html
  return div.textContent || div.innerText || ''
}

export function isCodeContent(content) {
  if (!content || typeof content !== 'string') {
    return false
  }

  const trimmed = content.trim()
  
  if (trimmed.startsWith('{') && trimmed.endsWith('}')) {
    try {
      const parsed = JSON.parse(trimmed)
      if (parsed.type === 'code') {
        return true
      }
    } catch (e) {
    }
  }
  
  if (trimmed.startsWith('```')) {
    const codeBlockStart = trimmed.match(/^```\w*\s*\n/)
    if (codeBlockStart) {
      return true
    }
    if (trimmed.length > 20 && trimmed.includes('\n')) {
      return true
    }
  }
  
  const codeBlockMatch = trimmed.match(/^```[\s\S]*?```$/s)
  if (codeBlockMatch) {
    const codeBlockLength = codeBlockMatch[0].length
    if (codeBlockLength >= trimmed.length * 0.5) {
      return true
    }
  }
  
  const codeBlockMatches = trimmed.match(/```[\s\S]*?```/gs)
  if (codeBlockMatches) {
    const totalCodeLength = codeBlockMatches.reduce((sum, match) => sum + match.length, 0)
    if (totalCodeLength >= trimmed.length * 0.5) {
      return true
    }
  }
  
  const incompleteCodeBlock = trimmed.match(/```[\s\S]+/s)
  if (incompleteCodeBlock) {
    const codeContent = incompleteCodeBlock[0]
    if (codeContent.length > 50 && !codeContent.includes('```', 3)) {
      const textBeforeCode = trimmed.substring(0, trimmed.indexOf('```'))
      if (textBeforeCode.length < codeContent.length * 0.3) {
        return true
      }
    }
  }
  
  return false
}

