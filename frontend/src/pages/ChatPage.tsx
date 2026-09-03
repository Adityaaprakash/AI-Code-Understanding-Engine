import React from 'react';
import { MessageSquare } from 'lucide-react';
import { PlaceholderPage } from '../components/ui/PlaceholderPage';

export const ChatPage: React.FC = () => (
  <PlaceholderPage
    task="7B"
    title="Codebase Chat"
    description="Ask natural-language questions about your codebase and receive grounded answers with source citations."
    icon={<MessageSquare size={40} strokeWidth={1} />}
  />
);
