import React from 'react';
import { Search } from 'lucide-react';
import { PlaceholderPage } from '../components/ui/PlaceholderPage';

export const SearchPage: React.FC = () => (
  <PlaceholderPage
    task="7F"
    title="Semantic Search"
    description="BM25 + vector hybrid search across indexed code chunks, symbols, and documentation."
    icon={<Search size={40} strokeWidth={1} />}
  />
);
