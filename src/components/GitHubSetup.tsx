import React, { useState, useEffect } from 'react';
import {
  Box,
  Paper,
  TextField,
  Button,
  Typography,
  CircularProgress,
  Alert,
  Divider,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Autocomplete,
} from '@mui/material';
import { GitHub as GitHubIcon } from '@mui/icons-material';
import { GitHubAuth } from './GitHubAuth';

interface GitHubSetupProps {
  onSetupComplete: (repoUrl: string, accessToken: string, metadata: RepositoryMetadata) => void;
}

interface SetupData {
  repoUrl: string;
  accessToken: string;
}

interface Repository {
  full_name: string;
  html_url: string;
  private: boolean;
  description?: string;
  default_branch: string;
}

interface RepositoryMetadata {
  name: string;
  full_name: string;
  description?: string;
  default_branch: string;
  private: boolean;
  owner: string;
}

// Replace this with your GitHub OAuth App client ID
const GITHUB_CLIENT_ID = process.env.REACT_APP_GITHUB_CLIENT_ID || '';

export const GitHubSetup: React.FC<GitHubSetupProps> = ({ onSetupComplete }) => {
  const [formData, setFormData] = useState<SetupData>({
    repoUrl: '',
    accessToken: '',
  });
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [repositories, setRepositories] = useState<Repository[]>([]);
  const [isLoadingRepos, setIsLoadingRepos] = useState(false);
  const [selectedRepo, setSelectedRepo] = useState<Repository | null>(null);

  const fetchUserRepositories = async (accessToken: string) => {
    setIsLoadingRepos(true);
    setError(null);
    try {
      const response = await fetch('https://api.github.com/user/repos?sort=updated&per_page=100', {
        headers: {
          'Authorization': `Bearer ${accessToken}`,
          'Accept': 'application/vnd.github.v3+json'
        }
      });

      if (!response.ok) {
        throw new Error('Failed to fetch repositories');
      }

      const repos = await response.json();
      setRepositories(repos.map((repo: any) => ({
        full_name: repo.full_name,
        html_url: repo.html_url,
        private: repo.private,
        description: repo.description,
        default_branch: repo.default_branch
      })));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load repositories');
    } finally {
      setIsLoadingRepos(false);
    }
  };

  const handleAuthSuccess = async (accessToken: string) => {
    setFormData(prev => ({ ...prev, accessToken }));
    await fetchUserRepositories(accessToken);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsLoading(true);

    try {
      const apiUrl = process.env.REACT_APP_API_URL || 'http://localhost:8000';
      
      if (selectedRepo) {
        // Use selected repository from dropdown
        const response = await fetch(`${apiUrl}/api/setup/repository`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            repository_url: selectedRepo.html_url,
            access_token: formData.accessToken,
          }),
        });

        if (!response.ok) {
          const data = await response.json();
          throw new Error(data.message || 'Failed to validate repository access');
        }

        const data = await response.json();
        onSetupComplete(
          selectedRepo.html_url,
          formData.accessToken,
          data
        );
      } else {
        // Manual URL validation
        const urlPattern = /^https:\/\/github\.com\/[\w-]+\/[.\w-]+\/?$/;
        if (!urlPattern.test(formData.repoUrl)) {
          throw new Error('Please enter a valid GitHub repository URL (e.g., https://github.com/username/repository)');
        }

        const response = await fetch(`${apiUrl}/api/setup/repository`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            repository_url: formData.repoUrl,
            access_token: formData.accessToken || undefined,
          }),
        });

        if (!response.ok) {
          const data = await response.json();
          throw new Error(data.message || 'Failed to validate repository access');
        }

        const data = await response.json();
        onSetupComplete(
          formData.repoUrl,
          formData.accessToken,
          data
        );
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An unexpected error occurred');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Box
      sx={{
        height: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        backgroundColor: '#f5f5f5',
      }}
    >
      <Paper
        elevation={3}
        sx={{
          p: 4,
          maxWidth: 500,
          width: '90%',
          display: 'flex',
          flexDirection: 'column',
          gap: 3,
        }}
      >
        <Box sx={{ textAlign: 'center', mb: 2 }}>
          <GitHubIcon sx={{ fontSize: 48, color: 'text.secondary', mb: 2 }} />
          <Typography variant="h5" component="h1" gutterBottom>
            Connect to GitHub Repository
          </Typography>
          <Typography variant="body1" color="text.secondary">
            Sign in with GitHub or provide your repository details manually
          </Typography>
        </Box>

        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}

        <GitHubAuth
          onAuthSuccess={handleAuthSuccess}
          clientId={GITHUB_CLIENT_ID}
        />

        {formData.accessToken && (
          <form onSubmit={handleSubmit}>
            <FormControl fullWidth sx={{ mb: 3 }}>
              <Autocomplete
                value={selectedRepo}
                onChange={(_, newValue) => setSelectedRepo(newValue)}
                options={repositories}
                getOptionLabel={(option) => option.full_name}
                loading={isLoadingRepos}
                renderInput={(params) => (
                  <TextField
                    {...params}
                    label="Select Repository"
                    required
                    InputProps={{
                      ...params.InputProps,
                      endAdornment: (
                        <>
                          {isLoadingRepos ? <CircularProgress color="inherit" size={20} /> : null}
                          {params.InputProps.endAdornment}
                        </>
                      ),
                    }}
                  />
                )}
                renderOption={(props, option) => (
                  <MenuItem {...props}>
                    <Box>
                      <Typography variant="body1">{option.full_name}</Typography>
                      <Typography variant="caption" color="text.secondary">
                        {option.private ? 'Private' : 'Public'}
                      </Typography>
                    </Box>
                  </MenuItem>
                )}
              />
            </FormControl>

            <Button
              fullWidth
              variant="contained"
              size="large"
              type="submit"
              disabled={isLoading || !selectedRepo}
              startIcon={isLoading ? <CircularProgress size={20} /> : <GitHubIcon />}
            >
              {isLoading ? 'Connecting...' : 'Connect Repository'}
            </Button>
          </form>
        )}

        {!formData.accessToken && (
          <>
            <Divider sx={{ my: 2 }}>
              <Typography color="text.secondary">OR</Typography>
            </Divider>

            <form onSubmit={handleSubmit}>
              <TextField
                fullWidth
                label="Repository URL"
                placeholder="https://github.com/username/repository"
                value={formData.repoUrl}
                onChange={(e) =>
                  setFormData((prev) => ({ ...prev, repoUrl: e.target.value }))
                }
                required
                sx={{ mb: 2 }}
              />

              <TextField
                fullWidth
                label="Access Token (for private repositories)"
                placeholder="ghp_xxxxxxxxxxxx"
                value={formData.accessToken}
                onChange={(e) =>
                  setFormData((prev) => ({ ...prev, accessToken: e.target.value }))
                }
                type="password"
                sx={{ mb: 3 }}
              />

              <Button
                fullWidth
                variant="contained"
                size="large"
                type="submit"
                disabled={isLoading || !formData.repoUrl}
                startIcon={isLoading ? <CircularProgress size={20} /> : <GitHubIcon />}
              >
                {isLoading ? 'Connecting...' : 'Connect Repository'}
              </Button>
            </form>
          </>
        )}
      </Paper>
    </Box>
  );
}; 