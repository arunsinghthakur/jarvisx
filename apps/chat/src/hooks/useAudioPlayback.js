import { useState, useRef, useCallback, useEffect } from 'react'
import { textToSpeech, getSpeechAgentUrl } from '../services'

export function useAudioPlayback(workspaceConfig, isMuted, workspaceId = null, userId = null) {
  const [isPlaying, setIsPlaying] = useState(false)
  
  const audioQueueRef = useRef([])
  const isPlayingQueueRef = useRef(false)
  const audioPlayerRef = useRef(null)
  const currentAudioUrlRef = useRef(null)
  const currentAudioResolveRef = useRef(null)
  const isMutedRef = useRef(isMuted)
  const onQueueEmptyRef = useRef(null)

  useEffect(() => {
    isMutedRef.current = isMuted
    if (isMuted) {
      stopPlayback()
    }
  }, [isMuted])

  const processQueue = useCallback(async () => {
    if (isPlayingQueueRef.current || audioQueueRef.current.length === 0) {
      if (audioQueueRef.current.length === 0 && !isPlayingQueueRef.current) {
        setIsPlaying(false)
        onQueueEmptyRef.current?.()
      }
      return
    }

    isPlayingQueueRef.current = true
    setIsPlaying(true)
    const nextAudioBlob = audioQueueRef.current.shift()

    try {
      await new Promise((resolve) => {
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
        
        const handleError = () => {
          URL.revokeObjectURL(audioUrl)
          currentAudioUrlRef.current = null
          currentAudioResolveRef.current = null
          audioPlayerRef.current = null
          resolve()
        }
        
        audio.onended = handleEnded
        audio.onerror = handleError

        audio.play().catch(() => {
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
        processQueue()
      } else {
        setIsPlaying(false)
        onQueueEmptyRef.current?.()
      }
    }
  }, [])

  const queueTextToSpeech = useCallback(async (text) => {
    if (isMutedRef.current) return

    try {
      const speechAgentUrl = workspaceConfig ? getSpeechAgentUrl(workspaceConfig) : null
      const audioBlob = await textToSpeech(text, null, speechAgentUrl, workspaceId, userId)
      if (audioBlob && audioBlob.size > 0) {
        audioQueueRef.current.push(audioBlob)
        processQueue()
      }
    } catch (err) {
      console.error('Error in queueTextToSpeech:', err)
    }
  }, [workspaceConfig, workspaceId, userId, processQueue])

  const stopPlayback = useCallback(() => {
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
      currentAudioResolveRef.current()
      currentAudioResolveRef.current = null
    }
    
    if (currentAudioUrlRef.current) {
      URL.revokeObjectURL(currentAudioUrlRef.current)
      currentAudioUrlRef.current = null
    }
    
    audioQueueRef.current = []
    isPlayingQueueRef.current = false
    setIsPlaying(false)
  }, [])

  const clearQueue = useCallback(() => {
    audioQueueRef.current = []
  }, [])

  const setOnQueueEmpty = useCallback((callback) => {
    onQueueEmptyRef.current = callback
  }, [])

  useEffect(() => {
    return () => {
      stopPlayback()
    }
  }, [stopPlayback])

  return {
    isPlaying,
    isPlayingQueueRef,
    queueTextToSpeech,
    stopPlayback,
    clearQueue,
    setOnQueueEmpty,
    audioPlayerRef,
  }
}

