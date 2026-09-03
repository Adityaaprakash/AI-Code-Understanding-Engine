import React from 'react';
import { FileCode2 } from 'lucide-react';
import { PlaceholderPage } from '../components/ui/PlaceholderPage';

export const SymbolsPage: React.FC = () => (
  <PlaceholderPage
    task="7C"
    title="Symbol Explorer"
    description="Search and inspect code symbols — classes, functions, methods — with full context and source locations."
    icon={<FileCode2 size={40} strokeWidth={1} />}
  />
);
