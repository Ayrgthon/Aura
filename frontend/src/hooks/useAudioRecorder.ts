import { useState, useRef, useCallback, useEffect } from 'react';

interface UseAudioRecorderOptions {
  onRecordingComplete?: (audioBlob: Blob, mimeType: string) => void;
  onError?: (error: string) => void;
}

interface UseAudioRecorderReturn {
  isRecording: boolean;
  isPaused: boolean;
  recordedBlob: Blob | null;
  audioFormat: string | null;
  error: string | null;
  startRecording: () => Promise<boolean>;
  stopRecording: () => void;
  pauseRecording: () => void;
  resumeRecording: () => void;
  clearRecording: () => void;
  getAudioBlob: () => Blob | null;
}

// Formatos de audio en orden de preferencia (mejor compresión y compatibilidad)
const AUDIO_FORMATS = [
  'audio/webm;codecs=opus',
  'audio/webm',
  'audio/ogg;codecs=opus',
  'audio/mp4',
  'audio/wav'
];

// Detectar el mejor formato soportado por el navegador
const detectSupportedFormat = (): string | null => {
  for (const format of AUDIO_FORMATS) {
    if (MediaRecorder.isTypeSupported(format)) {
      console.log(`✅ Formato soportado detectado: ${format}`);
      return format;
    }
  }
  console.warn('⚠️ No se encontró ningún formato de audio soportado');
  return null;
};

export const useAudioRecorder = ({
  onRecordingComplete,
  onError
}: UseAudioRecorderOptions = {}): UseAudioRecorderReturn => {
  const [isRecording, setIsRecording] = useState(false);
  const [isPaused, setIsPaused] = useState(false);
  const [recordedBlob, setRecordedBlob] = useState<Blob | null>(null);
  const [audioFormat, setAudioFormat] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const chunksRef = useRef<Blob[]>([]);

  // Limpiar recursos del micrófono
  const cleanupMediaStream = useCallback(() => {
    if (mediaStreamRef.current) {
      mediaStreamRef.current.getTracks().forEach(track => {
        track.stop();
        console.log('🛑 Track de audio detenido y recursos liberados');
      });
      mediaStreamRef.current = null;
    }
  }, []);

  // Iniciar grabación
  const startRecording = useCallback(async (): Promise<boolean> => {
    try {
      // Limpiar error previo
      setError(null);

      // Detectar formato soportado
      const supportedFormat = detectSupportedFormat();
      if (!supportedFormat) {
        const errorMsg = 'El navegador no soporta grabación de audio';
        setError(errorMsg);
        onError?.(errorMsg);
        return false;
      }

      // Solicitar permiso de micrófono
      console.log('🎤 Solicitando permiso de micrófono...');
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
          channelCount: 1
        }
      });

      console.log('✅ Permiso de micrófono concedido');
      mediaStreamRef.current = stream;
      setAudioFormat(supportedFormat);

      // Crear MediaRecorder
      console.log(`📝 Creando MediaRecorder con formato: ${supportedFormat}`);
      const mediaRecorder = new MediaRecorder(stream, {
        mimeType: supportedFormat
      });

      console.log(`📊 MediaRecorder state: ${mediaRecorder.state}`);
      mediaRecorderRef.current = mediaRecorder;
      chunksRef.current = [];

      // Evento: cuando hay datos disponibles
      mediaRecorder.ondataavailable = (event) => {
        console.log(`📦 ondataavailable disparado, size: ${event.data?.size || 0}`);
        if (event.data && event.data.size > 0) {
          chunksRef.current.push(event.data);
          console.log(`✅ Chunk agregado: ${event.data.size} bytes. Total chunks: ${chunksRef.current.length}`);
        }
      };

      // Evento: cuando se detiene la grabación
      mediaRecorder.onstop = () => {
        console.log('🛑 onstop disparado! Total de chunks acumulados:', chunksRef.current.length);
        const blob = new Blob(chunksRef.current, { type: supportedFormat });
        console.log(`✅ Blob generado: ${blob.size} bytes, tipo: ${blob.type}`);

        setRecordedBlob(blob);
        setIsRecording(false);
        setIsPaused(false);

        onRecordingComplete?.(blob, supportedFormat);

        // Limpiar stream
        cleanupMediaStream();
      };

      // Evento: cuando inicia la grabación
      mediaRecorder.onstart = () => {
        console.log('▶️ onstart disparado! Grabación iniciada exitosamente');
      };

      // Evento: error durante la grabación
      mediaRecorder.onerror = (event: Event) => {
        const errorMsg = `Error durante la grabación: ${event}`;
        console.error('❌ onerror disparado:', errorMsg, event);
        setError(errorMsg);
        onError?.(errorMsg);
        setIsRecording(false);
        cleanupMediaStream();
      };

      // Iniciar grabación
      console.log('🚀 Llamando a mediaRecorder.start(1000)...');
      mediaRecorder.start(1000); // Generar chunks cada 1 segundo
      setIsRecording(true);
      console.log(`🎙️ Estado después de start(): ${mediaRecorder.state}`);

      return true;
    } catch (err) {
      let errorMsg = 'Error desconocido al iniciar grabación';

      if (err instanceof Error) {
        if (err.name === 'NotAllowedError') {
          errorMsg = 'Permiso de micrófono denegado';
        } else if (err.name === 'NotFoundError') {
          errorMsg = 'No se encontró ningún micrófono';
        } else if (err.name === 'NotReadableError') {
          errorMsg = 'El micrófono está siendo usado por otra aplicación';
        } else {
          errorMsg = `Error: ${err.message}`;
        }
      }

      console.error('❌', errorMsg, err);
      setError(errorMsg);
      onError?.(errorMsg);
      cleanupMediaStream();

      return false;
    }
  }, [onRecordingComplete, onError, cleanupMediaStream]);

  // Detener grabación
  const stopRecording = useCallback(() => {
    if (mediaRecorderRef.current && isRecording) {
      console.log('🛑 Deteniendo grabación...');
      mediaRecorderRef.current.stop();
    }
  }, [isRecording]);

  // Pausar grabación
  const pauseRecording = useCallback(() => {
    if (mediaRecorderRef.current && isRecording && !isPaused) {
      console.log('⏸️ Pausando grabación...');
      mediaRecorderRef.current.pause();
      setIsPaused(true);
    }
  }, [isRecording, isPaused]);

  // Reanudar grabación
  const resumeRecording = useCallback(() => {
    if (mediaRecorderRef.current && isRecording && isPaused) {
      console.log('▶️ Reanudando grabación...');
      mediaRecorderRef.current.resume();
      setIsPaused(false);
    }
  }, [isRecording, isPaused]);

  // Limpiar grabación
  const clearRecording = useCallback(() => {
    setRecordedBlob(null);
    chunksRef.current = [];
    setError(null);
    console.log('🗑️ Grabación limpiada');
  }, []);

  // Obtener Blob de audio
  const getAudioBlob = useCallback((): Blob | null => {
    return recordedBlob;
  }, [recordedBlob]);

  // Cleanup al desmontar - solo se ejecuta cuando el componente se desmonta
  useEffect(() => {
    return () => {
      console.log('🧹 Componente desmontado, ejecutando cleanup...');
      if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
        mediaRecorderRef.current.stop();
      }
      if (mediaStreamRef.current) {
        mediaStreamRef.current.getTracks().forEach(track => {
          track.stop();
          console.log('🛑 Track de audio detenido en cleanup');
        });
      }
    };
  }, []); // Sin dependencias para que solo se ejecute al desmontar

  return {
    isRecording,
    isPaused,
    recordedBlob,
    audioFormat,
    error,
    startRecording,
    stopRecording,
    pauseRecording,
    resumeRecording,
    clearRecording,
    getAudioBlob
  };
};
