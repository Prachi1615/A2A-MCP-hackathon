import React from 'react';
import { Box, useTheme, useMediaQuery } from '@mui/material';
import VapiChat from './VapiChat';

interface LayoutProps {
  children: React.ReactNode;
  apiKey: string;
}

const Layout: React.FC<LayoutProps> = ({ children, apiKey }) => {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));

  // Get repository configuration for context
  const getRepoConfig = () => {
    const config = localStorage.getItem('repoConfig');
    return config ? JSON.parse(config) : null;
  };

  const repoConfig = getRepoConfig();
  const context = repoConfig?.markdown || '';

  return (
    <Box sx={{ 
      display: 'flex',
      flexDirection: isMobile ? 'column' : 'row',
      minHeight: '100vh',
      width: '100%'
    }}>
      {/* Main Content */}
      <Box sx={{
        flex: 1,
        p: 3,
        minHeight: isMobile ? 'auto' : '100vh',
        overflow: 'auto',
        bgcolor: 'background.default'
      }}>
        {children}
      </Box>

      {/* Voice Chat Aside */}
      <Box sx={{
        width: isMobile ? '100%' : '400px',
        borderLeft: isMobile ? 'none' : `1px solid ${theme.palette.divider}`,
        borderTop: isMobile ? `1px solid ${theme.palette.divider}` : 'none',
        bgcolor: 'background.paper',
        p: 2,
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'center'
      }}>
        <VapiChat apiKey={apiKey} context={context} />
      </Box>
    </Box>
  );
};

export default Layout; 