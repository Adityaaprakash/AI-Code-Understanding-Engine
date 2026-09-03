import React from 'react';
import { Layers } from 'lucide-react';
import { PlaceholderPage } from '../components/ui/PlaceholderPage';

export const OverviewPage: React.FC = () => (
  <PlaceholderPage
    task="7A"
    title="Repository Overview"
    description="Index a repository and explore its structure, statistics, and indexing status."
    icon={<Layers size={40} strokeWidth={1} />}
  />
);
