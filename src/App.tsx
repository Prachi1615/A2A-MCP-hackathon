import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import SpeechConversation from './components/SpeechConversation';
import AuthPage from './components/AuthPage';
import Layout from './components/Layout';
import Dashboard from './components/Dashboard';
import VapiChat from './components/VapiChat';
import { Container, Typography, Box } from '@mui/material';

// Protected Route component
const ProtectedRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const repoConfig = localStorage.getItem('repoConfig');
  
  if (!repoConfig) {
    return <Navigate to="/auth" replace />;
  }
  
  return <>{children}</>;
};

function App() {
  // Get repository configuration
  const getRepoConfig = () => {
    const config = localStorage.getItem('repoConfig');
    return config ? JSON.parse(config) : null;
  };

  const repoConfig = getRepoConfig();
  const context = repoConfig?.markdown || '';

  return (
    <Router>
      <div className="App">
        <main>
          <Routes>
            <Route path="/auth" element={<AuthPage />} />
            <Route
              path="/speech"
              element={
                <ProtectedRoute>
                  <Layout apiKey={process.env.REACT_APP_VAPI_API_KEY || ''}>
                    <Dashboard markdownContent={context} />
                  </Layout>
                </ProtectedRoute>
              }
            />
            <Route path="/" element={<Navigate to="/auth" replace />} />
          </Routes>
        </main>
      </div>
    </Router>
  );
}

export default App;
