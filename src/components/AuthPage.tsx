import React from 'react';
import { useNavigate } from 'react-router-dom';
import { GitHubSetup } from './GitHubSetup';

const AuthPage: React.FC = () => {
  const navigate = useNavigate();

  const handleSetupComplete = (data: any) => {
    // Store the authentication data in localStorage
    localStorage.setItem('repoConfig', JSON.stringify(data));
    // Navigate to the speech recognition page
    navigate('/speech');
  };

  return (
    <div className="auth-page">
      <GitHubSetup onSetupComplete={handleSetupComplete} />
    </div>
  );
};

export default AuthPage; 