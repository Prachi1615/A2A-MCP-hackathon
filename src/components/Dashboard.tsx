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
import ReactMarkdown from 'react-markdown';
import { Components } from 'react-markdown';

interface RepoData {
  commits: Array<{ date: string; count: number }>;
  languages: Array<{ name: string; percentage: number }>;
  contributors: Array<{ name: string; commits: number }>;
}

interface DashboardProps {
  markdownContent?: string;
  isLoading?: boolean;
}

interface CodeProps {
  inline?: boolean;
  className?: string;
  children?: React.ReactNode;
}

const Dashboard: React.FC<DashboardProps> = ({ 
  markdownContent = '', 
  isLoading = false 
}) => {
  const [repoData, setRepoData] = useState<RepoData>({
    commits: [],
    languages: [],
    contributors: []
  });

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

  const components: Components = {
    h1: ({ node, ...props }) => <Typography variant="h4" gutterBottom {...props} />,
    h2: ({ node, ...props }) => <Typography variant="h5" gutterBottom {...props} />,
    h3: ({ node, ...props }) => <Typography variant="h6" gutterBottom {...props} />,
    h4: ({ node, ...props }) => <Typography variant="subtitle1" gutterBottom {...props} />,
    h5: ({ node, ...props }) => <Typography variant="subtitle2" gutterBottom {...props} />,
    h6: ({ node, ...props }) => <Typography variant="subtitle2" gutterBottom {...props} />,
    p: ({ node, ...props }) => <Typography variant="body1" paragraph {...props} />,
    li: ({ node, ...props }) => <Typography component="li" variant="body1" {...props} />,
    code: ({ inline, className, children, ...props }: CodeProps) => (
      <Box
        component="code"
        sx={{
          backgroundColor: 'grey.100',
          p: inline ? 0.5 : 2,
          borderRadius: 1,
          display: inline ? 'inline' : 'block',
          fontFamily: 'monospace',
          whiteSpace: 'pre-wrap',
          overflowX: 'auto'
        }}
        {...props}
      >
        {children}
      </Box>
    ),
    pre: ({ node, ...props }) => (
      <Box
        component="pre"
        sx={{
          backgroundColor: 'grey.100',
          p: 2,
          borderRadius: 1,
          overflowX: 'auto'
        }}
        {...props}
      />
    ),
  };

  return (
    <Box sx={{ p: 3 }}>
      <Paper sx={{ p: 3 }}>
        <ReactMarkdown components={components}>
          {markdownContent}
        </ReactMarkdown>
      </Paper>
    </Box>
  );
};

export default Dashboard; 