import { useState, useRef, useCallback, useEffect } from 'react'

const SILENCE_THRESHOLD = 30
const SILENCE_DURATION = 2000
const MIN_AUDIO_DURATION = 500
const MIN_AUDIO_SIZE = 1000

export function useVoiceRecording({ onAudioReady, enabled = true }) {
  const [isListening, setIsListening] = useState(false)
  const [micPermissionGranted, setMicPermissionGranted] = useState(false)
  const [isRequestingMic, setIsRequestingMic] = useState(false)
  const [error, setError] = useState(null)
  
  const mediaRecorderRef = useRef(null)
  const audioChunksRef = useRef([])
  const audioContextRef = useRef(null)
  const analyserRef = useRef(null)
  const animationFrameRef = useRef(null)
  const recordingStartTimeRef = useRef(null)
  const hasDetectedVoiceRef = useRef(false)
  const micPermissionRequestedRef = useRef(false)
  const isListeningRef = useRef(isListening)

  useEffect(() => {
    isListeningRef.current = isListening
  }, [isListening])

  useEffect(() => {
    return () => {
      if (mediaRecorderRef.current?.state !== 'inactive') {
        try {
          mediaRecorderRef.current?.stop()
        } catch (err) {
          console.error('Error stopping media recorder:', err)
        }
      }
      if (audioContextRef.current?.state !== 'closed') {
        try {
          audioContextRef.current?.close()
        } catch (err) {
          console.error('Error closing audio context:', err)
        }
      }
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current)
      }
    }
  }, [])

  const requestMicrophonePermission = useCallback(async () => {
    if (micPermissionRequestedRef.current && micPermissionGranted) return true
    
    if (!navigator.mediaDevices?.getUserMedia) {
      setError('Microphone access is not supported in this browser.')
      return false
    }
    
    setIsRequestingMic(true)
    micPermissionRequestedRef.current = true
    
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
          sampleRate: 16000,
        }
      })
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
  }, [micPermissionGranted])

  const startVoiceActivityDetection = useCallback(() => {
    if (!analyserRef.current) return

    const dataArray = new Uint8Array(analyserRef.current.frequencyBinCount)
    let silenceStartTime = null
    let isActive = true
    
    const detectVoice = () => {
      if (!isActive) return
      
      analyserRef.current?.getByteFrequencyData(dataArray)
      const average = dataArray.reduce((a, b) => a + b) / dataArray.length
      
      if (average > SILENCE_THRESHOLD) {
        hasDetectedVoiceRef.current = true
        silenceStartTime = null
      } else {
        if (hasDetectedVoiceRef.current) {
          if (silenceStartTime === null) {
            silenceStartTime = Date.now()
          } else if (Date.now() - silenceStartTime > SILENCE_DURATION) {
            isActive = false
            stopListening()
            return
          }
        }
      }
      
      if (isActive) {
        animationFrameRef.current = requestAnimationFrame(detectVoice)
      }
    }
    
    detectVoice()
  }, [])

  const stopListening = useCallback(() => {
    if (mediaRecorderRef.current?.state !== 'inactive') {
      mediaRecorderRef.current?.stop()
    }
    if (audioContextRef.current?.state !== 'closed') {
      try {
        audioContextRef.current?.close()
      } catch (err) {
        console.error('Error closing audio context:', err)
      }
      audioContextRef.current = null
    }
    if (animationFrameRef.current) {
      cancelAnimationFrame(animationFrameRef.current)
      animationFrameRef.current = null
    }
    setIsListening(false)
  }, [])

  const startListening = useCallback(async () => {
    if (!enabled) return
    
    setError(null)
    
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
          sampleRate: 16000,
        }
      })
      
      audioContextRef.current = new (window.AudioContext || window.webkitAudioContext)()
      const source = audioContextRef.current.createMediaStreamSource(stream)
      analyserRef.current = audioContextRef.current.createAnalyser()
      analyserRef.current.fftSize = 2048
      source.connect(analyserRef.current)
      
      const mimeType = MediaRecorder.isTypeSupported('audio/webm') 
        ? 'audio/webm' 
        : MediaRecorder.isTypeSupported('audio/mp4')
        ? 'audio/mp4'
        : 'audio/webm'
      
      mediaRecorderRef.current = new MediaRecorder(stream, { mimeType })
      audioChunksRef.current = []
      recordingStartTimeRef.current = Date.now()
      hasDetectedVoiceRef.current = false
      
      mediaRecorderRef.current.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data)
        }
      }
      
      mediaRecorderRef.current.onstop = async () => {
        const recordingDuration = Date.now() - recordingStartTimeRef.current
        const audioBlob = new Blob(audioChunksRef.current, { type: mimeType })
        
        if (!hasDetectedVoiceRef.current) {
          audioChunksRef.current = []
          return
        }
        
        if (recordingDuration < MIN_AUDIO_DURATION || audioBlob.size < MIN_AUDIO_SIZE) {
          audioChunksRef.current = []
          return
        }
        
        onAudioReady?.(audioBlob)
        audioChunksRef.current = []
      }
      
      mediaRecorderRef.current.start(100)
      setIsListening(true)
      startVoiceActivityDetection()
      
    } catch (err) {
      console.error('Error accessing microphone:', err)
      setError('Microphone access denied. Please allow microphone access and try again.')
      setIsListening(false)
    }
  }, [enabled, onAudioReady, startVoiceActivityDetection])

  return {
    isListening,
    isListeningRef,
    micPermissionGranted,
    isRequestingMic,
    error,
    setError,
    startListening,
    stopListening,
    requestMicrophonePermission,
  }
}

