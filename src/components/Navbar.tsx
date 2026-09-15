import React from 'react';
import { Database, RefreshCw, FileSpreadsheet } from 'lucide-react';
import { DatabaseSummary } from '../types';

interface NavbarProps {
  summary: DatabaseSummary | null;
  onReset: () => void;
  isResetting: boolean;
  activeTab: string;
  setActiveTab: (tab: string) => void;
}

export const Navbar: React.FC<NavbarProps> = ({
  summary,
  onReset,
  isResetting,
  activeTab,
  setActiveTab,
}) => {
  return (
    <header id="main-header" className="bg-slate-900 text-white border-b border-slate-800 sticky top-0 z-40">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-lg bg-indigo-600 flex items-center justify-center text-white shadow-md">
              <Database className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <span className="font-bold text-lg text-slate-100 tracking-tight">Research Funding Pipeline</span>
                <span className="px-2 py-0.5 text-xs font-medium bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 rounded-full">
                  SQLite 3 Embedded
                </span>
              </div>
            </div>
          </div>

          <div className="flex items-center space-x-2">
            {summary && (
              <div className="hidden md:flex items-center space-x-3 mr-4 text-xs">
                <div className="bg-slate-800/80 px-3 py-1.5 rounded-md border border-slate-700">
                  <span className="text-slate-400">Central Students: </span>
                  <span className="font-semibold text-white">{summary.total_students}</span>
                </div>
                {summary.students_dual_funded > 0 && (
                  <div className="bg-amber-950/60 px-3 py-1.5 rounded-md border border-amber-800/60 text-amber-300">
                    <span>Dual Funded: </span>
                    <span className="font-bold">{summary.students_dual_funded}</span>
                  </div>
                )}
              </div>
            )}

            <button
              id="reset-db-btn"
              onClick={onReset}
              disabled={isResetting}
              className="inline-flex items-center space-x-1.5 px-3 py-1.5 text-xs font-medium text-rose-300 hover:text-rose-200 bg-rose-950/40 hover:bg-rose-900/50 border border-rose-900/60 rounded-md transition disabled:opacity-50"
              title="Reset all tables"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${isResetting ? 'animate-spin' : ''}`} />
              <span>Reset</span>
            </button>
          </div>
        </div>

        {/* Navigation Tabs */}
        <div className="flex space-x-1 overflow-x-auto py-2 border-t border-slate-800 text-sm">
          <button
            id="tab-import"
            onClick={() => setActiveTab('import')}
            className={`px-3 py-1.5 rounded-md text-xs font-medium whitespace-nowrap transition ${
              activeTab === 'import'
                ? 'bg-indigo-600 text-white shadow-sm'
                : 'text-slate-300 hover:text-white hover:bg-slate-800'
            }`}
          >
            Data Intake Hub
          </button>
          <button
            id="tab-central"
            onClick={() => setActiveTab('central')}
            className={`px-3 py-1.5 rounded-md text-xs font-medium whitespace-nowrap transition flex items-center space-x-1.5 ${
              activeTab === 'central'
                ? 'bg-indigo-600 text-white shadow-sm'
                : 'text-slate-300 hover:text-white hover:bg-slate-800'
            }`}
          >
            <span>Central Students</span>
            {summary && summary.total_students > 0 && (
              <span className="px-1.5 py-0.2 text-[10px] bg-slate-900 text-slate-200 rounded-full">
                {summary.total_students}
              </span>
            )}
          </button>
          <button
            id="tab-fws"
            onClick={() => setActiveTab('fws')}
            className={`px-3 py-1.5 rounded-md text-xs font-medium whitespace-nowrap transition flex items-center space-x-1.5 ${
              activeTab === 'fws'
                ? 'bg-indigo-600 text-white shadow-sm'
                : 'text-slate-300 hover:text-white hover:bg-slate-800'
            }`}
          >
            <span>FWS Sub-Table</span>
            {summary && summary.total_fws_records > 0 && (
              <span className="px-1.5 py-0.2 text-[10px] bg-slate-900 text-slate-200 rounded-full">
                {summary.total_fws_records}
              </span>
            )}
          </button>
          <button
            id="tab-grant"
            onClick={() => setActiveTab('grant')}
            className={`px-3 py-1.5 rounded-md text-xs font-medium whitespace-nowrap transition flex items-center space-x-1.5 ${
              activeTab === 'grant'
                ? 'bg-indigo-600 text-white shadow-sm'
                : 'text-slate-300 hover:text-white hover:bg-slate-800'
            }`}
          >
            <span>Project Supply Grant Sub-Table</span>
            {summary && summary.total_grant_records > 0 && (
              <span className="px-1.5 py-0.2 text-[10px] bg-slate-900 text-slate-200 rounded-full">
                {summary.total_grant_records}
              </span>
            )}
          </button>
        </div>
      </div>
    </header>
  );
};
