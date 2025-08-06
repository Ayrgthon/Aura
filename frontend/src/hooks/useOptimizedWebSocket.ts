import { useState, useEffect, useCallback, useRef } from 'react';
import { useWebRTC } from './useWebRTC';

interface WebSocketMessage {
  type: string;
  [key: string]: any;
}

interface UseOptimizedWebSocketOptions {
  url?: string;
  onMessage?: (message: WebSocketMessage) => void;
  onOpen?: () => void;
  onClose?: () => void;
  onError?: (error: Event) => void;
  reconnect?: boolean;
  reconnectInterval?: number;
  useWebRTC?: boolean;
}

export const useOptimizedWebSocket = ({
  url = 'ws://localhost:8766',
  onMessage,
  onOpen,
  onClose,
  onError,
  reconnect = true,
  reconnectInterval = 1000, // Faster reconnection
  useWebRTC = true,
}: UseOptimizedWebSocketOptions = {}) => {
  const [isConnected, setIsConnected] = useState(false);
  const [lastMessage, setLastMessage] = useState<WebSocketMessage | null>(null);
  const [webRTCAvailable, setWebRTCAvailable] = useState(false);
  const [clientId, setClientId] = useState<string | null>(null);
  
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const messageQueueRef = useRef<string[]>([]);
  const connectionAttempts = useRef(0);
  
  // WebRTC integration
  const {
    isConnected: webRTCConnected,
    connectionState: webRTCState,
    isRecording,
    initializeWebRTC,
    startAudioCapture,
    stopAudioCapture,
    createOffer,
    handleAnswer,
    addIceCandidate,
    cleanup: cleanupWebRTC
  } = useWebRTC({
    onAudioData: useCallback((audioData: ArrayBuffer) => {
      // Process audio data for real-time STT if needed
      // This could be sent directly to the server for processing
    }, []),
    onConnectionStateChange: useCallback((state) => {
      console.log('WebRTC Connection State:', state);
    }, []),
    onError: useCallback((error) => {
      console.error('WebRTC Error:', error);
    }, [])
  });
  
  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.CONNECTING || wsRef.current?.readyState === WebSocket.OPEN) {
      return;
    }
    
    console.log('🔗 Conectando a servidor optimizado:', url);
    
    try {
      const ws = new WebSocket(url);
      
      ws.onopen = () => {
        console.log('✅ WebSocket conectado exitosamente');
        setIsConnected(true);
        connectionAttempts.current = 0;
        
        // Send queued messages
        while (messageQueueRef.current.length > 0) {
          const message = messageQueueRef.current.shift();
          if (message) {
            ws.send(message);
          }
        }
        
        if (onOpen) onOpen();
      };

      ws.onmessage = async (event) => {
        try {
          const message = JSON.parse(event.data) as WebSocketMessage;
          setLastMessage(message);
          
          // Handle WebRTC-specific messages
          if (message.type === 'connection') {
            setClientId(message.client_id);
            setWebRTCAvailable(message.webrtc_available || false);
            
            // Initialize WebRTC if available and requested
            if (message.webrtc_available && useWebRTC) {
              await initializeWebRTC();
            }
          } else if (message.type === 'webrtc_answer') {
            await handleAnswer({
              type: message.type as RTCSdpType,
              sdp: message.sdp
            });
          } else if (message.type === 'webrtc_ice_candidate') {
            await addIceCandidate(message.candidate);
          }
          
          if (onMessage) onMessage(message);
        } catch (error) {
          console.error('Error parseando mensaje:', error);
        }
      };

      ws.onclose = (event) => {
        console.log('❌ WebSocket desconectado:', event.code, event.reason);
        setIsConnected(false);
        wsRef.current = null;
        
        if (onClose) onClose();
        
        // Exponential backoff for reconnection
        if (reconnect && event.code !== 1000 && !reconnectTimeoutRef.current) {
          connectionAttempts.current += 1;
          const delay = Math.min(reconnectInterval * Math.pow(2, connectionAttempts.current - 1), 30000);
          
          console.log(`🔄 Reintentando conexión en ${delay}ms... (intento ${connectionAttempts.current})`);
          reconnectTimeoutRef.current = setTimeout(() => {
            reconnectTimeoutRef.current = null;
            connect();
          }, delay);
        }
      };

      ws.onerror = (error) => {
        console.error('❌ Error WebSocket:', error);
        if (onError) onError(error);
      };

      wsRef.current = ws;
    } catch (error) {
      console.error('Error conectando WebSocket:', error);
    }
  }, [url, onMessage, onOpen, onClose, onError, reconnect, reconnectInterval, useWebRTC, initializeWebRTC, handleAnswer, addIceCandidate]);

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    
    cleanupWebRTC();
    
    if (wsRef.current) {
      wsRef.current.close(1000, 'Manual disconnect');
      wsRef.current = null;
    }
    
    connectionAttempts.current = 0;
  }, [cleanupWebRTC]);

  const sendMessage = useCallback((message: WebSocketMessage) => {
    const messageStr = JSON.stringify(message);
    
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(messageStr);
      return true;
    } else {
      // Queue message for when connection is restored
      messageQueueRef.current.push(messageStr);
      console.warn('WebSocket no conectado, mensaje encolado');
      return false;
    }
  }, []);
  
  const sendOptimizedMessage = useCallback((type: string, data: any = {}) => {
    return sendMessage({ type, ...data, timestamp: Date.now() });
  }, [sendMessage]);
  
  const initializeWebRTCConnection = useCallback(async () => {
    if (!webRTCAvailable || !clientId) {
      return false;
    }
    
    try {
      const offer = await createOffer();
      if (offer) {
        sendOptimizedMessage('webrtc_offer', { offer });
        return true;
      }
    } catch (error) {
      console.error('Error initializing WebRTC connection:', error);
    }
    
    return false;
  }, [webRTCAvailable, clientId, createOffer, sendOptimizedMessage]);
  
  const startOptimizedListening = useCallback(async () => {
    // Start WebRTC audio if available, otherwise fallback to WebSocket
    if (webRTCAvailable && webRTCConnected) {
      const success = await startAudioCapture();
      if (success) {
        sendOptimizedMessage('start_listening_webrtc');
        return true;
      }
    }
    
    // Fallback to WebSocket-based listening
    return sendOptimizedMessage('start_listening');
  }, [webRTCAvailable, webRTCConnected, startAudioCapture, sendOptimizedMessage]);
  
  const stopOptimizedListening = useCallback(() => {
    if (isRecording) {
      stopAudioCapture();
    }
    
    return sendOptimizedMessage('stop_listening');
  }, [isRecording, stopAudioCapture, sendOptimizedMessage]);

  // Connect on mount
  useEffect(() => {
    const timer = setTimeout(connect, 100);
    
    return () => {
      clearTimeout(timer);
      disconnect();
    };
  }, [connect, disconnect]);

  return {
    // WebSocket state
    isConnected,
    lastMessage,
    clientId,
    
    // WebRTC state
    webRTCAvailable,
    webRTCConnected,
    webRTCState,
    isRecording,
    
    // Connection methods
    connect,
    disconnect,
    sendMessage,
    sendOptimizedMessage,
    
    // WebRTC methods
    initializeWebRTCConnection,
    startOptimizedListening,
    stopOptimizedListening,
    
    // Legacy methods for compatibility
    sendMessage: sendOptimizedMessage,
  };
};