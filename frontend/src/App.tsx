import React from 'react';
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import { ThemeProvider } from './context/ThemeContext';
import { CommandPaletteProvider } from './context/CommandPaletteContext';
import { AppShell } from './components/shell/AppShell';
import { OverviewPage } from './pages/OverviewPage';
import { RepositoriesPage } from './pages/RepositoriesPage';
import { SearchPage } from './pages/SearchPage';
import { SymbolsPage } from './pages/SymbolsPage';
import { GraphPage } from './pages/GraphPage';
import { ChatPage } from './pages/ChatPage';
import { ImpactPage } from './pages/ImpactPage';
import { NotFoundPage } from './pages/NotFoundPage';

const App: React.FC = () => {
  return (
    <ThemeProvider>
      <CommandPaletteProvider>
        <BrowserRouter>
          <Routes>
            {/* Root → overview */}
            <Route path="/" element={<Navigate to="/overview" replace />} />

            {/* App shell wraps all inner routes */}
            <Route element={<AppShell />}>
              <Route path="/overview"      element={<OverviewPage />} />
              <Route path="/repositories"  element={<RepositoriesPage />} />
              <Route path="/search"        element={<SearchPage />} />
              <Route path="/symbols"       element={<SymbolsPage />} />
              <Route path="/graph"         element={<GraphPage />} />
              <Route path="/chat"          element={<ChatPage />} />
              <Route path="/impact"        element={<ImpactPage />} />
            </Route>

            {/* Catch-all */}
            <Route path="*" element={<NotFoundPage />} />
          </Routes>
        </BrowserRouter>
      </CommandPaletteProvider>
    </ThemeProvider>
  );
};

export default App;
