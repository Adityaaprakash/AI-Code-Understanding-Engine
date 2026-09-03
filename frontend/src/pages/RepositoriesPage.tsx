import React from 'react';
import { GitBranch } from 'lucide-react';
import { PlaceholderPage } from '../components/ui/PlaceholderPage';

export const RepositoriesPage: React.FC = () => (
  <PlaceholderPage
    task="7A"
    title="Repositories"
    description="Connect GitHub repositories or local paths to index and analyse."
    icon={<GitBranch size={40} strokeWidth={1} />}
  />
);
