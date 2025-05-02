import React from 'react';
import { Box, useTheme, useMediaQuery } from '@mui/material';
import VoiceChat from './VoiceChat';

interface LayoutProps {
  children: React.ReactNode;
  apiKey: string;
}

const Layout: React.FC<LayoutProps> = ({ children, apiKey }) => {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));

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
        <VoiceChat apiKey={apiKey} />
      </Box>
    </Box>
  );
};

export default Layout; 