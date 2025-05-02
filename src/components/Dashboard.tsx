import React, { useState, useEffect } from 'react';
import { 
  Box, 
  Typography, 
  Paper,
  CircularProgress
} from '@mui/material';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  BarChart,
  Bar
} from 'recharts';

interface RepoData {
  commits: Array<{ date: string; count: number }>;
  languages: Array<{ name: string; percentage: number }>;
  contributors: Array<{ name: string; commits: number }>;
}

const Dashboard: React.FC = () => {
  const [repoData, setRepoData] = useState<RepoData>({
    commits: [],
    languages: [],
    contributors: []
  });
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchRepoData = async () => {
      try {
        // TODO: Replace with actual GitHub API calls
        // This is mock data for demonstration
        const mockData: RepoData = {
          commits: [
            { date: '2023-01', count: 12 },
            { date: '2023-02', count: 19 },
            { date: '2023-03', count: 15 },
            { date: '2023-04', count: 22 },
            { date: '2023-05', count: 18 },
          ],
          languages: [
            { name: 'TypeScript', percentage: 45 },
            { name: 'JavaScript', percentage: 30 },
            { name: 'CSS', percentage: 15 },
            { name: 'HTML', percentage: 10 },
          ],
          contributors: [
            { name: 'User1', commits: 120 },
            { name: 'User2', commits: 85 },
            { name: 'User3', commits: 65 },
            { name: 'User4', commits: 45 },
          ]
        };

        // Simulate API call delay
        await new Promise(resolve => setTimeout(resolve, 1000));
        setRepoData(mockData);
      } catch (error) {
        console.error('Error fetching repository data:', error);
      } finally {
        setIsLoading(false);
      }
    };

    fetchRepoData();
  }, []);

  if (isLoading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%' }}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h4" gutterBottom>
        Repository Analytics
      </Typography>

      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 3 }}>
        {/* Commits Over Time */}
        <Box sx={{ flexGrow: 1, width: { xs: '100%', md: 'calc(66.666% - 12px)' } }}>
          <Paper sx={{ p: 2, height: 400 }}>
            <Typography variant="h6" gutterBottom>
              Commits Over Time
            </Typography>
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={repoData.commits}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="date" />
                <YAxis />
                <Tooltip />
                <Line type="monotone" dataKey="count" stroke="#8884d8" />
              </LineChart>
            </ResponsiveContainer>
          </Paper>
        </Box>

        {/* Language Distribution */}
        <Box sx={{ flexGrow: 1, width: { xs: '100%', md: 'calc(33.333% - 12px)' } }}>
          <Paper sx={{ p: 2, height: 400 }}>
            <Typography variant="h6" gutterBottom>
              Language Distribution
            </Typography>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={repoData.languages}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" />
                <YAxis />
                <Tooltip />
                <Bar dataKey="percentage" fill="#82ca9d" />
              </BarChart>
            </ResponsiveContainer>
          </Paper>
        </Box>

        {/* Top Contributors */}
        <Box sx={{ flexGrow: 1, width: '100%' }}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>
              Top Contributors
            </Typography>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={repoData.contributors}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" />
                <YAxis />
                <Tooltip />
                <Bar dataKey="commits" fill="#8884d8" />
              </BarChart>
            </ResponsiveContainer>
          </Paper>
        </Box>
      </Box>
    </Box>
  );
};

export default Dashboard; 