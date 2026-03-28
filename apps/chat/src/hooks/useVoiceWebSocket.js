import { useState, useRef, useCallback, useEffect } from 'react'
import { VoiceWebSocket, float32ToBase64PCM16, base64ToAudioBlob } from '../services/voiceWebSocket'

export function useVoiceWebSocket({
  wsUrl,
  organizationId,
  workflowId,
  userId,
  sessionId,
  voice = 'alloy',
  enabled = true,
  onTranscript,
  onTextChunk,
  onTextDone,
  onError,
}) {
  const [isConnected, setIsConnected] = useState(false)
  const [isListening, setIsListening] = useState(false)
  const [isProcessing, setIsProcessing] = useState(false)
  const [isSpeaking, setIsSpeaking] = useState(false)

  const wsRef = useRef(null)
  const vadRef = useRef(null)
  const audioContextRef = useRef(null)
  const audioQueueRef = useRef([])
  const isPlayingRef = useRef(false)
  const audioPlayerRef = useRef(null)
  const allAudioReceivedRef = useRef(false)
  const sessionIdRef = useRef(sessionId)

  useEffect(() => { sessionIdRef.current = sessionId }, [sessionId])

  const playNextInQueue = useCallback(async () => {
    if (isPlayingRef.current || audioQueueRef.current.length === 0) {
      if (audioQueueRef.current.length === 0 && !isPlayingRef.current && allAudioReceivedRef.current) {
        setIsSpeaking(false)
        setIsProcessing(false)
      }
      return
    }

    isPlayingRef.current = true
    setIsSpeaking(true)
    const blob = audioQueueRef.current.shift()

    try {
      await new Promise((resolve) => {
        const url = URL.createObjectURL(blob)
        const audio = new Audio(url)
        audioPlayerRef.current = audio
        audio.onended = () => { URL.revokeObjectURL(url); audioPlayerRef.current = null; resolve() }
        audio.onerror = () => { URL.revokeObjectURL(url); audioPlayerRef.current = null; resolve() }
        audio.play().catch(() => { URL.revokeObjectURL(url); audioPlayerRef.current = null; resolve() })
      })
    } finally {
      isPlayingRef.current = false
      playNextInQueue()
    }
  }, [])

  const stopPlayback = useCallback(() => {
    audioQueueRef.current = []
    isPlayingRef.current = false
    allAudioReceivedRef.current = true
    if (audioPlayerRef.current) {
      audioPlayerRef.current.pause()
      audioPlayerRef.current = null
    }
    setIsSpeaking(false)
    if (wsRef.current?.isConnected) {
      wsRef.current.stopAudio()
    }
  }, [])

  const connect = useCallback(async () => {
    if (!enabled || !wsUrl || !organizationId || !workflowId) return

    const ws = new VoiceWebSocket()
    wsRef.current = ws

    ws.onTranscript((msg) => {
      if (msg.text && onTranscript) onTranscript(msg.text)
    })

    ws.onTextChunk((msg) => {
      if (msg.content && onTextChunk) onTextChunk(msg.content)
    })

    ws.onAudioChunk((msg) => {
      if (msg.data) {
        const blob = base64ToAudioBlob(msg.data)
        audioQueueRef.current.push(blob)
        playNextInQueue()
      }
    })

    ws.onTextDone((msg) => {
      if (msg.session_id) sessionIdRef.current = msg.session_id
      if (onTextDone) onTextDone(msg.session_id)
    })

    ws.on('audioDone', () => {
      allAudioReceivedRef.current = true
      if (audioQueueRef.current.length === 0 && !isPlayingRef.current) {
        setIsSpeaking(false)
        setIsProcessing(false)
      }
    })

    ws.onError((msg) => {
      if (onError) onError(msg.message)
      setIsProcessing(false)
    })

    ws.on('close', () => {
      setIsConnected(false)
    })

    try {
      await ws.connect(wsUrl, {
        organization_id: organizationId,
        workflow_id: workflowId,
        user_id: userId,
        session_id: sessionId,
        voice,
      })
      setIsConnected(true)
    } catch (e) {
      console.error('[useVoiceWS] Connection failed:', e)
      if (onError) onError('Failed to connect to voice service')
    }
  }, [wsUrl, organizationId, workflowId, userId, sessionId, voice, enabled, onTranscript, onTextChunk, onTextDone, onError, playNextInQueue])

  const disconnect = useCallback(() => {
    if (vadRef.current) {
      try { vadRef.current.destroy() } catch (e) { /* ignore */ }
      vadRef.current = null
    }
    if (wsRef.current) {
      wsRef.current.disconnect()
      wsRef.current = null
    }
    setIsConnected(false)
    setIsListening(false)
    setIsProcessing(false)
    setIsSpeaking(false)
  }, [])

  const startListening = useCallback(async () => {
    if (!wsRef.current?.isConnected) return

    stopPlayback()
    setIsListening(true)

    try {
      const vad = await import('@ricky0123/vad-web')
      const myvad = await vad.MicVAD.new({
        positiveSpeechThreshold: 0.8,
        negativeSpeechThreshold: 0.3,
        minSpeechFrames: 3,
        preSpeechPadFrames: 5,
        redemptionFrames: 8,
        onFrameProcessed: (probs, frame) => {
          if (wsRef.current?.isConnected && frame) {
            const b64 = float32ToBase64PCM16(frame)
            wsRef.current.sendAudioChunk(b64)
          }
        },
        onSpeechStart: () => {
          stopPlayback()
        },
        onSpeechEnd: (audio) => {
          setIsListening(false)
          setIsProcessing(true)
          allAudioReceivedRef.current = false
          audioQueueRef.current = []

          if (wsRef.current?.isConnected) {
            if (audio && audio.length > 0) {
              const b64 = float32ToBase64PCM16(audio)
              wsRef.current.sendAudioChunk(b64)
            }
            wsRef.current.sendSpeechEnd()
          }

          if (vadRef.current) {
            try { vadRef.current.pause() } catch (e) { /* ignore */ }
          }
        },
      })

      vadRef.current = myvad
      myvad.start()
    } catch (e) {
      console.error('[useVoiceWS] VAD init failed:', e)
      setIsListening(false)
      if (onError) onError('Failed to initialize voice detection')
    }
  }, [stopPlayback, onError])

  const stopListening = useCallback(() => {
    if (vadRef.current) {
      try { vadRef.current.pause() } catch (e) { /* ignore */ }
    }
    setIsListening(false)
  }, [])

  const sendText = useCallback((text) => {
    if (!wsRef.current?.isConnected || !text) return
    stopPlayback()
    setIsProcessing(true)
    allAudioReceivedRef.current = false
    audioQueueRef.current = []
    wsRef.current.sendTextMessage(text, sessionIdRef.current)
  }, [stopPlayback])

  useEffect(() => {
    return () => disconnect()
  }, [disconnect])

  return {
    isConnected,
    isListening,
    isProcessing,
    isSpeaking,
    connect,
    disconnect,
    startListening,
    stopListening,
    stopPlayback,
    sendText,
    sessionId: sessionIdRef.current,
  }
}
