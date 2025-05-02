import React, { useState, useEffect, useCallback, useRef } from 'react';
import './SpeechConversation.css';
import {
  IconButton,
  Fab,
  Collapse,
  Paper,
  Slider,
  Select,
  MenuItem,
  Typography,
  Box,
  AppBar,
  Toolbar,
  FormControl,
  InputLabel,
  Tooltip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
} from '@mui/material';
import {
  Mic as MicIcon,
  Settings as SettingsIcon,
  Stop as StopIcon,
  RestartAlt as RestartIcon
} from '@mui/icons-material';
import { keyframes } from '@emotion/react';
import { styled } from '@mui/material/styles';
import { useNavigate } from 'react-router-dom';

// Type definitions for Web Speech API
interface SpeechRecognitionResult {
  transcript: string;
  confidence: number;
}

interface SpeechRecognitionAlternative {
  [index: number]: SpeechRecognitionResult;
  isFinal: boolean;
}

interface SpeechRecognitionResultList {
  [index: number]: SpeechRecognitionAlternative;
  length: number;
}

interface SpeechRecognitionEvent extends Event {
  results: SpeechRecognitionResultList;
  resultIndex: number;
}

interface SpeechRecognitionInterface extends EventTarget {
  continuous: boolean;
  interimResults: boolean;
  lang: string;
  onresult: (event: SpeechRecognitionEvent) => void;
  onend: () => void;
  onerror: (event: Event) => void;
  start: () => void;
  stop: () => void;
  abort: () => void;
}

interface SpeechRecognitionConstructor {
  new (): SpeechRecognitionInterface;
}

declare global {
  interface Window {
    SpeechRecognition?: SpeechRecognitionConstructor;
    webkitSpeechRecognition?: SpeechRecognitionConstructor;
  }
}

// Get the appropriate SpeechRecognition constructor
const SpeechRecognitionAPI = (window.SpeechRecognition || window.webkitSpeechRecognition) as SpeechRecognitionConstructor;

interface Message {
  text: string;
  type: 'user' | 'system';
}

interface VoiceSettings {
  rate: number;
  pitch: number;
  volume: number;
}

interface LLMResponse {
  text: string;
  data?: any;
}

interface ConversationResponse {
  text: string;
  conversation_id: string;
}

interface RepositoryMetadata {
  name: string;
  description?: string;
  default_branch: string;
  private: boolean;
  owner: string;
}

interface RepositoryConfig {
  repoUrl: string;
  accessToken: string;
  metadata: RepositoryMetadata;
}

const waveAnimation = keyframes`
  0% { 
    transform: scale(1);
    box-shadow: 0 0 0 0 rgba(25, 118, 210, 0.6);
  }
  50% { 
    transform: scale(1.05);
    box-shadow: 0 0 0 15px rgba(25, 118, 210, 0);
  }
  100% { 
    transform: scale(1);
    box-shadow: 0 0 0 0 rgba(25, 118, 210, 0);
  }
`;

const outerWaveAnimation = keyframes`
  0% { 
    transform: scale(1);
    opacity: 0.5;
  }
  100% { 
    transform: scale(1.8);
    opacity: 0;
  }
`;

const WiggleFab = styled(Fab)(({ theme }) => ({
  position: 'relative',
  '&.wiggling': {
    animation: `${waveAnimation} 1.5s ease-in-out infinite`,
    '&:before, &:after': {
      content: '""',
      position: 'absolute',
      inset: -4,
      borderRadius: '50%',
      border: '2px solid rgba(25, 118, 210, 0.4)',
      animation: `${outerWaveAnimation} 2s ease-out infinite`
    },
    '&:after': {
      inset: -4,
      animationDelay: '0.5s'
    },
    '& .wave-circle': {
      position: 'absolute',
      inset: -4,
      borderRadius: '50%',
      border: '2px solid rgba(25, 118, 210, 0.4)',
      animation: `${outerWaveAnimation} 2s ease-out infinite`,
      animationDelay: '1s'
    }
  }
}));

const LoadingDots = () => (
  <Box className="dot-loading" sx={{ my: 2 }}>
    <span></span>
    <span></span>
    <span></span>
  </Box>
);

const SpeechConversation: React.FC = () => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isListening, setIsListening] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [speechRecognition, setSpeechRecognition] = useState<SpeechRecognitionInterface | null>(null);
  const [voiceSettings, setVoiceSettings] = useState<VoiceSettings>({
    rate: 1.0,
    pitch: 1.0,
    volume: 1.0
  });
  const [availableVoices, setAvailableVoices] = useState<SpeechSynthesisVoice[]>([]);
  const selectedVoiceRef = useRef<SpeechSynthesisVoice | null>(null);
  const [interimTranscript, setInterimTranscript] = useState('');
  const [finalTranscript, setFinalTranscript] = useState('');
  const finalTranscriptRef = useRef('');
  const [selectedVoiceName, setSelectedVoiceName] = useState<string>('');
  const [error, setError] = useState<string | null>(null);
  const conversationIdRef = useRef<string | null>(null);
  const isInitializedRef = useRef<boolean>(false);
  const [isLoading, setIsLoading] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [resetDialogOpen, setResetDialogOpen] = useState(false);
  const [isValid, setIsValid] = useState(true);
  const navigate = useNavigate();

  // Get repository configuration from localStorage
  const getRepoConfig = (): RepositoryConfig | null => {
    const config = localStorage.getItem('repoConfig');
    return config ? JSON.parse(config) : null;
  };

  // Validate metadata in useEffect
  useEffect(() => {
    const config = getRepoConfig();
    if (!config || !config.metadata || !config.metadata.name) {
      setIsValid(false);
      navigate('/auth');
    }
  }, [navigate]);

  // Initialize speech recognition
  useEffect(() => {
    console.log('Initializing speech recognition...');
    try {
      if (SpeechRecognitionAPI) {
        console.log('SpeechRecognitionAPI available');
        const recognition = new SpeechRecognitionAPI();
        recognition.continuous = true;  // Keep recording while button is held
        recognition.interimResults = true;
        recognition.lang = 'en-US';
        
        recognition.onresult = (event: SpeechRecognitionEvent) => {
          let currentTranscript = '';
          
          // Get the latest transcript
          for (let i = event.resultIndex; i < event.results.length; i++) {
            const transcript = event.results[i][0].transcript;
            
            if (event.results[i].isFinal) {
              // Append to final transcript
              currentTranscript = transcript;
              setFinalTranscript(prev => {
                const newTranscript = prev ? `${prev} ${transcript}` : transcript;
                finalTranscriptRef.current = newTranscript;
                return newTranscript;
              });
            } else {
              // Update interim transcript
              currentTranscript = transcript;
              setInterimTranscript(transcript);
            }
          }
        };

        recognition.onend = () => {
          console.log('Speech recognition ended.');
          if (finalTranscriptRef.current) {
            handleUserInput(finalTranscriptRef.current.trim());
            setFinalTranscript('');
            finalTranscriptRef.current = '';  // Clear the ref
          }
          setIsListening(false);
        };

        recognition.onerror = (event) => {
          console.error('Speech recognition error:', event);
          setIsListening(false);
        };

        setSpeechRecognition(recognition);
      } else {
        console.error('Speech recognition not supported in this browser');
        alert('Speech recognition is not supported in your browser');
      }
    } catch (error) {
      console.error('Error initializing speech recognition:', error);
      if (error instanceof Error) {
        alert(`Error initializing speech recognition: ${error.message}`);
      }
    }
  }, []);

  // Load available voices
  useEffect(() => {
    const loadVoices = () => {
      const voices = window.speechSynthesis.getVoices();
      
      // Filter for high-quality, human-like English voices
      const preferredVoices = voices.filter(voice => {
        const voiceName = voice.name.toLowerCase();
        const isEnglish = voice.lang.startsWith('en');
        
        return isEnglish && (
          // Google's WaveNet voices
          voiceName.includes('wavenet') ||
          // Microsoft's neural voices
          voiceName.includes('neural') ||
          // Apple's high-quality voices
          voiceName.includes('samantha') ||
          voiceName.includes('daniel') ||
          // Other known high-quality voices
          voiceName.includes('enhanced') ||
          voiceName.includes('premium')
        );
      });

      // Sort voices by quality (put WaveNet and Neural voices first)
      const sortedVoices = preferredVoices.sort((a, b) => {
        const aName = a.name.toLowerCase();
        const bName = b.name.toLowerCase();
        
        if (aName.includes('wavenet') && !bName.includes('wavenet')) return -1;
        if (!aName.includes('wavenet') && bName.includes('wavenet')) return 1;
        if (aName.includes('neural') && !bName.includes('neural')) return -1;
        if (!aName.includes('neural') && bName.includes('neural')) return 1;
        return 0;
      });

      // Take only the top 4 voices
      const topVoices = sortedVoices.slice(0, 4);
      
      setAvailableVoices(topVoices);
      
      if (!selectedVoiceRef.current && topVoices.length > 0) {
        selectedVoiceRef.current = topVoices[0];
        setSelectedVoiceName(topVoices[0].name);
      }
    };

    loadVoices();
    window.speechSynthesis.addEventListener('voiceschanged', loadVoices);
    
    return () => {
      window.speechSynthesis.removeEventListener('voiceschanged', loadVoices);
    };
  }, []);

  // Initialize conversation with repository info
  useEffect(() => {
    const startNewConversation = async () => {
      const config = getRepoConfig();
      if (!config) {
        navigate('/auth');
        return;
      }

      try {
        console.log('Starting new conversation...');
        const response = await fetch('http://127.0.0.1:8000/api/conversation/start', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            repository_url: config.repoUrl,
            access_token: config.accessToken
          }),
        });
        
        if (!response.ok) {
          const error = await response.json();
          throw new Error(error.message || 'Failed to start conversation');
        }
        
        const data = await response.json();
        console.log('Conversation started:', data);
        
        if (!data.id) {
          throw new Error('No conversation ID received from server');
        }
        
        conversationIdRef.current = data.id;
        console.log('Conversation ID set:', data.id);
      } catch (error) {
        console.error('Error starting conversation:', error);
        setError('Failed to start conversation. Please check your repository settings.');
        navigate('/auth');
      }
    };

    // Only start a new conversation if we don't have one and haven't initialized yet
    if (!conversationIdRef.current && !isInitializedRef.current) {
      console.log('No conversation ID found, starting new conversation');
      isInitializedRef.current = true;
      startNewConversation();
    } else {
      console.log('Using existing conversation ID:', conversationIdRef.current);
    }
  }, [navigate]);

  const handleUserInput = async (text: string) => {
    console.log('Handling user input:', text);
    if (!text.trim()) {
      console.log('Empty text, skipping');
      return;
    }

    setMessages(prev => [...prev, { text, type: 'user' }]);
    
    try {
      const config = getRepoConfig();
      if (!config) {
        navigate('/auth');
        return;
      }

      const currentConversationId = conversationIdRef.current;
      if (!currentConversationId) {
        console.error('No conversation ID available');
        setError('No active conversation. Please try again.');
        return;
      }

      console.log('Processing input with backend:', text);
      setError(null);
      setIsLoading(true);
      
      const response = await fetch(`http://127.0.0.1:8000/api/conversation/${currentConversationId}/message`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
        },
        body: JSON.stringify({
          text: text,
          role: 'user',
          timestamp: new Date().toISOString()
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        console.error('Error response:', errorData);
        throw new Error(errorData.message || 'Failed to process message');
      }

      const data = await response.json();
      console.log('Received response from backend:', data);
      
      setIsLoading(false);
      setMessages(prev => [...prev, { text: data.text, type: 'system' }]);
      speakText(data.text);
    } catch (error) {
      console.error('Error processing input:', error);
      setError('Sorry, there was an error processing your request. Please try again.');
      setIsLoading(false);
      if (error instanceof Error && error.message.includes('repository')) {
        handleReset()
      } else {
        setMessages(prev => [...prev, { 
          text: "I'm having trouble processing your request right now. Please try again.", 
          type: 'system' 
        }]);
      }
    }
  };

  const speakText = (text: string) => {
    console.log('Speaking text:', text);
    try {
      if (!window.speechSynthesis) {
        console.error('Speech synthesis not supported in this browser');
        return;
      }

      window.speechSynthesis.cancel();
      
      const utterance = new SpeechSynthesisUtterance(text);
      
      const voices = window.speechSynthesis.getVoices();
      console.log('Available voices:', voices);
      
      if (selectedVoiceRef.current) {
        console.log('Using selected voice:', selectedVoiceRef.current);
        utterance.voice = selectedVoiceRef.current;
      } else {
        const defaultVoice = voices.find(voice => voice.lang.startsWith('en'));
        if (defaultVoice) {
          console.log('Using default voice:', defaultVoice);
          utterance.voice = defaultVoice;
        }
      }

      utterance.rate = voiceSettings.rate;
      utterance.pitch = voiceSettings.pitch;
      utterance.volume = voiceSettings.volume;

      utterance.onstart = () => {
        console.log('Speech started');
        setIsSpeaking(true);
      };

      utterance.onend = () => {
        console.log('Speech ended');
        setIsSpeaking(false);
      };

      utterance.onerror = (event) => {
        console.error('Speech synthesis error:', event);
        setIsSpeaking(false);
      };

      window.speechSynthesis.speak(utterance);
    } catch (error) {
      console.error('Error in speech synthesis:', error);
      setIsSpeaking(false);
    }
  };

  const handleVoiceChange = (voiceName: string) => {
    console.log('Attempting to change voice to:', voiceName);
    const voices = window.speechSynthesis.getVoices();
    const newVoice = voices.find(voice => voice.name === voiceName);
    
    if (newVoice) {
      console.log('Found voice:', newVoice);
      selectedVoiceRef.current = newVoice;
      setSelectedVoiceName(voiceName);
    } else {
      console.log('Voice not found:', voiceName);
    }
  };

  const toggleListening = useCallback(async () => {
    if (isListening) {
      // Stop listening
      if (speechRecognition) {
        try {
          speechRecognition.stop();
          setIsListening(false);
        } catch (error) {
          console.error('Error stopping speech recognition:', error);
        }
      }
    } else {
      // Start listening
      console.log('Starting to listen...');
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        console.log('Microphone access granted');
        stream.getTracks().forEach(track => track.stop());
        
        if (speechRecognition && !isSpeaking) {
          console.log('Speech recognition available, starting...');
          setFinalTranscript('');
          setInterimTranscript('');
          
          speechRecognition.start();
          console.log('Speech recognition started');
          setIsListening(true);
        } else {
          console.log('Cannot start listening:', { speechRecognition: !!speechRecognition, isSpeaking });
        }
      } catch (error) {
        console.error('Error starting speech recognition:', error);
        if (error instanceof Error) {
          alert(`Error accessing microphone: ${error.message}`);
        }
      }
    }
  }, [speechRecognition, isListening, isSpeaking]);

  const handleReset = () => {
    conversationIdRef.current = null;
    setResetDialogOpen(false);
    navigate('/auth');
  };

  if (!isValid) {
    return null;
  }

  const config = getRepoConfig();
  if (!config) {
    return null;
  }

  return (
    <div className="speech-conversation">
      <AppBar position="static" color="transparent" elevation={0}>
        <Toolbar>
          <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
            {config.metadata.name} - Voice Chat
          </Typography>
          <Tooltip title="Change Repository">
            <IconButton
              color="primary"
              onClick={() => setResetDialogOpen(true)}
              sx={{ mr: 1 }}
            >
              <RestartIcon />
            </IconButton>
          </Tooltip>
          <Tooltip title="Voice Settings">
            <IconButton
              color="primary"
              onClick={() => setSettingsOpen(!settingsOpen)}
              aria-label="settings"
            >
              <SettingsIcon />
            </IconButton>
          </Tooltip>
        </Toolbar>
      </AppBar>

      {/* Reset Confirmation Dialog */}
      <Dialog
        open={resetDialogOpen}
        onClose={() => setResetDialogOpen(false)}
      >
        <DialogTitle>Change Repository?</DialogTitle>
        <DialogContent>
          <Typography>
            This will end your current conversation and let you connect to a different repository. 
            Are you sure you want to continue?
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setResetDialogOpen(false)}>Cancel</Button>
          <Button onClick={handleReset} color="primary" variant="contained">
            Change Repository
          </Button>
        </DialogActions>
      </Dialog>

      <Collapse in={settingsOpen}>
        <Paper 
          sx={{ 
            p: 2, 
            m: 2, 
            backgroundColor: 'rgba(255, 255, 255, 0.9)',
            backdropFilter: 'blur(10px)'
          }}
        >
          <Box sx={{ mb: 2 }}>
            <FormControl fullWidth>
              <InputLabel>Voice</InputLabel>
              <Select
                value={selectedVoiceName}
                onChange={(e) => handleVoiceChange(e.target.value)}
                label="Voice"
              >
                {availableVoices.map(voice => (
                  <MenuItem key={voice.name} value={voice.name}>
                    {voice.name}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          </Box>

          <Box sx={{ mb: 2 }}>
            <Typography gutterBottom>Speed</Typography>
            <Slider
              value={voiceSettings.rate}
              onChange={(_, value) => setVoiceSettings(prev => ({
                ...prev,
                rate: value as number
              }))}
              min={0.5}
              max={2}
              step={0.1}
              marks
              valueLabelDisplay="auto"
            />
          </Box>

          <Box sx={{ mb: 2 }}>
            <Typography gutterBottom>Pitch</Typography>
            <Slider
              value={voiceSettings.pitch}
              onChange={(_, value) => setVoiceSettings(prev => ({
                ...prev,
                pitch: value as number
              }))}
              min={0.5}
              max={2}
              step={0.1}
              marks
              valueLabelDisplay="auto"
            />
          </Box>
        </Paper>
      </Collapse>

      <div className="conversation-container">
        {error && (
          <Paper 
            sx={{ 
              p: 1, 
              m: 1, 
              backgroundColor: '#ffebee',
              color: '#c62828'
            }}
          >
            {error}
          </Paper>
        )}
        {isLoading && <LoadingDots />}
        {messages.map((message, index) => (
          <div key={index} className={`message ${message.type}`}>
            {message.text}
          </div>
        ))}
        {isListening && (
          <div className="message interim">
            {interimTranscript == "" ? "...": interimTranscript}
          </div>
        )}
      </div>

      <Box sx={{ 
        position: 'fixed', 
        bottom: 32, 
        left: '50%', 
        transform: 'translateX(-50%)',
        zIndex: 1000 
      }}>
        <WiggleFab
          className={isListening ? 'wiggling' : ''}
          color={isListening ? "secondary" : "primary"}
          sx={{ 
            width: 80, 
            height: 80,
            boxShadow: 3,
            '&:active': {
              transform: 'scale(0.95)'
            }
          }}
          onClick={toggleListening}
          disabled={isSpeaking}
        >
          {isListening ? <StopIcon sx={{ fontSize: 32 }} /> : <MicIcon sx={{ fontSize: 32 }} />}
          {isListening && <div className="wave-circle" />}
        </WiggleFab>
      </Box>
    </div>
  );
};

export default SpeechConversation; 