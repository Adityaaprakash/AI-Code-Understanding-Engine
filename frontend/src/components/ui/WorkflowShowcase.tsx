import React from 'react';
import { Link } from 'react-router-dom';
import { 
  FolderGit2, 
  Search, 
  FileCode2, 
  Network, 
  MessageSquare, 
  BookOpen, 
  Target,
  ArrowRight
} from 'lucide-react';
import { Panel } from './Panel';
import { Button } from './Button';

interface WorkflowShowcaseProps {
  repositoryId?: string;
}

export const WorkflowShowcase: React.FC<WorkflowShowcaseProps> = ({ repositoryId }) => {
  const steps = [
    {
      id: 'repo',
      title: 'Repository & Dashboard',
      description: 'Import and instantly parse repositories into a canonical semantic graph.',
      icon: <FolderGit2 size={24} />,
      link: repositoryId ? `/overview/${repositoryId}` : '/repositories',
      linkLabel: 'View Dashboard'
    },
    {
      id: 'search',
      title: 'Universal Search',
      description: 'Search the codebase using lexical, semantic, and graph signals.',
      icon: <Search size={24} />,
      link: repositoryId ? `/search/${repositoryId}` : '/search',
      linkLabel: 'Search Code'
    },
    {
      id: 'symbol',
      title: 'Symbol Understanding',
      description: 'Inspect a symbol and its relationships.',
      icon: <FileCode2 size={24} />,
      link: '/symbols',
      linkLabel: 'Explore Symbols' // Requires search first usually, but links to empty state to prompt search
    },
    {
      id: 'graph',
      title: 'Semantic Graph',
      description: 'Visualize dependencies and structural code relationships.',
      icon: <Network size={24} />,
      link: repositoryId ? `/graph/${repositoryId}` : '/graph',
      linkLabel: 'View Graph'
    },
    {
      id: 'chat',
      title: 'Ask AI Chat',
      description: 'Ask questions grounded in retrieved code context.',
      icon: <MessageSquare size={24} />,
      link: repositoryId ? `/chat/${repositoryId}` : '/chat',
      linkLabel: 'Start Chat'
    },
    {
      id: 'citation',
      title: 'Grounded Citations',
      description: 'Answers provide deterministic citation markers verifying their source context.',
      icon: <BookOpen size={24} />,
      link: repositoryId ? `/chat/${repositoryId}` : '/chat',
      linkLabel: 'See Citations'
    },
    {
      id: 'impact',
      title: 'Impact Analysis',
      description: 'Trace why a symbol may be affected and calculate blast radius recursively.',
      icon: <Target size={24} />,
      link: '/impact',
      linkLabel: 'Analyze Impact'
    }
  ];

  return (
    <div className="workflow-showcase" style={{ margin: 'var(--sp-8) 0' }}>
      <style>{`
        .workflow-showcase-title {
          font-size: var(--text-lg);
          font-weight: var(--weight-semibold);
          margin-bottom: var(--sp-4);
          color: var(--text-primary);
        }
        .workflow-timeline {
          display: flex;
          flex-direction: column;
          gap: var(--sp-4);
          position: relative;
        }
        .workflow-timeline::before {
          content: '';
          position: absolute;
          left: 24px;
          top: 0;
          bottom: 0;
          width: 2px;
          background-color: var(--border);
          z-index: 0;
        }
        @media (min-width: 768px) {
          .workflow-timeline {
            flex-direction: row;
            flex-wrap: wrap;
            align-items: stretch;
          }
          .workflow-timeline::before {
             display: none;
          }
        }
        .workflow-step {
          position: relative;
          z-index: 1;
          display: flex;
          gap: var(--sp-4);
          align-items: flex-start;
          width: 100%;
        }
        @media (min-width: 768px) {
          .workflow-step {
             width: calc(50% - var(--sp-2));
          }
        }
        .workflow-icon-wrapper {
          display: flex;
          align-items: center;
          justify-content: center;
          width: 48px;
          height: 48px;
          border-radius: 50%;
          background-color: var(--bg-surface);
          border: 2px solid var(--border);
          color: var(--accent);
          flex-shrink: 0;
        }
        .workflow-card {
          flex: 1;
          display: flex;
          flex-direction: column;
          gap: var(--sp-2);
        }
        .workflow-card h3 {
          margin: 0;
          font-size: var(--text-base);
          font-weight: var(--weight-semibold);
          color: var(--text-primary);
        }
        .workflow-card p {
          margin: 0;
          font-size: var(--text-sm);
          color: var(--text-secondary);
          line-height: 1.5;
        }
      `}</style>
      
      <h2 className="workflow-showcase-title">Explore CodeLens Intelligence Flow</h2>
      
      <div className="workflow-timeline">
        {steps.map((step, index) => (
          <div className="workflow-step" key={step.id}>
            <div className="workflow-icon-wrapper">
              {step.icon}
            </div>
            <Panel className="workflow-card">
              <h3>{index + 1}. {step.title}</h3>
              <p>{step.description}</p>
              <div style={{ marginTop: 'auto', paddingTop: 'var(--sp-2)' }}>
                <Link to={step.link} style={{ textDecoration: 'none' }} aria-label={`Navigate to ${step.linkLabel}`}>
                  <Button variant="ghost" size="sm" iconRight={<ArrowRight size={14} />}>
                    {step.linkLabel}
                  </Button>
                </Link>
              </div>
            </Panel>
          </div>
        ))}
      </div>
    </div>
  );
};
