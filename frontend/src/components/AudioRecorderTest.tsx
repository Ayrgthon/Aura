import React, { useState } from 'react';
import { useAudioRecorder } from '@/hooks/useAudioRecorder';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Mic, Square, Play, Pause, Trash2, Upload } from 'lucide-react';
import { uploadAudioToApi, checkApiHealth } from '@/utils/audioApi';

const AudioRecorderTest = () => {
  const [isUploading, setIsUploading] = useState(false);
  const [uploadSuccess, setUploadSuccess] = useState(false);
  const [transcription, setTranscription] = useState<string | null>(null);

  const {
    isRecording,
    isPaused,
    recordedBlob,
    audioFormat,
    error,
    startRecording,
    stopRecording,
    pauseRecording,
    resumeRecording,
    clearRecording
  } = useAudioRecorder({
    onRecordingComplete: (blob, mimeType) => {
      console.log('✅ Grabación completada!');
      console.log('Tamaño:', blob.size, 'bytes');
      console.log('Tipo MIME:', mimeType);
      setUploadSuccess(false);
      setTranscription(null);
    },
    onError: (errorMsg) => {
      console.error('❌ Error:', errorMsg);
    }
  });

  const handleStartStop = async () => {
    if (isRecording) {
      stopRecording();
    } else {
      await startRecording();
    }
  };

  const handlePlayback = () => {
    if (recordedBlob) {
      const audioUrl = URL.createObjectURL(recordedBlob);
      const audio = new Audio(audioUrl);
      audio.play();

      // Limpiar URL cuando termine
      audio.onended = () => {
        URL.revokeObjectURL(audioUrl);
      };
    }
  };

  const handleDownload = () => {
    if (recordedBlob) {
      const url = URL.createObjectURL(recordedBlob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `recording-${Date.now()}.${audioFormat?.split('/')[1].split(';')[0] || 'webm'}`;
      a.click();
      URL.revokeObjectURL(url);
    }
  };

  const handleUploadToApi = async () => {
    if (!recordedBlob) return;

    try {
      setIsUploading(true);
      const result = await uploadAudioToApi(recordedBlob);
      console.log('✅ Subida exitosa:', result);
      setUploadSuccess(true);
      setTranscription(result.transcription);
    } catch (error) {
      console.error('❌ Error subiendo audio:', error);
      alert('Error subiendo el audio. Asegúrate de que la API esté corriendo en http://localhost:8001');
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="min-h-screen bg-background flex items-center justify-center p-8">
      <Card className="p-6 w-full max-w-md">
        <h2 className="text-2xl font-bold mb-4">Audio Recorder Test</h2>

        {/* Estado */}
        <div className="mb-4 p-3 bg-muted rounded">
          <div className="text-sm space-y-1">
            <div>Estado: {isRecording ? (isPaused ? '⏸️ Pausado' : '🎙️ Grabando') : '⏹️ Detenido'}</div>
            <div>Formato: {audioFormat || 'N/A'}</div>
            {recordedBlob && (
              <div>Audio grabado: {(recordedBlob.size / 1024).toFixed(2)} KB</div>
            )}
          </div>
        </div>

        {/* Error */}
        {error && (
          <div className="mb-4 p-3 bg-destructive/10 text-destructive rounded">
            ❌ {error}
          </div>
        )}

        {/* Controles de grabación */}
        <div className="flex gap-2 mb-4">
          <Button
            onClick={handleStartStop}
            variant={isRecording ? 'destructive' : 'default'}
            className="flex-1"
          >
            {isRecording ? (
              <>
                <Square className="w-4 h-4 mr-2" />
                Detener
              </>
            ) : (
              <>
                <Mic className="w-4 h-4 mr-2" />
                Grabar
              </>
            )}
          </Button>

          {isRecording && (
            <Button
              onClick={isPaused ? resumeRecording : pauseRecording}
              variant="outline"
            >
              {isPaused ? (
                <Play className="w-4 h-4" />
              ) : (
                <Pause className="w-4 h-4" />
              )}
            </Button>
          )}
        </div>

        {/* Controles de reproducción */}
        {recordedBlob && !isRecording && (
          <>
            <div className="flex gap-2 mb-2">
              <Button onClick={handlePlayback} variant="outline" className="flex-1">
                <Play className="w-4 h-4 mr-2" />
                Reproducir
              </Button>
              <Button onClick={handleDownload} variant="outline" className="flex-1">
                Descargar
              </Button>
              <Button onClick={clearRecording} variant="outline">
                <Trash2 className="w-4 h-4" />
              </Button>
            </div>

            {/* Botón para subir a la API */}
            <Button
              onClick={handleUploadToApi}
              disabled={isUploading}
              className="w-full"
              variant={uploadSuccess ? "default" : "secondary"}
            >
              <Upload className="w-4 h-4 mr-2" />
              {isUploading ? 'Subiendo...' : uploadSuccess ? '✅ Subido a la API' : 'Subir a la API'}
            </Button>

            {/* Mostrar transcripción */}
            {transcription && (
              <div className="mt-4 p-3 bg-blue-500/10 border border-blue-500/30 rounded">
                <div className="text-sm font-medium text-blue-400 mb-2">
                  📝 Transcripción (Vosk):
                </div>
                <div className="text-sm text-white/90">
                  {transcription}
                </div>
              </div>
            )}
          </>
        )}

        {/* Información */}
        <div className="mt-6 p-3 bg-muted rounded text-xs text-muted-foreground">
          <p className="mb-2">💡 Instrucciones:</p>
          <ul className="list-disc list-inside space-y-1">
            <li>Click en "Grabar" para iniciar</li>
            <li>Click en "Detener" para finalizar</li>
            <li>Usa pausa/reanudar durante la grabación</li>
            <li>Reproduce o descarga el audio grabado</li>
            <li>Sube el audio a la API (puerto 8001)</li>
          </ul>
          <p className="mt-2 text-yellow-600">
            ⚠️ Asegúrate de iniciar la API con: <code>python blueprint/audio_api.py</code> (Puerto 8001)
          </p>
        </div>
      </Card>
    </div>
  );
};

export default AudioRecorderTest;
