import React, { useState, useEffect, useRef, useMemo, memo, useCallback } from 'react'
import { useChat } from 'ai/react'
import { 
  textToSpeech,
  parseMessageContent, 
  extractTextFromHtml, 
  isCodeContent,
  extractUrlInfo,
  fetchWorkspaceConfig, 
  fetchChatbotConfig,
  getSpeechAgentUrl,
  createConversation,
  getConversation,
  addMessagesBulk,
  URL_TYPE,
} from '../../services'
import { MarkdownRenderer } from './MarkdownRenderer'
import { ChartRenderer } from './ChartRenderer'
import { TableRenderer } from './TableRenderer'
import { FileRenderer } from './FileRenderer'
import { ConversationSidebar } from './ConversationSidebar'
import { FileUpload, filesToBase64, formatFileSize, getFileTypeInfo } from './FileUpload'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { oneLight } from 'react-syntax-highlighter/dist/esm/styles/prism'
import { getAuthToken } from '../../lib/auth'
import {
  MicrophoneIcon,
  StopIcon,
  SendIcon,
  VolumeIcon,
  VolumeOffIcon,
  AttachmentIcon,
} from '../common'
import { useVoiceWebSocket } from '../../hooks/useVoiceWebSocket'
import './VoiceChat.css'
import './ChartRenderer.css'
import './TableRenderer.css'
import './FileRenderer.css'
import './ConversationSidebar.css'

const MessageContent = memo(function MessageContent({ message }) {
  const [showHtmlPreview, setShowHtmlPreview] = useState(false)
  
  const parsedContent = useMemo(() => parseMessageContent(message.content), [message.content])

  if (parsedContent.type === 'chart') {
    return (
      <div className="message-text">
        <ChartRenderer config={parsedContent.content} />
      </div>
    )
  }

  if (parsedContent.type === 'table') {
    return (
      <div className="message-text">
        <TableRenderer config={parsedContent.content} />
      </div>
    )
  }

  if (parsedContent.type === 'file') {
    return (
      <div className="message-text">
        <FileRenderer config={parsedContent.content} />
      </div>
    )
  }

  if (parsedContent.type === 'html') {
    return (
      <>
        <div className="message-text">
          <MarkdownRenderer content={extractTextFromHtml(parsedContent.content)} />
        </div>
        <div className="html-preview-container">
          <button
            className="html-preview-toggle"
            onClick={() => setShowHtmlPreview(!showHtmlPreview)}
            aria-expanded={showHtmlPreview}
          >
            {showHtmlPreview ? 'Hide Preview' : 'Show HTML Preview'}
          </button>
          {showHtmlPreview && (
            <div className="html-preview-wrapper">
              <iframe
                className="html-preview-iframe"
                title="HTML Preview"
                srcDoc={parsedContent.content}
                sandbox="allow-same-origin allow-scripts"
              />
              <div className="html-preview-actions">
                <a
                  href={`data:text/html;charset=utf-8,${encodeURIComponent(parsedContent.content)}`}
                  download={parsedContent.filename || "preview.html"}
                  className="download-html-btn"
                >
                  Download HTML
                </a>
              </div>
            </div>
          )}
        </div>
      </>
    )
  }

  if (parsedContent.type === 'json') {
    try {
      const jsonContent = typeof parsedContent.content === 'string' 
        ? JSON.parse(parsedContent.content) 
        : parsedContent.content
      const formatted = JSON.stringify(jsonContent, null, 2)
      return (
        <div className="message-text">
          <div className="code-block-wrapper">
            <div className="code-block-header">
              <span className="code-block-language">json</span>
            </div>
            <SyntaxHighlighter
              style={oneLight}
              language="json"
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
                  whiteSpace: 'pre',
                  tabSize: 2,
                }
              }}
            >
              {formatted}
            </SyntaxHighlighter>
          </div>
        </div>
      )
    } catch (e) {
      // JSON parse failed, fall through to default markdown rendering
    }
  }

  return (
    <div className="message-text">
      <MarkdownRenderer content={parsedContent.content} />
    </div>
  )
})

const DEFAULT_BOT_NAME = 'JarvisX'
const CHAT_MODE = {
  TEXT: 'text',
  VOICE: 'voice',
  BOTH: 'both',
}

const getWelcomeText = (agentName) => `Hello, my name is ${agentName}. How can I help you.`

const applyBranding = (name) => {
  if (typeof document === 'undefined') return
  const botName = name?.trim() || DEFAULT_BOT_NAME
  document.title = botName

  const createFaviconDataUrl = () => {
    const canvas = document.createElement('canvas')
    const size = 64
    canvas.width = size
    canvas.height = size
    const ctx = canvas.getContext('2d')
    if (!ctx) return null

    ctx.fillStyle = '#111827'
    ctx.fillRect(0, 0, size, size)

    ctx.fillStyle = '#10B981'
    ctx.font = 'bold 36px "Inter", "Arial", sans-serif'
    ctx.textAlign = 'center'
    ctx.textBaseline = 'middle'
    const initial = botName.charAt(0).toUpperCase()
    ctx.fillText(initial, size / 2, size / 2)

    return canvas.toDataURL('image/png')
  }

  const dataUrl = createFaviconDataUrl()
  if (!dataUrl) return

  const existing = document.getElementById('dynamic-favicon')
  if (existing) {
    existing.href = dataUrl
    return
  }

  const link = document.createElement('link')
  link.id = 'dynamic-favicon'
  link.rel = 'icon'
  link.type = 'image/png'
  link.href = dataUrl
  document.head.appendChild(link)
}

const VoiceChat = ({ user, onLogout }) => {
  const [isListening, setIsListening] = useState(false)
  const [isProcessing, setIsProcessing] = useState(false)
  const [error, setError] = useState(null)
  const [urlType, setUrlType] = useState(null)
  const [resourceId, setResourceId] = useState(null)
  const [workspaceId, setWorkspaceId] = useState(null)
  const [config, setConfig] = useState(null)
  const [isLoadingConfig, setIsLoadingConfig] = useState(true)
  const [configLoadFailed, setConfigLoadFailed] = useState(false)
  const [configErrorMessage, setConfigErrorMessage] = useState(null)
  const [allowFileUpload, setAllowFileUpload] = useState(true)
  const [contextId, setContextId] = useState(() => {
    try {
      const saved = localStorage.getItem('voiceChatContextId')
      return saved || null
    } catch (e) {
      return null
    }
  })
  const [isTranscribing, setIsTranscribing] = useState(false)
  const [micPermissionGranted, setMicPermissionGranted] = useState(false)
  const [isRequestingMic, setIsRequestingMic] = useState(false)
  const [textInput, setTextInput] = useState('')
  const [shouldAutoListen, setShouldAutoListen] = useState(false)
  const [isMuted, setIsMuted] = useState(false)
  const [voiceModeEnabled, setVoiceModeEnabled] = useState(false)
  const [interimTranscript, setInterimTranscript] = useState('')
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const [currentConversationId, setCurrentConversationId] = useState(null)
  const [pendingMessages, setPendingMessages] = useState([])
  const [userMenuOpen, setUserMenuOpen] = useState(false)
  const [attachedFiles, setAttachedFiles] = useState([])
  const [showFileUpload, setShowFileUpload] = useState(false)
  
  const useWebSocketVoice = true

  const wsVoiceUrl = config ? `ws://localhost:9003/ws/voice` : null

  const wsVoice = useVoiceWebSocket({
    wsUrl: wsVoiceUrl,
    organizationId: user?.organization_id,
    workflowId: resourceId,
    userId: user?.id || user?.user_id,
    sessionId: contextId,
    voice: config?.voice_agent_name || 'alloy',
    enabled: useWebSocketVoice && voiceModeEnabled && !!config,
    onTranscript: useCallback((text) => {
      setInterimTranscript('')
      if (text) {
        append({ role: 'user', content: text })
      }
    }, []),
    onTextChunk: useCallback((content) => {
      setMessages(prev => {
        const last = prev[prev.length - 1]
        if (last && last.role === 'assistant' && last._streaming) {
          return [...prev.slice(0, -1), { ...last, content: last.content + content }]
        }
        return [...prev, { id: Date.now().toString(), role: 'assistant', content, _streaming: true }]
      })
    }, []),
    onTextDone: useCallback((sid) => {
      if (sid) setContextId(sid)
      setMessages(prev => {
        const last = prev[prev.length - 1]
        if (last && last._streaming) {
          const { _streaming, ...rest } = last
          return [...prev.slice(0, -1), rest]
        }
        return prev
      })
    }, []),
    onError: useCallback((msg) => {
      setError(msg)
    }, []),
  })

  useEffect(() => {
    if (useWebSocketVoice && voiceModeEnabled && config && !wsVoice.isConnected) {
      wsVoice.connect()
    }
  }, [voiceModeEnabled, config, useWebSocketVoice])

  const processedTextRef = useRef('')
  const userMenuRef = useRef(null)
  const audioQueueRef = useRef([])
  const isPlayingQueueRef = useRef(false)
  const streamFinishedRef = useRef(false)
  const micPermissionRequestedRef = useRef(false)
  const isMutedRef = useRef(isMuted)
  const voiceModeEnabledRef = useRef(voiceModeEnabled)
  const abortControllerRef = useRef(null)
  const currentAudioUrlRef = useRef(null)
  const currentAudioResolveRef = useRef(null)

  const processAudioQueue = async () => {
    if (isPlayingQueueRef.current || audioQueueRef.current.length === 0) {
        if (audioQueueRef.current.length === 0 && !isPlayingQueueRef.current && streamFinishedRef.current) {
            finishProcessing()
        }
        return
    }

    if (speechRecognitionRef.current) {
        try {
            speechRecognitionRef.current.stop()
        } catch (e) {
            // Ignore - stop() can throw if recognition not active
        }
    }
    setIsListening(false)

    isPlayingQueueRef.current = true
    const nextAudioBlob = audioQueueRef.current.shift()

    try {
      await new Promise((resolve, reject) => {
        const audioUrl = URL.createObjectURL(nextAudioBlob)
        currentAudioUrlRef.current = audioUrl
        currentAudioResolveRef.current = resolve
        const audio = new Audio(audioUrl)
        audioPlayerRef.current = audio
        
        const handleEnded = () => {
          URL.revokeObjectURL(audioUrl)
          currentAudioUrlRef.current = null
          currentAudioResolveRef.current = null
          audioPlayerRef.current = null
          resolve()
        }
        
        const handleError = (e) => {
          console.error('Audio playback error:', e)
          URL.revokeObjectURL(audioUrl)
          currentAudioUrlRef.current = null
          currentAudioResolveRef.current = null
          audioPlayerRef.current = null
          resolve()
        }
        
        audio.onended = handleEnded
        audio.onerror = handleError

        audio.play().catch(e => {
          console.error('Play error:', e)
          URL.revokeObjectURL(audioUrl)
          currentAudioUrlRef.current = null
          currentAudioResolveRef.current = null
          audioPlayerRef.current = null
          resolve()
        })
      })
    } catch (error) {
      console.error('Queue processing error:', error)
    } finally {
      isPlayingQueueRef.current = false
      if (audioQueueRef.current.length > 0) {
        processAudioQueue()
      } else {
        if (streamFinishedRef.current) {
            finishProcessing(true)
        }
      }
    }
  }

  const queueTextToSpeech = async (text) => {
    try {
      if (isMutedRef.current || !voiceModeEnabledRef.current) {
        return
      }
      const speechAgentUrl = config ? getSpeechAgentUrl(config) : null
      const userId = user?.id || user?.user_id
      const audioBlob = await textToSpeech(text, null, speechAgentUrl, workspaceId, userId)
      if (audioBlob && audioBlob.size > 0) {
        audioQueueRef.current.push(audioBlob)
        processAudioQueue()
      }
    } catch (err) {
      console.error('Error in queueTextToSpeech:', err)
    }
  }

  useEffect(() => {
    const loadConfig = async () => {
      try {
        setIsLoadingConfig(true)
        const urlInfo = extractUrlInfo()
        
        if (!urlInfo.id) {
          const message = 'ID is required in the URL (e.g., /chatbot/{id} or /workspace/{id}).'
          console.error(message)
          setConfigErrorMessage(message)
          setConfigLoadFailed(true)
          setError(message)
          setIsLoadingConfig(false)
          return
        }

        setUrlType(urlInfo.type)
        setResourceId(urlInfo.id)
        
        if (urlInfo.type === URL_TYPE.CHATBOT) {
          const chatbotConfig = await fetchChatbotConfig(urlInfo.id)
          
          const normalizedConfig = {
            bot_name: chatbotConfig.bot_name || DEFAULT_BOT_NAME,
            chat_mode: chatbotConfig.chat_mode || CHAT_MODE.BOTH,
            allow_file_upload: chatbotConfig.allow_file_upload !== false,
            workflow_id: chatbotConfig.workflow_id,
          }
          
          setConfig(normalizedConfig)
          setAllowFileUpload(normalizedConfig.allow_file_upload)
        } else {
          setWorkspaceId(urlInfo.id)
          const workspaceConfig = await fetchWorkspaceConfig(urlInfo.id)
          
          const normalizedConfig = {
            bot_name: workspaceConfig.voice_agent_name || DEFAULT_BOT_NAME,
            chat_mode: workspaceConfig.chat_mode || CHAT_MODE.BOTH,
            allow_file_upload: true,
          }
          
          setConfig(normalizedConfig)
          setAllowFileUpload(true)
        }
      } catch (err) {
        console.error('Failed to load configuration:', err)
        setConfigLoadFailed(true)
        const message = `Failed to load configuration: ${err.message}`
        setConfigErrorMessage(message)
        setError(message)
      } finally {
        setIsLoadingConfig(false)
      }
    }

    loadConfig()
  }, [])

  const chatMode = config?.chat_mode || CHAT_MODE.BOTH
  const voiceAllowed = chatMode === CHAT_MODE.VOICE || chatMode === CHAT_MODE.BOTH
  const textAllowed = chatMode === CHAT_MODE.TEXT || chatMode === CHAT_MODE.BOTH

  useEffect(() => {
    if (configLoadFailed) {
      applyBranding(configErrorMessage || 'Unavailable')
      return
    }

    if (isLoadingConfig) return

    const botName = config?.bot_name || DEFAULT_BOT_NAME
    applyBranding(botName)
    
    loadWelcomeMessage()
  }, [config, configLoadFailed, configErrorMessage, isLoadingConfig])

  const requestBody = useMemo(() => {
    const body = {
      context_id: contextId,
      session_id: contextId,
    }
    if (urlType === URL_TYPE.CHATBOT && resourceId) {
      body.workflow_id = resourceId
    } else if (workspaceId) {
      body.workspace_id = workspaceId
    }
    const userId = user?.id || user?.user_id
    if (userId) {
      body.user_id = userId
    }
    return body
  }, [contextId, workspaceId, resourceId, urlType, user])

  const requestHeaders = useMemo(() => {
    const headers = {}
    
    const organizationId = user?.organization_id
    if (organizationId) {
      headers['x-tenant-id'] = organizationId
    }
    
    if (urlType === URL_TYPE.CHATBOT && resourceId) {
      headers['x-workflow-id'] = resourceId
    } else if (workspaceId) {
      headers['x-workspace-id'] = workspaceId
    }
    
    const userId = user?.id || user?.user_id
    if (userId) {
      headers['x-user-id'] = userId
    }
    
    const token = getAuthToken()
    if (token) {
      headers['Authorization'] = `Bearer ${token}`
    }
    
    return headers
  }, [workspaceId, resourceId, urlType, user])

  const chatApiEndpoint = useMemo(() => {
    if (urlType === URL_TYPE.CHATBOT && resourceId) {
      return `/api/chatbot/${resourceId}/chat`
    }
    return '/api/chat'
  }, [urlType, resourceId])
  
  const { messages, append, isLoading, setMessages, data, stop } = useChat({
    api: chatApiEndpoint,
    body: requestBody,
    headers: requestHeaders,
    onFinish: async (message) => {
      streamFinishedRef.current = true
      
      if (message.role === 'assistant' && message.content) {
        if (isMuted) {
          audioQueueRef.current = []
          isPlayingQueueRef.current = false
          processedTextRef.current = message.content
          if (audioPlayerRef.current) {
            audioPlayerRef.current.pause()
            audioPlayerRef.current = null
          }
          finishProcessing(voiceAllowed)
          return
        }
        
        if (isCodeContent(message.content)) {
          audioQueueRef.current = []
          isPlayingQueueRef.current = false
          processedTextRef.current = message.content
          if (audioPlayerRef.current) {
            audioPlayerRef.current.pause()
            audioPlayerRef.current = null
          }
          finishProcessing(voiceAllowed)
          return
        }
        
        const parsed = parseMessageContent(message.content)
        const textForTTS = parsed.type === 'html' 
          ? extractTextFromHtml(parsed.content) 
          : parsed.type === 'json'
          ? parsed.content
          : message.content
        
        if (isCodeContent(textForTTS)) {
          audioQueueRef.current = []
          isPlayingQueueRef.current = false
          processedTextRef.current = textForTTS
          if (audioPlayerRef.current) {
            audioPlayerRef.current.pause()
            audioPlayerRef.current = null
          }
          finishProcessing(voiceAllowed)
          return
        }
        
        const remainingText = textForTTS.substring(processedTextRef.current.length)
        if (remainingText.trim().length > 0) {
          if (remainingText.includes('```')) {
            processedTextRef.current = textForTTS
            finishProcessing(voiceAllowed)
            return
          }
          await queueTextToSpeech(remainingText)
        }
        
        if (audioQueueRef.current.length === 0 && !isPlayingQueueRef.current) {
             finishProcessing(voiceAllowed)
        }
      } else {
        console.warn('No assistant message content to convert to speech')
        finishProcessing(voiceAllowed)
      }
    },
    onError: (error) => {
      console.error('Chat error:', error)
      setError(error.message || 'Failed to get response from agent')
      finishProcessing(voiceAllowed)
    },
  })

  useEffect(() => {
    if (isLoading) {
      const lastMessage = messages[messages.length - 1]
      if (lastMessage?.role === 'user') {
         processedTextRef.current = ''
         audioQueueRef.current = []
         isPlayingQueueRef.current = false
         streamFinishedRef.current = false
         if (audioPlayerRef.current) {
           audioPlayerRef.current.pause()
           audioPlayerRef.current = null
         }
      }
    }
  }, [isLoading, messages])

  useEffect(() => {
    if (!isLoading) return

    const lastMessage = messages[messages.length - 1]
    if (!lastMessage || lastMessage.role !== 'assistant') return

    if (isMuted) {
      audioQueueRef.current = []
      isPlayingQueueRef.current = false
      processedTextRef.current = lastMessage.content
      if (audioPlayerRef.current) {
        audioPlayerRef.current.pause()
        audioPlayerRef.current = null
      }
      return
    }

    if (isCodeContent(lastMessage.content)) {
      audioQueueRef.current = []
      isPlayingQueueRef.current = false
      processedTextRef.current = lastMessage.content
      if (audioPlayerRef.current) {
        audioPlayerRef.current.pause()
        audioPlayerRef.current = null
      }
      return
    }

    const parsed = parseMessageContent(lastMessage.content)
    const textForTTS = parsed.type === 'html' 
      ? extractTextFromHtml(parsed.content) 
      : parsed.type === 'json'
      ? parsed.content
      : lastMessage.content
    
    if (isCodeContent(textForTTS)) {
      audioQueueRef.current = []
      isPlayingQueueRef.current = false
      processedTextRef.current = textForTTS
      if (audioPlayerRef.current) {
        audioPlayerRef.current.pause()
        audioPlayerRef.current = null
      }
      return
    }
    
    const unprocessedText = textForTTS.substring(processedTextRef.current.length)
    const sentenceMatch = unprocessedText.match(/([.!?]+)[\s\n]+/)

    if (sentenceMatch) {
      const sentenceEndIndex = sentenceMatch.index + sentenceMatch[0].length
      const sentenceToSpeak = unprocessedText.substring(0, sentenceEndIndex)
      
      if (sentenceToSpeak.includes('```')) {
        processedTextRef.current += sentenceToSpeak
        return
      }
      
      processedTextRef.current += sentenceToSpeak
      queueTextToSpeech(sentenceToSpeak)
    }
  }, [messages, isLoading, isMuted])
  
  const speechRecognitionRef = useRef(null)
  const audioPlayerRef = useRef(null)
  const isProcessingRef = useRef(false)
  const startListeningRef = useRef(null)
  const autoListenTimerRef = useRef(null)
  const micPermissionGrantedRef = useRef(micPermissionGranted)
  const isListeningRef = useRef(isListening)
  const isLoadingRef = useRef(isLoading)
  const isTranscribingRef = useRef(isTranscribing)
  const interimTranscriptRef = useRef('')
  
  const welcomePlayedRef = useRef(false)
  const conversationPanelRef = useRef(null)
  const textInputRef = useRef(null)
  const fileInputRef = useRef(null)

  useEffect(() => {
    return () => {
      if (speechRecognitionRef.current) {
        try {
          speechRecognitionRef.current.stop()
        } catch (err) {
          console.error('Error stopping speech recognition:', err)
        }
        speechRecognitionRef.current = null
      }
      if (audioPlayerRef.current) {
        try {
          audioPlayerRef.current.pause()
        } catch (err) {
          console.error('Error pausing audio player:', err)
        }
        audioPlayerRef.current = null
      }
    }
  }, [])

  useEffect(() => {
    if (data && data.length > 0) {
      for (const dataItem of data) {
        const newSessionId = dataItem?.session_id || dataItem?.context_id
        if (newSessionId && newSessionId !== contextId) {
          setContextId(newSessionId)
          try {
            localStorage.setItem('voiceChatContextId', newSessionId)
          } catch (e) {
            // Ignore localStorage errors (private browsing, quota exceeded)
          }
          break
        }
      }
    }
  }, [data, contextId])

  useEffect(() => {
    micPermissionGrantedRef.current = micPermissionGranted
  }, [micPermissionGranted])

  useEffect(() => {
    isListeningRef.current = isListening
  }, [isListening])

  useEffect(() => {
    isLoadingRef.current = isLoading
  }, [isLoading])

  useEffect(() => {
    isTranscribingRef.current = isTranscribing
  }, [isTranscribing])
  

  useEffect(() => {
    if (!shouldAutoListen) return

    const attemptListen = () => {
      if (!voiceAllowed || !micPermissionGrantedRef.current) {
        setShouldAutoListen(false)
        return
      }
      if (isListeningRef.current) {
        setShouldAutoListen(false)
        return
      }
      if (
        isProcessingRef.current ||
        isPlayingQueueRef.current ||
        isLoadingRef.current ||
        isTranscribingRef.current
      ) {
        autoListenTimerRef.current = setTimeout(attemptListen, 250)
        return
      }
      startListeningRef.current?.()
      setShouldAutoListen(false)
    }

    attemptListen()

    return () => {
      if (autoListenTimerRef.current) {
        clearTimeout(autoListenTimerRef.current)
        autoListenTimerRef.current = null
      }
    }
  }, [shouldAutoListen, voiceAllowed])
  
  const requestMicrophonePermission = async () => {
    if (micPermissionRequestedRef.current && micPermissionGranted) return true
    
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      setError('Microphone access is not supported in this browser.')
      return false
    }
    
    setIsRequestingMic(true)
    micPermissionRequestedRef.current = true
    
    try {
      const constraints = {
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
          sampleRate: 16000,
        }
      }
      
      const stream = await navigator.mediaDevices.getUserMedia(constraints)
      stream.getTracks().forEach(track => track.stop())
      
      setMicPermissionGranted(true)
      setIsRequestingMic(false)
      return true
    } catch (err) {
      console.error('Error requesting microphone permission:', err)
      setIsRequestingMic(false)
      micPermissionRequestedRef.current = false
      
      if (err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError') {
        setError('Microphone access denied. Please allow microphone access to use voice chat.')
      } else if (err.name === 'NotFoundError' || err.name === 'DevicesNotFoundError') {
        setError('No microphone found. Please connect a microphone and try again.')
      } else {
        setError('Failed to access microphone. Please check your browser settings and try again.')
      }
      return false
    }
  }

  useEffect(() => {
    const scrollToBottom = () => {
      if (conversationPanelRef.current) {
        conversationPanelRef.current.scrollTop = conversationPanelRef.current.scrollHeight
      }
    }
    
    scrollToBottom()
    const timeoutId = setTimeout(scrollToBottom, 50)
    
    return () => clearTimeout(timeoutId)
  }, [messages, interimTranscript, isLoading])

  const loadWelcomeMessage = () => {
    if (welcomePlayedRef.current) return

    const userMessages = messages.filter(m => m.role === 'user')
    if (userMessages.length > 0) return

    welcomePlayedRef.current = true

    try {
      const botName = config?.bot_name || 'JarvisX'
      const welcomeText = getWelcomeText(botName)
      
      if (setMessages) {
        setMessages([{
          id: `welcome-${Date.now()}`,
          role: 'assistant',
          content: welcomeText,
        }])
      }
    } catch (err) {
      console.error('Error loading welcome message:', err)
      welcomePlayedRef.current = false
    }
  }

  const getSpeechRecognition = () => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition
    if (!SpeechRecognition) {
      return null
    }
    return new SpeechRecognition()
  }

  const SILENCE_TIMEOUT_MS = 1500
  const silenceTimerRef = useRef(null)
  const accumulatedTranscriptRef = useRef('')

  const clearSilenceTimer = () => {
    if (silenceTimerRef.current) {
      clearTimeout(silenceTimerRef.current)
      silenceTimerRef.current = null
    }
  }

  const startSilenceTimer = (recognition) => {
    clearSilenceTimer()
    silenceTimerRef.current = setTimeout(() => {
      const fullTranscript = accumulatedTranscriptRef.current.trim()
      if (fullTranscript) {
        recognition.stop()
        setInterimTranscript('')
        accumulatedTranscriptRef.current = ''
        processVoiceInput(fullTranscript)
      }
    }, SILENCE_TIMEOUT_MS)
  }

  const startListening = async () => {
    if (isProcessingRef.current || isProcessing || isLoading || isTranscribing) {
      return
    }
    
    const recognition = getSpeechRecognition()
    if (!recognition) {
      setError('Speech recognition is not supported in this browser. Please use Chrome or Edge.')
      return
    }
    
    try {
      setError(null)
      setInterimTranscript('')
      interimTranscriptRef.current = ''
      accumulatedTranscriptRef.current = ''
      clearSilenceTimer()
      
      recognition.continuous = true
      recognition.interimResults = true
      recognition.lang = 'en-US'
      
      recognition.onstart = () => {
        setIsListening(true)
        setMicPermissionGranted(true)
      }
      
      recognition.onresult = (event) => {
        let newFinalTranscript = ''
        let interim = ''
        
        for (let i = event.resultIndex; i < event.results.length; i++) {
          const transcript = event.results[i][0].transcript
          if (event.results[i].isFinal) {
            newFinalTranscript += transcript
          } else {
            interim += transcript
          }
        }
        
        if (newFinalTranscript) {
          accumulatedTranscriptRef.current += newFinalTranscript
        }
        
        const displayText = accumulatedTranscriptRef.current + interim
        setInterimTranscript(displayText)
        interimTranscriptRef.current = displayText
        
        if (newFinalTranscript || interim) {
          startSilenceTimer(recognition)
        }
      }
      
      recognition.onerror = (event) => {
        console.error('Speech recognition error:', event.error)
        clearSilenceTimer()
        setInterimTranscript('')
        accumulatedTranscriptRef.current = ''
        if (event.error === 'not-allowed') {
          setError('Microphone access denied. Please allow microphone access to use voice input.')
          setMicPermissionGranted(false)
        } else if (event.error === 'no-speech') {
          if (voiceModeEnabledRef.current && !isProcessingRef.current) {
            setTimeout(() => {
              if (voiceModeEnabledRef.current && !isProcessingRef.current) {
                startListening()
              }
            }, 500)
          }
        } else if (event.error !== 'aborted') {
          setError(`Speech recognition error: ${event.error}`)
        }
        setIsListening(false)
      }
      
      recognition.onend = () => {
        setIsListening(false)
        clearSilenceTimer()
        const remainingTranscript = accumulatedTranscriptRef.current.trim()
        if (remainingTranscript && !isProcessingRef.current) {
          accumulatedTranscriptRef.current = ''
          setInterimTranscript('')
          processVoiceInput(remainingTranscript)
        } else {
          setInterimTranscript('')
        }
        speechRecognitionRef.current = null
      }
      
      speechRecognitionRef.current = recognition
      recognition.start()
      
    } catch (err) {
      console.error('Error starting speech recognition:', err)
      setError('Failed to start speech recognition. Please try again.')
      setIsListening(false)
    }
  }
  startListeningRef.current = startListening

  const stopListening = () => {
    clearSilenceTimer()
    if (speechRecognitionRef.current) {
      try {
        speechRecognitionRef.current.stop()
      } catch (err) {
        console.error('Error stopping speech recognition:', err)
      }
      speechRecognitionRef.current = null
    }
    accumulatedTranscriptRef.current = ''
    setInterimTranscript('')
    setIsListening(false)
  }

  const processVoiceInput = async (text) => {
    if (!voiceAllowed) {
      setError('Voice input is disabled for this workspace.')
      return
    }
    if (isProcessingRef.current || isPlayingQueueRef.current) {
      return
    }
    
    if (!text || !text.trim()) {
      if (voiceModeEnabledRef.current) {
        setTimeout(() => {
          if (voiceModeEnabledRef.current && !isProcessingRef.current && !isPlayingQueueRef.current) {
            startListening()
          }
        }, 500)
      }
      return
    }
    
    isProcessingRef.current = true
    setIsProcessing(true)
    setError(null)
    isActiveSessionRef.current = true
    
    try {
      await append({ 
        role: 'user', 
        content: text.trim() 
      })
    } catch (err) {
      console.error('Error processing voice input:', err)
      setError(err.message || 'Failed to send message. Please try again.')
      isProcessingRef.current = false
      setIsProcessing(false)
    }
  }

  const processTextMessage = async (text, files = []) => {
    if (!textAllowed) {
      setError('Text input is disabled for this workspace.')
      return
    }
    if (isProcessingRef.current) {
      return
    }
    
    if ((!text || !text.trim()) && files.length === 0) {
      return
    }
    
    isProcessingRef.current = true
    setIsProcessing(true)
    setError(null)
    isActiveSessionRef.current = true
    
    try {
      let messageContent = text.trim()
      
      if (files.length > 0) {
        const fileData = await filesToBase64(files)
        const fileDescriptions = files.map(f => {
          const typeInfo = getFileTypeInfo(f.type)
          return `[${typeInfo.icon} ${f.name} (${typeInfo.label}, ${formatFileSize(f.size)})]`
        }).join('\n')
        
        messageContent = messageContent 
          ? `${messageContent}\n\nAttached files:\n${fileDescriptions}`
          : `Please analyze these files:\n${fileDescriptions}`
        
        await append({ 
          role: 'user', 
          content: messageContent,
          data: { files: fileData }
        })
      } else {
        await append({ 
          role: 'user', 
          content: messageContent 
        })
      }
      
      setTextInput('')
      setAttachedFiles([])
      
    } catch (err) {
      console.error('Error processing text message:', err)
      setError(err.message || 'Failed to send message. Please try again.')
      isProcessingRef.current = false
      setIsProcessing(false)
    }
  }

  const handleTextSubmit = async (e) => {
    e.preventDefault()
    if (!textAllowed) {
      setError('Text input is disabled for this workspace.')
      return
    }
    if ((!textInput.trim() && attachedFiles.length === 0) || isProcessing || isLoading) {
      return
    }
    
    if (isListening || isProcessingRef.current) {
      cancelCurrentOperation()
      await new Promise(resolve => setTimeout(resolve, 200))
    }
    
    await processTextMessage(textInput, attachedFiles)
  }

  const handleTextKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleTextSubmit(e)
    }
  }

  const handleFileSelect = useCallback((files) => {
    setAttachedFiles(prev => [...prev, ...files])
    setShowFileUpload(false)
  }, [])

  const handleFileRemove = useCallback((index) => {
    setAttachedFiles(prev => prev.filter((_, i) => i !== index))
  }, [])

  const handleAttachmentClick = useCallback(() => {
    if (fileInputRef.current) {
      fileInputRef.current.click()
    }
  }, [])

  const handleFileInputChange = useCallback((e) => {
    if (e.target.files?.length > 0) {
      handleFileSelect(Array.from(e.target.files))
      e.target.value = ''
    }
  }, [handleFileSelect])
  
  const stopAudioPlayback = () => {
    if (audioPlayerRef.current) {
      try {
        audioPlayerRef.current.pause()
        audioPlayerRef.current.currentTime = 0
        audioPlayerRef.current.onended = null
        audioPlayerRef.current.onerror = null
      } catch (err) {
        console.error('Error stopping audio player:', err)
      }
      audioPlayerRef.current = null
    }
    
    if (currentAudioResolveRef.current) {
      try {
        currentAudioResolveRef.current()
      } catch (err) {
        console.error('Error resolving audio Promise:', err)
      }
      currentAudioResolveRef.current = null
    }
    
    if (currentAudioUrlRef.current) {
      try {
        URL.revokeObjectURL(currentAudioUrlRef.current)
      } catch (err) {
        console.error('Error revoking audio URL:', err)
      }
      currentAudioUrlRef.current = null
    }
    
    audioQueueRef.current = []
    isPlayingQueueRef.current = false
  }
  
  useEffect(() => {
    isMutedRef.current = isMuted
    if (isMuted) {
      stopAudioPlayback()
    }
  }, [isMuted])

  useEffect(() => {
    voiceModeEnabledRef.current = voiceModeEnabled
  }, [voiceModeEnabled])
  
  const cancelCurrentOperation = () => {
    if (isLoading) {
      stop()
    }
    
    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
      abortControllerRef.current = null
    }
    
    stopAudioPlayback()
    
    if (isListening) {
      stopListening()
    }
    
    isProcessingRef.current = false
    setIsProcessing(false)
    setIsTranscribing(false)
    streamFinishedRef.current = false
    processedTextRef.current = ''
    interimTranscriptRef.current = ''
  }

  const finishProcessing = (shouldResumeListening = false) => {
    isProcessingRef.current = false
    setIsProcessing(false)
    setIsTranscribing(false)
    streamFinishedRef.current = false
    processedTextRef.current = ''
    
    if (shouldResumeListening && voiceAllowed && micPermissionGranted && voiceModeEnabled) {
        setTimeout(() => {
            if (!isProcessingRef.current && !isPlayingQueueRef.current) {
                setShouldAutoListen(true)
            }
        }, 800)
    }
  }

  const toggleListening = async () => {
    if (!voiceAllowed) {
      setError('Voice input is disabled for this workspace.')
      return
    }
    
    if (isListening || wsVoice.isListening) {
      if (useWebSocketVoice) {
        wsVoice.stopListening()
        wsVoice.stopPlayback()
      } else {
        stopListening()
      }
      setVoiceModeEnabled(false)
      setShouldAutoListen(false)
      return
    }
    
    if (isProcessingRef.current || isProcessing || isLoading || isTranscribing || isPlayingQueueRef.current) {
      cancelCurrentOperation()
      await new Promise(resolve => setTimeout(resolve, 200))
    }
    
    if (!micPermissionGranted) {
      const permissionGranted = await requestMicrophonePermission()
      if (!permissionGranted) {
        return
      }
    }
    
    setVoiceModeEnabled(true)
    if (useWebSocketVoice) {
      if (!wsVoice.isConnected) {
        await wsVoice.connect()
      }
      wsVoice.startListening()
    } else {
      startListening()
    }
  }

  const displayMessages = messages.filter(m => m.role === 'user' || m.role === 'assistant')

  const handleSelectConversation = useCallback(async (conversation) => {
    if (conversation.id === currentConversationId) return
    
    isActiveSessionRef.current = false
    
    const currentWorkflowId = urlType === URL_TYPE.CHATBOT ? resourceId : workspaceId
    
    try {
      const fullConversation = await getConversation(currentWorkflowId, conversation.id)
      setCurrentConversationId(conversation.id)
      
      if (conversation.session_id || fullConversation.session_id) {
        const sessionId = conversation.session_id || fullConversation.session_id
        setContextId(sessionId)
        try {
          localStorage.setItem('voiceChatContextId', sessionId)
        } catch (e) {
          // Ignore localStorage errors (private browsing, quota exceeded)
        }
      }
      
      const loadedMessages = fullConversation.messages.map(m => ({
        id: m.id,
        role: m.role,
        content: m.content,
      }))
      setMessages(loadedMessages)
      savedMessageCountRef.current = loadedMessages.length
    } catch (err) {
      console.error('Failed to load conversation:', err)
      setError('Failed to load conversation')
    }
  }, [currentConversationId, setMessages, urlType, resourceId, workspaceId])

  const handleNewConversation = useCallback(() => {
    const newContextId = crypto.randomUUID()
    setContextId(newContextId)
    try {
      localStorage.setItem('voiceChatContextId', newContextId)
    } catch (e) {
      // Ignore localStorage errors (private browsing, quota exceeded)
    }
    setCurrentConversationId(null)
    setMessages([])
    setPendingMessages([])
    savedMessageCountRef.current = 0
    isActiveSessionRef.current = false
  }, [setMessages])

  const savedMessageCountRef = useRef(0)
  const isActiveSessionRef = useRef(false)
  const savingRef = useRef(false)
  
  const saveConversation = useCallback(async (newMessages) => {
    if (!workspaceId || !user) return
    if (newMessages.length < 2) return
    if (!isActiveSessionRef.current) return
    if (savingRef.current) return
    
    const hasUserMessage = newMessages.some(m => m.role === 'user' && m.content?.trim())
    const hasAssistantMessage = newMessages.some(m => m.role === 'assistant' && m.content?.trim())
    if (!hasUserMessage || !hasAssistantMessage) return
    
    savingRef.current = true
    
    try {
      if (!currentConversationId) {
        const messagesToSave = newMessages.map(m => ({
          role: m.role,
          content: m.content,
        }))
        const conversation = await createConversation(workspaceId, null, messagesToSave)
        setCurrentConversationId(conversation.id)
        savedMessageCountRef.current = newMessages.length
        if (window.refreshConversationSidebar) {
          window.refreshConversationSidebar()
        }
      } else {
        const newOnly = newMessages.slice(savedMessageCountRef.current).map(m => ({
          role: m.role,
          content: m.content,
        }))
        if (newOnly.length > 0) {
          await addMessagesBulk(currentConversationId, newOnly)
          savedMessageCountRef.current = newMessages.length
        }
      }
    } catch (err) {
      console.error('Failed to save conversation:', err)
    } finally {
      savingRef.current = false
    }
  }, [workspaceId, user, currentConversationId])

  useEffect(() => {
    if (!isLoading && messages.length >= 2 && isActiveSessionRef.current) {
      const hasUserMessage = messages.some(m => m.role === 'user' && m.content?.trim())
      const lastMsg = messages[messages.length - 1]
      if (hasUserMessage && lastMsg.role === 'assistant' && lastMsg.content?.trim()) {
        saveConversation(messages)
      }
    }
  }, [isLoading, messages, saveConversation])

  const renderNotFound = (message) => (
    <div className="chat-container">
      <div className="chat-main">
        <div className="chat-header">
          <h1 className="chat-title">Unavailable</h1>
        </div>
        <div className="chat-messages" style={{ justifyContent: 'center', alignItems: 'center' }}>
          <div style={{ textAlign: 'center', color: 'var(--color-text-secondary)' }}>
            <div style={{ fontSize: '48px', marginBottom: '16px' }}>🔍</div>
            <p>{message || 'Check the link or try again later.'}</p>
          </div>
        </div>
      </div>
    </div>
  )

  if (isLoadingConfig) {
    return (
      <div className="chat-container">
        <div className="chat-main">
          <div className="chat-header">
            <h1 className="chat-title">Loading...</h1>
          </div>
          <div className="chat-messages" style={{ justifyContent: 'center', alignItems: 'center' }}>
            <div className="loading-spinner"></div>
          </div>
        </div>
      </div>
    )
  }

  if (configLoadFailed) {
    return renderNotFound(configErrorMessage)
  }

  const botName = config?.bot_name || 'JarvisX'
  const isBusy = isProcessing || isLoading || isTranscribing

  const getUserInitials = () => {
    if (!user) return '?'
    const firstName = user.first_name || ''
    const lastName = user.last_name || ''
    if (firstName && lastName) {
      return `${firstName[0]}${lastName[0]}`.toUpperCase()
    }
    if (firstName) return firstName[0].toUpperCase()
    if (user.email) return user.email[0].toUpperCase()
    return '?'
  }

  const getUserDisplayName = () => {
    if (!user) return 'User'
    if (user.first_name && user.last_name) {
      return `${user.first_name} ${user.last_name}`
    }
    if (user.first_name) return user.first_name
    return user.email || 'User'
  }

  return (
    <div className="chat-container with-sidebar">
      <div className="chat-header">
        <div className="chat-header-left">
          {!sidebarOpen && (
            <button 
              className="header-icon-btn sidebar-open-btn" 
              onClick={() => setSidebarOpen(true)}
              title="Open sidebar"
            >
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
                <line x1="9" y1="3" x2="9" y2="21" />
              </svg>
            </button>
          )}
        </div>
        <div className="chat-header-center">
          <div className="brand-logo">
            <div className="brand-icon">
              <svg width="28" height="28" viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
                <rect width="32" height="32" rx="8" fill="url(#jarvis-chat-gradient)"/>
                <path d="M16 6C10.477 6 6 10.477 6 16s4.477 10 10 10 10-4.477 10-10S21.523 6 16 6zm0 2a8 8 0 110 16 8 8 0 010-16z" fill="rgba(255,255,255,0.2)"/>
                <circle cx="16" cy="16" r="4" fill="white"/>
                <circle cx="16" cy="16" r="2" fill="url(#jarvis-chat-gradient)"/>
                <path d="M16 8v4M16 20v4M8 16h4M20 16h4" stroke="rgba(255,255,255,0.6)" strokeWidth="1.5" strokeLinecap="round"/>
                <circle cx="12" cy="12" r="1.5" fill="rgba(255,255,255,0.8)"/>
                <circle cx="20" cy="12" r="1.5" fill="rgba(255,255,255,0.8)"/>
                <circle cx="12" cy="20" r="1.5" fill="rgba(255,255,255,0.8)"/>
                <circle cx="20" cy="20" r="1.5" fill="rgba(255,255,255,0.8)"/>
                <defs>
                  <linearGradient id="jarvis-chat-gradient" x1="0" y1="0" x2="32" y2="32" gradientUnits="userSpaceOnUse">
                    <stop stopColor="#6366f1"/>
                    <stop offset="1" stopColor="#8b5cf6"/>
                  </linearGradient>
                </defs>
              </svg>
              {isBusy && <span className="brand-status-ring"></span>}
            </div>
            <h1 className="chat-title">
              <span className="brand-text">{botName}</span>
              {isBusy && <span className="thinking-indicator"><span></span><span></span><span></span></span>}
            </h1>
          </div>
        </div>
        <div className="chat-header-right">
          {voiceAllowed && (
            <button
              className={`header-icon-btn ${isMuted ? 'muted' : ''}`}
              onClick={() => setIsMuted(prev => !prev)}
              title={isMuted ? 'Unmute voice responses' : 'Mute voice responses'}
            >
              {isMuted ? <VolumeOffIcon size={20} /> : <VolumeIcon size={20} />}
            </button>
          )}
          {user && (
            <div className="user-menu-container" ref={userMenuRef}>
              <button 
                className="user-avatar-btn"
                onClick={() => setUserMenuOpen(prev => !prev)}
                title={getUserDisplayName()}
              >
                {getUserInitials()}
              </button>
              {userMenuOpen && (
                <div className="user-menu-dropdown">
                  <div className="user-menu-header">
                    <div className="user-menu-avatar">{getUserInitials()}</div>
                    <div className="user-menu-info">
                      <span className="user-menu-name">{getUserDisplayName()}</span>
                      {user.email && <span className="user-menu-email">{user.email}</span>}
                    </div>
                  </div>
                  <div className="user-menu-divider"></div>
                  <button className="user-menu-item" onClick={onLogout}>
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
                      <polyline points="16 17 21 12 16 7" />
                      <line x1="21" y1="12" x2="9" y2="12" />
                    </svg>
                    <span>Log out</span>
                  </button>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      <div className="chat-body">
        {user && (
          <ConversationSidebar
            workflowId={urlType === URL_TYPE.CHATBOT ? resourceId : workspaceId}
            currentConversationId={currentConversationId}
            onSelectConversation={handleSelectConversation}
            onNewConversation={handleNewConversation}
            isOpen={sidebarOpen}
            onToggle={() => setSidebarOpen(prev => !prev)}
          />
        )}
        <div className="chat-main">
          {error && (
          <div className="chat-error">
            <span>⚠️ {error}</span>
            <button onClick={() => setError(null)} className="error-dismiss">×</button>
          </div>
        )}

        <div className="chat-messages" ref={conversationPanelRef}>
          {displayMessages.length === 0 && !interimTranscript ? (
            <div className="chat-empty">
              <div className="empty-icon">{botName.charAt(0).toUpperCase()}</div>
              <h2>Start a conversation</h2>
              <p>Type a message or {voiceAllowed ? 'click the microphone to speak' : 'press Enter to send'}</p>
            </div>
          ) : (
            <>
              {displayMessages.map((message, index) => (
                <div key={message.id || index} className={`chat-message ${message.role}`}>
                  <div className="message-inner">
                    <div className="message-avatar">
                      {message.role === 'user' ? 'U' : botName.charAt(0).toUpperCase()}
                    </div>
                    <div className="message-content">
                      <div className="message-sender">
                        {message.role === 'user' ? 'You' : botName}
                      </div>
                      <MessageContent message={message} />
                      {message.role === 'assistant' && isLoading && index === displayMessages.length - 1 && (
                        <span className="typing-dots">
                          <span></span><span></span><span></span>
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              ))}
              {isListening && interimTranscript && (
                <div className="chat-message user interim">
                  <div className="message-inner">
                    <div className="message-avatar">U</div>
                    <div className="message-content">
                      <div className="message-sender">You</div>
                      <div className="message-text interim-text">
                        {interimTranscript}
                        <span className="listening-indicator">
                          <span></span><span></span><span></span>
                        </span>
                      </div>
                    </div>
                  </div>
                </div>
              )}
              {isLoading && displayMessages.length > 0 && displayMessages[displayMessages.length - 1].role === 'user' && (
                <div className="chat-message assistant thinking">
                  <div className="message-inner">
                    <div className="message-avatar">{botName.charAt(0).toUpperCase()}</div>
                    <div className="message-content">
                      <div className="message-sender">{botName}</div>
                      <div className="message-text thinking-bubble">
                        <span className="thinking-text">Thinking</span>
                        <span className="thinking-dots">
                          <span></span><span></span><span></span>
                        </span>
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </>
          )}
        </div>

        <div className="chat-input-container">
          {attachedFiles.length > 0 && (
            <div className="attached-files-preview">
              {attachedFiles.map((file, index) => {
                const typeInfo = getFileTypeInfo(file.type)
                return (
                  <div key={`${file.name}-${index}`} className="attached-file-item">
                    <span className="attached-file-icon">{typeInfo.icon}</span>
                    <span className="attached-file-name">{file.name}</span>
                    <span className="attached-file-size">{formatFileSize(file.size)}</span>
                    <button
                      type="button"
                      className="attached-file-remove"
                      onClick={() => handleFileRemove(index)}
                      title="Remove file"
                    >
                      ×
                    </button>
                  </div>
                )
              })}
            </div>
          )}
          <form className="chat-input-form" onSubmit={handleTextSubmit}>
            <input
              ref={fileInputRef}
              type="file"
              multiple
              accept="image/*,audio/*,video/*,application/pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.txt,.csv,.json,.md"
              onChange={handleFileInputChange}
              style={{ display: 'none' }}
            />
            <div className="chat-input-wrapper">
              {allowFileUpload && (
                <button
                  type="button"
                  className="input-icon-btn attach-btn"
                  onClick={handleAttachmentClick}
                  disabled={isBusy}
                  title="Attach file"
                >
                  <AttachmentIcon size={18} />
                </button>
              )}
              <textarea
                ref={textInputRef}
                className="chat-input"
                value={textInput}
                onChange={(e) => setTextInput(e.target.value)}
                onKeyDown={handleTextKeyDown}
                placeholder={textAllowed ? "Type your message..." : "Text input disabled"}
                rows={1}
                disabled={!textAllowed || isBusy}
              />
              <div className="chat-input-actions">
                {voiceAllowed && (
                  <button
                    type="button"
                    className={`input-icon-btn mic-btn ${isListening ? 'listening' : ''} ${isBusy && !isListening ? 'busy' : ''}`}
                    onClick={toggleListening}
                    disabled={isRequestingMic}
                    title={
                      isRequestingMic 
                        ? 'Requesting microphone...'
                        : isListening 
                        ? 'Stop listening' 
                        : isBusy
                        ? 'Cancel and speak'
                        : 'Start voice input'
                    }
                  >
                    {isRequestingMic ? (
                      <div className="mini-spinner"></div>
                    ) : isListening ? (
                      <StopIcon size={18} />
                    ) : (
                      <MicrophoneIcon size={18} />
                    )}
                  </button>
                )}
                <button
                  type="submit"
                  className="input-icon-btn send-btn"
                  disabled={!textAllowed || (!textInput.trim() && attachedFiles.length === 0) || isBusy}
                  title="Send message"
                >
                  <SendIcon size={18} />
                </button>
              </div>
            </div>
          </form>
          </div>
        </div>
      </div>
    </div>
  )
}

export default VoiceChat
