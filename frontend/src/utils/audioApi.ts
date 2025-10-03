/**
 * Utilidad para enviar audio grabado a la REST API
 */

export interface UploadAudioResponse {
  success: boolean;
  message: string;
  file: {
    filename: string;
    size: number;
    size_kb: number;
    content_type: string;
    saved_path: string;
    timestamp: string;
  };
  transcription: string | null;
}

export interface ProcessAudioResponse {
  success: boolean;
  message: string;
  transcription: string;
  gemini_response: string;
  audio_base64: string;
  audio_format: string;
  processing_time: string;
}

/**
 * Envía un Blob de audio a la REST API
 *
 * @param audioBlob - Blob de audio a enviar
 * @param apiUrl - URL de la API (default: http://localhost:8001)
 * @returns Promise con la respuesta de la API
 */
export async function uploadAudioToApi(
  audioBlob: Blob,
  apiUrl: string = 'http://localhost:8001'
): Promise<UploadAudioResponse> {
  try {
    console.log('📤 Enviando audio a la API...');
    console.log('📊 Tamaño:', audioBlob.size, 'bytes');
    console.log('📊 Tipo:', audioBlob.type);

    // Crear FormData con el audio
    const formData = new FormData();
    formData.append('audio', audioBlob, `recording-${Date.now()}.webm`);

    // Enviar a la API
    const response = await fetch(`${apiUrl}/upload-audio`, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const data: UploadAudioResponse = await response.json();
    console.log('✅ Audio enviado exitosamente:', data);

    return data;
  } catch (error) {
    console.error('❌ Error enviando audio:', error);
    throw error;
  }
}

/**
 * Procesa audio completo: transcripción + Gemini + TTS
 *
 * @param audioBlob - Blob de audio a enviar
 * @param apiUrl - URL de la API (default: http://localhost:8001)
 * @returns Promise con transcripción, respuesta y audio en base64
 */
export async function processAudioComplete(
  audioBlob: Blob,
  apiUrl: string = 'http://localhost:8001'
): Promise<ProcessAudioResponse> {
  try {
    console.log('🚀 Enviando audio para procesamiento completo...');
    console.log('📊 Tamaño:', audioBlob.size, 'bytes');
    console.log('📊 Tipo:', audioBlob.type);

    // Crear FormData con el audio
    const formData = new FormData();
    formData.append('audio', audioBlob, `recording-${Date.now()}.webm`);

    // Enviar a la API
    const response = await fetch(`${apiUrl}/process-audio`, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const data: ProcessAudioResponse = await response.json();
    console.log('✅ Procesamiento completo exitoso');
    console.log('📝 Transcripción:', data.transcription);
    console.log('🤖 Respuesta Gemini:', data.gemini_response);
    console.log('🔊 Audio base64 recibido:', data.audio_base64.length, 'caracteres');

    return data;
  } catch (error) {
    console.error('❌ Error procesando audio:', error);
    throw error;
  }
}

/**
 * Reproduce audio desde base64
 *
 * @param audioBase64 - String base64 del audio
 * @param format - Formato del audio (mp3, wav, etc.)
 */
export function playAudioFromBase64(audioBase64: string, format: string = 'mp3'): void {
  try {
    console.log('🔊 Reproduciendo audio desde base64...');

    // Decodificar base64 a binary
    const binaryString = atob(audioBase64);
    const bytes = new Uint8Array(binaryString.length);
    for (let i = 0; i < binaryString.length; i++) {
      bytes[i] = binaryString.charCodeAt(i);
    }

    // Crear Blob
    const blob = new Blob([bytes], { type: `audio/${format}` });

    // Crear URL y reproducir
    const audioUrl = URL.createObjectURL(blob);
    const audio = new Audio(audioUrl);

    audio.play();

    // Limpiar URL cuando termine
    audio.onended = () => {
      URL.revokeObjectURL(audioUrl);
      console.log('✅ Reproducción completada');
    };

    audio.onerror = (error) => {
      console.error('❌ Error reproduciendo audio:', error);
      URL.revokeObjectURL(audioUrl);
    };

  } catch (error) {
    console.error('❌ Error decodificando/reproduciendo audio:', error);
  }
}

/**
 * Verifica si la API está disponible
 *
 * @param apiUrl - URL de la API (default: http://localhost:8001)
 * @returns Promise<boolean> - true si la API está disponible
 */
export async function checkApiHealth(
  apiUrl: string = 'http://localhost:8001'
): Promise<boolean> {
  try {
    const response = await fetch(`${apiUrl}/health`);
    return response.ok;
  } catch (error) {
    console.error('❌ API no disponible:', error);
    return false;
  }
}
