import { useState, useEffect, useCallback, useRef } from 'react';

interface WebSocketMessage {
  type: string;
  [key: string]: any;
}

interface UseWebSocketOptions {
  url?: string;
  onMessage?: (message: WebSocketMessage) => void;
  onOpen?: () => void;
  onClose?: () => void;
  onError?: (error: Event) => void;
  reconnect?: boolean;
  reconnectInterval?: number;
}

export const useWebSocket = ({
  url = 'ws://localhost:8766',
  onMessage,
  onOpen,
  onClose,
  onError,
  reconnect = true,
  reconnectInterval = 3000,
}: UseWebSocketOptions = {}) => {
  const [isConnected, setIsConnected] = useState(false);
  const [lastMessage, setLastMessage] = useState<WebSocketMessage | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  const connect = useCallback(() => {
    console.log('🔗 Intentando conectar a:', url);
    try {
      const ws = new WebSocket(url);
      
      ws.onopen = () => {
        console.log('✅ WebSocket conectado exitosamente');
        setIsConnected(true);
        if (onOpen) onOpen();
      };

      ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data) as WebSocketMessage;
          setLastMessage(message);
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
        
        // Intentar reconectar solo si no fue cierre manual
        if (reconnect && event.code !== 1000 && !reconnectTimeoutRef.current) {
          console.log(`🔄 Reintentando conexión en ${reconnectInterval}ms...`);
          reconnectTimeoutRef.current = setTimeout(() => {
            reconnectTimeoutRef.current = null;
            connect();
          }, reconnectInterval);
        }
      };

      ws.onerror = (error) => {
        console.error('❌ Error WebSocket:', error);
        console.error('❌ Estado de la conexión:', ws.readyState);
        if (onError) onError(error);
      };

      wsRef.current = ws;
    } catch (error) {
      console.error('Error conectando WebSocket:', error);
    }
  }, [url, onMessage, onOpen, onClose, onError, reconnect, reconnectInterval]);

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
  }, []);

  const sendMessage = useCallback((message: WebSocketMessage) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message));
      return true;
    }
    console.warn('WebSocket no está conectado');
    return false;
  }, []);

  // Conectar al montar
  useEffect(() => {
    const timer = setTimeout(() => {
      connect();
    }, 100); // Pequeño delay para evitar problemas de inicialización
    
    // Limpiar al desmontar
    return () => {
      clearTimeout(timer);
      disconnect();
    };
  }, []); // Eliminar dependencias circulares

  return {
    isConnected,
    lastMessage,
    sendMessage,
    connect,
    disconnect,
  };
}; 