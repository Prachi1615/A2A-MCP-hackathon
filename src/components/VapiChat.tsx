import React, { useEffect, useState } from 'react';
import { Box, Button, Typography, Paper, CircularProgress, Alert } from '@mui/material';
import MicIcon from '@mui/icons-material/Mic';
import MicOffIcon from '@mui/icons-material/MicOff';
import Vapi from '@vapi-ai/web';

interface VapiChatProps {
  apiKey: string;
  context?: string;
}

const VapiChat: React.FC<VapiChatProps> = ({ apiKey, context }) => {
  const [vapi, setVapi] = useState<Vapi | null>(null);
  const [isRecording, setIsRecording] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    if (apiKey) {
      const vapiInstance = new Vapi(apiKey);
      setVapi(vapiInstance);

      // Set up event listeners
      vapiInstance.on('speech-start', () => {
        console.log('Assistant started speaking');
      });

      vapiInstance.on('speech-end', () => {
        console.log('Assistant finished speaking');
      });

      vapiInstance.on('call-start', () => {
        console.log('Call started');
      });

      vapiInstance.on('call-end', () => {
        console.log('Call ended');
        setIsRecording(false);
      });

      vapiInstance.on('error', (e) => {
        console.error('VAPI error:', e);
        setError(e.message);
      });

      return () => {
        vapiInstance.stop();
      };
    }
  }, [apiKey]);

  const startCall = async () => {
    if (!vapi) return;

    try {
      setIsLoading(true);
      setError(null);

      // Create system message with context if provided
      const systemMessage = context 
        ? `You are a helpful assistant. Here is the context for our conversation: ${context}`
        : "You are a helpful assistant.";

      // Start the call with a basic assistant configuration
      await vapi.start({
        transcriber: {
          provider: "deepgram",
          model: "nova-2",
          language: "en-US",
        },
        model: {
          provider: "openai",
          model: "gpt-3.5-turbo",
          messages: [
            {
              role: "system",
              content: systemMessage,
            },
          ],
        },
        voice: {
          provider: "playht",
          voiceId: "jennifer",
        },
      });

      setIsRecording(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start call');
    } finally {
      setIsLoading(false);
    }
  };

  const stopCall = () => {
    if (vapi) {
      vapi.stop();
      setIsRecording(false);
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
          <Button
            variant="contained"
            color={isRecording ? 'secondary' : 'primary'}
            onClick={isRecording ? stopCall : startCall}
            disabled={isLoading || !apiKey}
            sx={{
              width: 120,
              height: 120,
              borderRadius: '50%',
              position: 'relative',
              zIndex: 1,
              transition: 'all 0.3s ease-in-out',
              '&:hover': {
                transform: 'scale(1.05)',
                boxShadow: '0 0 20px rgba(0, 0, 0, 0.2)'
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

      {!apiKey && (
        <Alert severity="warning" sx={{ mt: 2 }}>
          Please set your VAPI API key in the .env file
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

export default VapiChat; 