export class VoiceWebSocket {
  constructor() {
    this._ws = null
    this._callbacks = {}
    this._reconnectAttempts = 0
    this._maxReconnectAttempts = 3
    this._config = null
  }

  connect(url, config) {
    this._config = config
    this._reconnectAttempts = 0

    return new Promise((resolve, reject) => {
      try {
        this._ws = new WebSocket(url)

        this._ws.onopen = () => {
          this._reconnectAttempts = 0
          this._ws.send(JSON.stringify({ type: 'config', ...config }))
        }

        this._ws.onmessage = (event) => {
          try {
            const msg = JSON.parse(event.data)
            this._handleMessage(msg, resolve)
          } catch (e) {
            console.error('[VoiceWS] Failed to parse message:', e)
          }
        }

        this._ws.onerror = (error) => {
          console.error('[VoiceWS] WebSocket error:', error)
          this._fire('error', { message: 'WebSocket connection error' })
          reject(error)
        }

        this._ws.onclose = (event) => {
          this._fire('close', { code: event.code, reason: event.reason })
        }
      } catch (e) {
        reject(e)
      }
    })
  }

  _handleMessage(msg, resolveConnect) {
    switch (msg.type) {
      case 'ready':
        if (resolveConnect) resolveConnect(this)
        break
      case 'transcript':
        this._fire('transcript', msg)
        break
      case 'text_chunk':
        this._fire('textChunk', msg)
        break
      case 'audio_chunk':
        this._fire('audioChunk', msg)
        break
      case 'text_done':
        this._fire('textDone', msg)
        break
      case 'audio_done':
        this._fire('audioDone', msg)
        break
      case 'error':
        this._fire('error', msg)
        break
      default:
        break
    }
  }

  sendAudioChunk(pcmBase64) {
    this._send({ type: 'audio_chunk', data: pcmBase64 })
  }

  sendSpeechEnd() {
    this._send({ type: 'speech_end' })
  }

  sendTextMessage(content, sessionId) {
    this._send({ type: 'text_message', content, session_id: sessionId })
  }

  stopAudio() {
    this._send({ type: 'stop_audio' })
  }

  disconnect() {
    if (this._ws) {
      try {
        this._ws.close(1000, 'client disconnect')
      } catch (e) {
        // ignore
      }
      this._ws = null
    }
    this._callbacks = {}
  }

  get isConnected() {
    return this._ws && this._ws.readyState === WebSocket.OPEN
  }

  on(event, callback) {
    if (!this._callbacks[event]) this._callbacks[event] = []
    this._callbacks[event].push(callback)
    return () => {
      this._callbacks[event] = this._callbacks[event].filter(cb => cb !== callback)
    }
  }

  onTranscript(cb) { return this.on('transcript', cb) }
  onTextChunk(cb) { return this.on('textChunk', cb) }
  onAudioChunk(cb) { return this.on('audioChunk', cb) }
  onTextDone(cb) { return this.on('textDone', cb) }
  onAudioDone(cb) { return this.on('audioDone', cb) }
  onError(cb) { return this.on('error', cb) }

  _fire(event, data) {
    const cbs = this._callbacks[event]
    if (cbs) cbs.forEach(cb => cb(data))
  }

  _send(data) {
    if (this._ws && this._ws.readyState === WebSocket.OPEN) {
      this._ws.send(JSON.stringify(data))
    }
  }
}

export function float32ToBase64PCM16(float32Array) {
  const pcm16 = new Int16Array(float32Array.length)
  for (let i = 0; i < float32Array.length; i++) {
    const s = Math.max(-1, Math.min(1, float32Array[i]))
    pcm16[i] = s < 0 ? s * 0x8000 : s * 0x7FFF
  }
  const bytes = new Uint8Array(pcm16.buffer)
  let binary = ''
  for (let i = 0; i < bytes.length; i++) {
    binary += String.fromCharCode(bytes[i])
  }
  return btoa(binary)
}

export function base64ToAudioBlob(base64, mimeType = 'audio/mpeg') {
  const binary = atob(base64)
  const bytes = new Uint8Array(binary.length)
  for (let i = 0; i < binary.length; i++) {
    bytes[i] = binary.charCodeAt(i)
  }
  return new Blob([bytes], { type: mimeType })
}
