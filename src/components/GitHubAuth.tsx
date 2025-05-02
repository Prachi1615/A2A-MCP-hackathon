import React, { useEffect, useState } from 'react';
import {
  Button,
  CircularProgress,
  Typography,
  Box,
  Alert,
} from '@mui/material';
import { GitHub as GitHubIcon } from '@mui/icons-material';

interface GitHubAuthProps {
  onAuthSuccess: (accessToken: string) => void;
  clientId: string;
}

export const GitHubAuth: React.FC<GitHubAuthProps> = ({ onAuthSuccess, clientId }) => {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // Handle the OAuth callback
    const handleCallback = async () => {
      const queryParams = new URLSearchParams(window.location.search);
      const code = queryParams.get('code');
      const error = queryParams.get('error');
      const errorDescription = queryParams.get('error_description');

      // Clean up the URL immediately
      window.history.replaceState({}, document.title, window.location.pathname);

      if (error || errorDescription) {
        setError(errorDescription || 'Authentication failed');
        return;
      }

      if (code) {
        setIsLoading(true);
        setError(null);

        try {
          console.log('Exchanging code for access token...');
          const apiUrl = process.env.REACT_APP_API_URL || 'http://localhost:8000';
          const response = await fetch(`${apiUrl}/api/auth/github/callback`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({ code }),
          });

          if (!response.ok) {
            const data = await response.json();
            throw new Error(data.message || 'Failed to authenticate with GitHub');
          }

          const data = await response.json();
          
          if (!data.access_token) {
            throw new Error('No access token received');
          }

          console.log('Successfully obtained access token');
          onAuthSuccess(data.access_token);
        } catch (err) {
          console.error('Authentication error:', err);
          setError(err instanceof Error ? err.message : 'Authentication failed');
        } finally {
          setIsLoading(false);
        }
      }
    };

    handleCallback();
  }, [onAuthSuccess]);

  const handleLogin = () => {
    if (!clientId) {
      setError('GitHub Client ID is not configured');
      return;
    }

    const redirectUri = `${window.location.origin}${window.location.pathname}`;
    const scope = 'repo'; // Minimum scope needed for repository access
    const state = Math.random().toString(36).substring(7); // Add state parameter for security
    
    // Store state in sessionStorage for verification when the user returns
    sessionStorage.setItem('githubOAuthState', state);

    const authUrl = new URL('https://github.com/login/oauth/authorize');
    authUrl.searchParams.append('client_id', clientId);
    authUrl.searchParams.append('redirect_uri', redirectUri);
    authUrl.searchParams.append('scope', scope);
    authUrl.searchParams.append('state', state);

    console.log('Redirecting to GitHub login...');
    window.location.href = authUrl.toString();
  };

  if (isLoading) {
    return (
      <Box display="flex" flexDirection="column" alignItems="center" justifyContent="center" p={2}>
        <CircularProgress sx={{ mb: 2 }} />
        <Typography variant="body2" color="text.secondary">
          Authenticating with GitHub...
        </Typography>
      </Box>
    );
  }

  return (
    <Box>
      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}
      <Button
        variant="contained"
        color="primary"
        startIcon={<GitHubIcon />}
        onClick={handleLogin}
        fullWidth
        size="large"
        disabled={!clientId}
      >
        Sign in with GitHub
      </Button>
      <Typography variant="body2" color="text.secondary" align="center" sx={{ mt: 1 }}>
        This will allow access to your GitHub repositories
      </Typography>
    </Box>
  );
}; 