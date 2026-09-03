import React from 'react';
import { Network } from 'lucide-react';
import { PlaceholderPage } from '../components/ui/PlaceholderPage';

export const GraphPage: React.FC = () => (
  <PlaceholderPage
    task="7D"
    title="Code Graph"
    description="Visualise the structural relationship graph — calls, imports, inheritance, and dependencies."
    icon={<Network size={40} strokeWidth={1} />}
  />
);
