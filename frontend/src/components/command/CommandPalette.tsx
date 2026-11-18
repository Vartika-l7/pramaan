import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Search,
  LayoutDashboard,
  FolderArchive,
  Users,
  Network,
  Clock,
  Fingerprint,
  CheckSquare,
  Scale,
  Package,
  BarChart3,
  ArrowRight,
  ShieldAlert,
} from 'lucide-react';
import { useAppStore } from '../../lib/store';
import { fetchEvidenceList, fetchEntities } from '../../lib/api';

const STATIC_COMMANDS = [
  { label: 'Overview Dashboard', path: '/', icon: LayoutDashboard },
  { label: 'Evidence Vault', path: '/evidence', icon: FolderArchive },
  { label: 'Entities & People', path: '/entities', icon: Users },
  { label: 'Knowledge Graph', path: '/graph', icon: Network },
  { label: 'Event Sequence', path: '/events', icon: Clock },
  { label: 'Authenticity Checks', path: '/authenticity', icon: Fingerprint },
  { label: 'Review Queue', path: '/review', icon: CheckSquare },
  { label: 'Verifier & Challenge', path: '/verifier', icon: Scale },
  { label: 'Case Package', path: '/package', icon: Package },
  { label: 'Metrics & Benchmark', path: '/metrics', icon: BarChart3 },
];

export const CommandPalette: React.FC = () => {
  const navigate = useNavigate();
  const isOpen = useAppStore((state) => state.commandPaletteOpen);
  const setIsOpen = useAppStore((state) => state.setCommandPaletteOpen);
  const [query, setQuery] = useState('');

  // Global Cmd+K / Ctrl+K hotkey
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        setIsOpen(!isOpen);
      } else if (e.key === 'Escape' && isOpen) {
        setIsOpen(false);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, setIsOpen]);

  if (!isOpen) return null;

  const filteredCommands = STATIC_COMMANDS.filter((cmd) =>
    cmd.label.toLowerCase().includes(query.toLowerCase())
  );

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-24 bg-black/40 backdrop-blur-xs">
      <div className="w-full max-w-xl bg-surface-raised border border-border rounded-2xl shadow-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-100">
        {/* Search Input Bar */}
        <div className="flex items-center px-4 border-b border-border bg-surface">
          <Search className="w-4 h-4 text-ink-tertiary mr-3" />
          <input
            autoFocus
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Type to navigate modules or find evidence..."
            className="w-full py-4 text-sm font-sans bg-transparent focus:outline-hidden text-ink placeholder:text-ink-tertiary"
          />
          <kbd className="font-mono text-2xs text-ink-secondary bg-ivory px-2 py-0.5 rounded border border-border">
            ESC
          </kbd>
        </div>

        {/* Action List */}
        <div className="max-h-80 overflow-y-auto p-2 space-y-1">
          <div className="px-3 py-1.5 text-2xs font-sans font-bold uppercase tracking-wider text-ink-tertiary">
            Investigation Modules
          </div>

          {filteredCommands.length === 0 ? (
            <div className="p-6 text-center text-xs font-sans text-ink-secondary">
              No matching modules found.
            </div>
          ) : (
            filteredCommands.map((cmd) => {
              const Icon = cmd.icon;
              return (
                <button
                  key={cmd.path}
                  type="button"
                  onClick={() => {
                    navigate(cmd.path);
                    setIsOpen(false);
                  }}
                  className="w-full flex items-center justify-between px-3.5 py-2.5 rounded-lg hover:bg-ivory cursor-pointer text-ink font-sans text-xs transition-colors group"
                >
                  <div className="flex items-center gap-3">
                    <Icon className="w-4 h-4 text-cobalt group-hover:scale-105 transition-transform" />
                    <span className="font-medium">{cmd.label}</span>
                  </div>
                  <ArrowRight className="w-3.5 h-3.5 text-ink-tertiary group-hover:text-cobalt group-hover:translate-x-0.5 transition-all" />
                </button>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
};
