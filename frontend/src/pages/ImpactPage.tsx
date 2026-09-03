import React from 'react';
import { BarChart2 } from 'lucide-react';
import { PlaceholderPage } from '../components/ui/PlaceholderPage';

export const ImpactPage: React.FC = () => (
  <PlaceholderPage
    task="7E"
    title="Impact Analysis"
    description="Calculate the blast radius of a change — which symbols, files, and modules are affected."
    icon={<BarChart2 size={40} strokeWidth={1} />}
  />
);
