import { speechApiClient } from './api'

export async function transcribeAudio(audioBlob, speechAgentUrl = null, workspaceId = null, userId = null) {
  try {
    const response = await speechApiClient.transcribe(audioBlob, {
      workspaceId,
      userId,
    })
    
    const data = response.data
    if (data.status !== 'success') {
      throw new Error(data.error || 'Failed to transcribe audio')
    }
    
    return data.text
  } catch (error) {
    if (error.response) {
      throw new Error(`HTTP error! status: ${error.response.status}`)
    }
    throw error
  }
}

export async function textToSpeech(text, voice = null, speechAgentUrl = null, workspaceId = null, userId = null) {
  try {
    const response = await speechApiClient.textToSpeech(text, {
      voice,
      workspaceId,
      userId,
    })
    
    const contentType = response.headers['content-type'] || 'audio/mpeg'
    const blob = response.data
    
    if (blob.type !== contentType) {
      return new Blob([blob], { type: contentType })
    }
    
    return blob
  } catch (error) {
    if (error.response) {
      console.error('TTS API error:', error.response.status)
      throw new Error(`HTTP error! status: ${error.response.status}`)
    }
    throw error
  }
}

