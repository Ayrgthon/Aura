import { useState, useEffect, useRef, useCallback } from 'react';

interface UseWebRTCOptions {
  onAudioData?: (audioData: ArrayBuffer) => void;
  onConnectionStateChange?: (state: RTCPeerConnectionState) => void;
  onError?: (error: string) => void;
}

export const useWebRTC = ({
  onAudioData,
  onConnectionStateChange,
  onError
}: UseWebRTCOptions = {}) => {
  const [isConnected, setIsConnected] = useState(false);
  const [connectionState, setConnectionState] = useState<RTCPeerConnectionState>('new');
  const [isRecording, setIsRecording] = useState(false);
  
  const peerConnectionRef = useRef<RTCPeerConnection | null>(null);
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const processorRef = useRef<ScriptProcessorNode | null>(null);
  
  const initializeWebRTC = useCallback(async () => {
    try {
      // Create peer connection
      const pc = new RTCPeerConnection({
        iceServers: [{ urls: 'stun:stun.l.google.com:19302' }]
      });
      
      peerConnectionRef.current = pc;
      
      // Handle connection state changes
      pc.onconnectionstatechange = () => {
        const state = pc.connectionState;
        setConnectionState(state);
        setIsConnected(state === 'connected');
        onConnectionStateChange?.(state);
      };
      
      // Handle ICE candidates
      pc.onicecandidate = (event) => {
        if (event.candidate) {
          // Send ICE candidate to server via WebSocket
          // This will be handled by the parent component
        }
      };
      
      return pc;
    } catch (error) {
      const errorMsg = `Error initializing WebRTC: ${error}`;
      console.error(errorMsg);
      onError?.(errorMsg);
      return null;
    }
  }, [onConnectionStateChange, onError]);
  
  const startAudioCapture = useCallback(async () => {
    try {
      // Get user media
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
          sampleRate: 16000,
          channelCount: 1
        }
      });
      
      mediaStreamRef.current = stream;
      
      // Create audio context for processing
      const audioContext = new AudioContext({ sampleRate: 16000 });
      audioContextRef.current = audioContext;
      
      const source = audioContext.createMediaStreamSource(stream);
      const processor = audioContext.createScriptProcessor(4096, 1, 1);
      
      processorRef.current = processor;
      
      // Process audio data
      processor.onaudioprocess = (event) => {
        if (onAudioData && isRecording) {
          const inputBuffer = event.inputBuffer;
          const inputData = inputBuffer.getChannelData(0);
          
          // Convert to ArrayBuffer
          const buffer = new ArrayBuffer(inputData.length * 2);
          const view = new Int16Array(buffer);
          
          for (let i = 0; i < inputData.length; i++) {
            view[i] = Math.max(-32768, Math.min(32767, inputData[i] * 32768));
          }
          
          onAudioData(buffer);
        }
      };
      
      source.connect(processor);
      processor.connect(audioContext.destination);
      
      // Add tracks to peer connection
      if (peerConnectionRef.current) {
        stream.getTracks().forEach(track => {
          peerConnectionRef.current?.addTrack(track, stream);
        });
      }
      
      setIsRecording(true);
      return true;
    } catch (error) {
      const errorMsg = `Error starting audio capture: ${error}`;
      console.error(errorMsg);
      onError?.(errorMsg);
      return false;
    }
  }, [onAudioData, isRecording, onError]);
  
  const stopAudioCapture = useCallback(() => {
    try {
      // Stop media stream
      if (mediaStreamRef.current) {
        mediaStreamRef.current.getTracks().forEach(track => track.stop());
        mediaStreamRef.current = null;
      }
      
      // Disconnect audio processing
      if (processorRef.current) {
        processorRef.current.disconnect();
        processorRef.current = null;
      }
      
      // Close audio context
      if (audioContextRef.current) {
        audioContextRef.current.close();
        audioContextRef.current = null;
      }
      
      setIsRecording(false);
      return true;
    } catch (error) {
      const errorMsg = `Error stopping audio capture: ${error}`;
      console.error(errorMsg);
      onError?.(errorMsg);
      return false;
    }
  }, [onError]);
  
  const createOffer = useCallback(async () => {
    if (!peerConnectionRef.current) {
      return null;
    }
    
    try {
      const offer = await peerConnectionRef.current.createOffer();
      await peerConnectionRef.current.setLocalDescription(offer);
      return offer;
    } catch (error) {
      const errorMsg = `Error creating offer: ${error}`;
      console.error(errorMsg);
      onError?.(errorMsg);
      return null;
    }
  }, [onError]);
  
  const handleAnswer = useCallback(async (answer: RTCSessionDescriptionInit) => {
    if (!peerConnectionRef.current) {
      return false;
    }
    
    try {
      await peerConnectionRef.current.setRemoteDescription(answer);
      return true;
    } catch (error) {
      const errorMsg = `Error handling answer: ${error}`;
      console.error(errorMsg);
      onError?.(errorMsg);
      return false;
    }
  }, [onError]);
  
  const addIceCandidate = useCallback(async (candidate: RTCIceCandidateInit) => {
    if (!peerConnectionRef.current) {
      return false;
    }
    
    try {
      await peerConnectionRef.current.addIceCandidate(candidate);
      return true;
    } catch (error) {
      const errorMsg = `Error adding ICE candidate: ${error}`;
      console.error(errorMsg);
      onError?.(errorMsg);
      return false;
    }
  }, [onError]);
  
  const cleanup = useCallback(() => {
    stopAudioCapture();
    
    if (peerConnectionRef.current) {
      peerConnectionRef.current.close();
      peerConnectionRef.current = null;
    }
    
    setIsConnected(false);
    setConnectionState('closed');
  }, [stopAudioCapture]);
  
  // Cleanup on unmount
  useEffect(() => {
    return () => {
      cleanup();
    };
  }, [cleanup]);
  
  return {
    isConnected,
    connectionState,
    isRecording,
    initializeWebRTC,
    startAudioCapture,
    stopAudioCapture,
    createOffer,
    handleAnswer,
    addIceCandidate,
    cleanup
  };
};