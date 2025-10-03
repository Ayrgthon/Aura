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
