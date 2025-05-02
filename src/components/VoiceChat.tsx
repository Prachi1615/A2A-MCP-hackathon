import React, { useState, useRef, useEffect } from 'react';
import { 
  Box, 
  Button, 
  TextField, 
  Select, 
  MenuItem, 
  FormControl, 
  InputLabel, 
  Alert, 
  Typography,
  Paper,
  CircularProgress,
  IconButton,
  Tooltip,
  Avatar,
  List,
  ListItem,
  ListItemText,
  ListItemAvatar,
  Divider
} from '@mui/material';
import MicIcon from '@mui/icons-material/Mic';
import MicOffIcon from '@mui/icons-material/MicOff';
import VolumeUpIcon from '@mui/icons-material/VolumeUp';
import VolumeOffIcon from '@mui/icons-material/VolumeOff';
import WifiIcon from '@mui/icons-material/Wifi';
import WifiOffIcon from '@mui/icons-material/WifiOff';

interface Message {
  text: string;
  sender: 'user' | 'assistant';
  timestamp: Date;
}

interface VoiceChatProps {
  apiKey: string;
}

const VoiceChat: React.FC<VoiceChatProps> = ({ apiKey }) => {
  const [isRecording, setIsRecording] = useState(false);
  const [isMuted, setIsMuted] = useState(false);
  const [selectedVoice, setSelectedVoice] = useState('Puck');
  const [error, setError] = useState<string | null>(null);
  const [rtcConfig, setRtcConfig] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputLevel, setInputLevel] = useState(0);
  const [outputLevel, setOutputLevel] = useState(0);
  const [isConnected, setIsConnected] = useState(false);
  const [isListening, setIsListening] = useState(false);

  const peerConnectionRef = useRef<RTCPeerConnection | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const dataChannelRef = useRef<RTCDataChannel | null>(null);
  const webrtcIdRef = useRef<string>('');
  const analyserInputRef = useRef<AnalyserNode | null>(null);
  const analyserOutputRef = useRef<AnalyserNode | null>(null);
  const sourceInputRef = useRef<MediaStreamAudioSourceNode | null>(null);
  const sourceOutputRef = useRef<MediaStreamAudioSourceNode | null>(null);

  const voices = ['Puck', 'Charon', 'Kore', 'Fenrir', 'Aoede'];
  const apiUrl = process.env.REACT_APP_API_URL || 'http://localhost:8000';
  useEffect(() => {
    // Fetch RTC configuration from backend
    const fetchRTCConfig = async () => {
      try {
        setIsLoading(true);
        setError(null);
        console.log("Fetching RTC configuration from backend...");
        const response = await fetch(`${apiUrl}/`);
        console.log("Response status:", response.status);
        
        if (!response.ok) {
          const errorData = await response.json().catch(() => ({ detail: 'Failed to parse error response' }));
          console.error("Error response:", errorData);
          throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        console.log("Received RTC configuration:", data);
        setRtcConfig(data.rtc_config);
      } catch (err) {
        console.error("Error fetching RTC configuration:", err);
        setError(err instanceof Error ? err.message : 'Failed to fetch RTC configuration. Please try again later.');
      } finally {
        setIsLoading(false);
      }
    };

    fetchRTCConfig();

    return () => {
      stopWebRTC();
    };
  }, []);

  useEffect(() => {
    // Animation frame for audio visualization
    let animationFrameId: number;
    
    const updateAudioLevels = () => {
      if (analyserInputRef.current && isRecording) {
        const dataArray = new Uint8Array(analyserInputRef.current.frequencyBinCount);
        analyserInputRef.current.getByteFrequencyData(dataArray);
        const average = dataArray.reduce((a, b) => a + b) / dataArray.length;
        setInputLevel(average / 255);
      }
      
      if (analyserOutputRef.current && isConnected) {
        const dataArray = new Uint8Array(analyserOutputRef.current.frequencyBinCount);
        analyserOutputRef.current.getByteFrequencyData(dataArray);
        const average = dataArray.reduce((a, b) => a + b) / dataArray.length;
        setOutputLevel(average / 255);
      }
      
      animationFrameId = requestAnimationFrame(updateAudioLevels);
    };

    if (isRecording || isConnected) {
      updateAudioLevels();
    }

    return () => {
      if (animationFrameId) {
        cancelAnimationFrame(animationFrameId);
      }
    };
  }, [isRecording, isConnected]);

  const setupWebRTC = async () => {
    if (!apiKey) {
      setError('Please provide a valid Gemini API key in your .env file');
      return;
    }

    try {
      setIsLoading(true);
      setError(null);
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      webrtcIdRef.current = Math.random().toString(36).substring(7);

      const config = rtcConfig || {};
      peerConnectionRef.current = new RTCPeerConnection(config);

      // Add audio tracks to peer connection
      stream.getTracks().forEach(track => {
        peerConnectionRef.current?.addTrack(track, stream);
      });

      // Set up audio context and analysers
      audioContextRef.current = new AudioContext();
      sourceInputRef.current = audioContextRef.current.createMediaStreamSource(stream);
      analyserInputRef.current = audioContextRef.current.createAnalyser();
      sourceInputRef.current.connect(analyserInputRef.current);
      analyserInputRef.current.fftSize = 64;

      // Set up data channel
      dataChannelRef.current = peerConnectionRef.current.createDataChannel('text');
      dataChannelRef.current.onmessage = handleDataChannelMessage;

      // Set up event handlers
      peerConnectionRef.current.onicecandidate = handleIceCandidate;
      peerConnectionRef.current.ontrack = handleTrack;
      peerConnectionRef.current.onconnectionstatechange = handleConnectionStateChange;

      // Create and send offer
      const offer = await peerConnectionRef.current.createOffer();
      await peerConnectionRef.current.setLocalDescription(offer);
      const response = await fetch(`${apiUrl}/webrtc/offer`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          sdp: peerConnectionRef.current.localDescription?.sdp,
          type: peerConnectionRef.current.localDescription?.type,
          webrtc_id: webrtcIdRef.current,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to establish WebRTC connection');
      }

      const serverResponse = await response.json();
      await peerConnectionRef.current.setRemoteDescription(serverResponse);

      setIsRecording(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to set up WebRTC connection');
      stopWebRTC();
    } finally {
      setIsLoading(false);
    }
  };

  const handleIceCandidate = async (event: RTCPeerConnectionIceEvent) => {
    if (event.candidate) {
      try {
        await fetch(`${apiUrl}/webrtc/offer`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            candidate: event.candidate.toJSON(),
            webrtc_id: webrtcIdRef.current,
            type: 'ice-candidate',
          }),
        });
      } catch (err) {
        console.error('Error sending ICE candidate:', err);
      }
    }
  };

  const handleTrack = (event: RTCTrackEvent) => {
    if (event.track.kind === 'audio') {
      const audioElement = new Audio();
      audioElement.srcObject = event.streams[0];
      audioElement.play().catch(console.error);

      if (audioContextRef.current) {
        sourceOutputRef.current = audioContextRef.current.createMediaStreamSource(event.streams[0]);
        analyserOutputRef.current = audioContextRef.current.createAnalyser();
        sourceOutputRef.current.connect(analyserOutputRef.current);
        analyserOutputRef.current.fftSize = 2048;
      }
    }
  };

  const handleConnectionStateChange = () => {
    if (peerConnectionRef.current) {
      const state = peerConnectionRef.current.connectionState;
      setIsConnected(state === 'connected');
      console.log('Connection state:', state);
      if (['disconnected', 'failed', 'closed'].includes(state)) {
        stopWebRTC();
      }
    }
  };

  const handleDataChannelMessage = async (event: MessageEvent) => {
    try {
      const data = JSON.parse(event.data);
      if (data.type === 'error') {
        setError(data.message);
      } else if (data.type === 'send_input') {
        setIsListening(true);
        const response = await fetch(`${apiUrl}/input_hook`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            webrtc_id: webrtcIdRef.current,
            api_key: apiKey,
            voice_name: selectedVoice,
          }),
        });

        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.detail || 'Failed to send audio input');
        }
        setIsListening(false);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error processing message');
      setIsListening(false);
    }
  };

  const stopWebRTC = () => {
    if (peerConnectionRef.current) {
      peerConnectionRef.current.getSenders().forEach(sender => {
        if (sender.track) {
          sender.track.stop();
        }
      });
      peerConnectionRef.current.close();
      peerConnectionRef.current = null;
    }

    if (audioContextRef.current) {
      audioContextRef.current.close();
      audioContextRef.current = null;
    }

    if (sourceInputRef.current) {
      sourceInputRef.current.disconnect();
      sourceInputRef.current = null;
    }

    if (sourceOutputRef.current) {
      sourceOutputRef.current.disconnect();
      sourceOutputRef.current = null;
    }

    setIsRecording(false);
    setIsMuted(false);
  };

  const toggleMute = () => {
    if (peerConnectionRef.current) {
      const newMutedState = !isMuted;
      peerConnectionRef.current.getSenders().forEach(sender => {
        if (sender.track && sender.track.kind === 'audio') {
          sender.track.enabled = !newMutedState;
        }
      });
      setIsMuted(newMutedState);
    }
  };

  return (
    <Box sx={{ 
      maxWidth: 800, 
      mx: 'auto', 
      p: 3,
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      minHeight: '80vh'
    }}>
      <Paper elevation={3} sx={{ 
        p: 4, 
        borderRadius: '50%', 
        position: 'relative',
        background: 'transparent',
        boxShadow: 'none'
      }}>
        <Box sx={{ 
          position: 'relative',
          width: 200,
          height: 200,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center'
        }}>
          {/* Continuous wave animation */}
          {isListening && (
            <>
              {[...Array(5)].map((_, index) => (
                <Box
                  key={index}
                  sx={{
                    position: 'absolute',
                    width: '100%',
                    height: '100%',
                    borderRadius: '50%',
                    border: '2px solid',
                    borderColor: 'primary.main',
                    animation: 'pulse 3s infinite',
                    animationDelay: `${index * 0.6}s`,
                    '@keyframes pulse': {
                      '0%': {
                        transform: 'scale(1)',
                        opacity: 0.8
                      },
                      '50%': {
                        opacity: 0.4
                      },
                      '100%': {
                        transform: 'scale(2.5)',
                        opacity: 0
                      }
                    }
                  }}
                />
              ))}
            </>
          )}
          
          <Button
            variant="contained"
            color={isRecording ? 'secondary' : 'primary'}
            onClick={isRecording ? stopWebRTC : setupWebRTC}
            disabled={isLoading || !rtcConfig || !apiKey}
            sx={{
              width: 120,
              height: 120,
              borderRadius: '50%',
              position: 'relative',
              zIndex: 1,
              boxShadow: isListening ? '0 0 20px rgba(25, 118, 210, 0.5)' : 'none',
              transition: 'all 0.3s ease-in-out',
              '&:hover': {
                transform: isListening ? 'scale(1.05)' : 'scale(1.05)',
                boxShadow: isListening ? '0 0 30px rgba(25, 118, 210, 0.7)' : '0 0 20px rgba(0, 0, 0, 0.2)'
              }
            }}
          >
            {isLoading ? (
              <CircularProgress size={40} color="inherit" />
            ) : isRecording ? (
              <MicOffIcon sx={{ fontSize: 40 }} />
            ) : (
              <MicIcon sx={{ fontSize: 40 }} />
            )}
          </Button>
        </Box>
      </Paper>

      <Box sx={{ mt: 4, display: 'flex', alignItems: 'center', gap: 2 }}>
        <FormControl sx={{ minWidth: 120 }}>
          <InputLabel>Voice</InputLabel>
          <Select
            value={selectedVoice}
            onChange={(e) => setSelectedVoice(e.target.value)}
            label="Voice"
            disabled={isRecording || isLoading}
          >
            {voices.map((voice) => (
              <MenuItem key={voice} value={voice}>
                {voice}
              </MenuItem>
            ))}
          </Select>
        </FormControl>

        {isRecording && (
          <Button
            variant="outlined"
            onClick={toggleMute}
            startIcon={isMuted ? <MicOffIcon /> : <MicIcon />}
          >
            {isMuted ? 'Unmute' : 'Mute'}
          </Button>
        )}
      </Box>

      {!apiKey && (
        <Alert severity="warning" sx={{ mt: 2 }}>
          Please set your Gemini API key in the .env file
        </Alert>
      )}

      {error && (
        <Alert severity="error" sx={{ mt: 2 }}>
          {error}
        </Alert>
      )}
    </Box>
  );
};

export default VoiceChat; 