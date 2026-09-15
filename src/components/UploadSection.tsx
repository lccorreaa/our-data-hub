import React, { useState, useRef } from 'react';
import { Upload, FileText, CheckCircle2, AlertCircle, Play, ArrowRight, Layers, RefreshCw } from 'lucide-react';
import { MigrationResult } from '../types';

interface UploadSectionProps {
  onUpload: (file: File, fundingType: 'fws' | 'grant') => Promise<void>;
  onLoadSample: (type: 'fws' | 'grant' | 'both') => Promise<void>;
  isProcessing: boolean;
  latestMigration: MigrationResult | null;
  onViewCentral: () => void;
}

export const UploadSection: React.FC<UploadSectionProps> = ({
  onUpload,
  onLoadSample,
  isProcessing,
  latestMigration,
  onViewCentral,
}) => {
  const [fwsFile, setFwsFile] = useState<File | null>(null);
  const [grantFile, setGrantFile] = useState<File | null>(null);
  const [fwsDragOver, setFwsDragOver] = useState(false);
  const [grantDragOver, setGrantDragOver] = useState(false);

  const fwsInputRef = useRef<HTMLInputElement>(null);
  const grantInputRef = useRef<HTMLInputElement>(null);

  const handleFwsFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFwsFile(e.target.files[0]);
    }
  };

  const handleGrantFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setGrantFile(e.target.files[0]);
    }
  };

  const handleFwsDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setFwsDragOver(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      setFwsFile(e.dataTransfer.files[0]);
    }
  };

  const handleGrantDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setGrantDragOver(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      setGrantFile(e.dataTransfer.files[0]);
    }
  };

  return (
    <div className="space-y-6">
      {/* Intro Banner */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 text-white shadow-sm">
        <div className="max-w-3xl">
          <h1 className="text-2xl font-bold tracking-tight text-white mb-2">
            Dual-Format CSV Intake & Centralized Normalization
          </h1>
          <p className="text-sm text-slate-300 leading-relaxed">
            Upload Federal Work Study (FWS) and Project Supply Grant research CSV files. This service deduplicates students into a centralized
            <code className="text-xs bg-slate-800 px-1.5 py-0.5 rounded text-indigo-200 ml-1">students_doing_research</code> table,
            and routes remaining application-specific attributes to relational sub-tables linked by a unique Student ID (<code className="text-xs bg-slate-800 px-1 py-0.5 rounded text-emerald-300">STU-XXXX</code>).
          </p>
        </div>

      </div>

      {/* Dual Intake Dropzones */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Card 1: Federal Work Study Intake */}
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-5 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center space-x-2">
                <span className="w-2.5 h-2.5 rounded-full bg-blue-500"></span>
                <h2 className="font-semibold text-slate-900 text-base">Federal Work Study (FWS) CSV</h2>
              </div>
              <span className="text-[11px] font-medium px-2 py-0.5 bg-blue-50 text-blue-700 rounded border border-blue-200">
                Format 1: FWS
              </span>
            </div>

            <div
              onDragOver={(e) => { e.preventDefault(); setFwsDragOver(true); }}
              onDragLeave={() => setFwsDragOver(false)}
              onDrop={handleFwsDrop}
              onClick={() => fwsInputRef.current?.click()}
              className={`border-2 border-dashed rounded-lg p-6 text-center cursor-pointer transition ${
                fwsDragOver
                  ? 'border-blue-500 bg-blue-50/50'
                  : fwsFile
                  ? 'border-emerald-400 bg-emerald-50/30'
                  : 'border-slate-300 hover:border-blue-400 hover:bg-slate-50/60'
              }`}
            >
              <input
                ref={fwsInputRef}
                type="file"
                accept=".csv"
                className="hidden"
                onChange={handleFwsFileChange}
              />
              <div className="flex flex-col items-center">
                {fwsFile ? (
                  <>
                    <FileText className="w-8 h-8 text-emerald-600 mb-2" />
                    <span className="text-xs font-semibold text-slate-800 break-all">{fwsFile.name}</span>
                    <span className="text-[11px] text-slate-500 mt-0.5">{(fwsFile.size / 1024).toFixed(1)} KB</span>
                  </>
                ) : (
                  <>
                    <Upload className="w-8 h-8 text-slate-400 mb-2" />
                    <span className="text-xs font-semibold text-slate-700">Drop FWS CSV here or click to browse</span>
                    <span className="text-[11px] text-slate-400 mt-1">Accepts standard .csv exports</span>
                  </>
                )}
              </div>
            </div>
          </div>

          <div className="mt-4 pt-4 border-t border-slate-100 flex items-center justify-between">
            <button
              id="upload-fws-btn"
              onClick={() => {
                if (fwsFile) onUpload(fwsFile, 'fws');
              }}
              disabled={!fwsFile || isProcessing}
              className="inline-flex items-center space-x-1 px-3.5 py-1.5 text-xs font-semibold bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition disabled:opacity-40"
            >
              {isProcessing ? (
                <>
                  <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                  <span>Processing...</span>
                </>
              ) : (
                <>
                  <Play className="w-3 h-3 fill-current" />
                  <span>Run Pipeline Migration</span>
                </>
              )}
            </button>
          </div>
        </div>

        {/* Card 2: Project Supply Grant Intake */}
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-5 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center space-x-2">
                <span className="w-2.5 h-2.5 rounded-full bg-violet-500"></span>
                <h2 className="font-semibold text-slate-900 text-base">Student Project Supply Grant CSV</h2>
              </div>
              <span className="text-[11px] font-medium px-2 py-0.5 bg-violet-50 text-violet-700 rounded border border-violet-200">
                Format 2: Supply Grant
              </span>
            </div>

            <div
              onDragOver={(e) => { e.preventDefault(); setGrantDragOver(true); }}
              onDragLeave={() => setGrantDragOver(false)}
              onDrop={handleGrantDrop}
              onClick={() => grantInputRef.current?.click()}
              className={`border-2 border-dashed rounded-lg p-6 text-center cursor-pointer transition ${
                grantDragOver
                  ? 'border-violet-500 bg-violet-50/50'
                  : grantFile
                  ? 'border-emerald-400 bg-emerald-50/30'
                  : 'border-slate-300 hover:border-violet-400 hover:bg-slate-50/60'
              }`}
            >
              <input
                ref={grantInputRef}
                type="file"
                accept=".csv"
                className="hidden"
                onChange={handleGrantFileChange}
              />
              <div className="flex flex-col items-center">
                {grantFile ? (
                  <>
                    <FileText className="w-8 h-8 text-emerald-600 mb-2" />
                    <span className="text-xs font-semibold text-slate-800 break-all">{grantFile.name}</span>
                    <span className="text-[11px] text-slate-500 mt-0.5">{(grantFile.size / 1024).toFixed(1)} KB</span>
                  </>
                ) : (
                  <>
                    <Upload className="w-8 h-8 text-slate-400 mb-2" />
                    <span className="text-xs font-semibold text-slate-700">Drop Grant CSV here or click to browse</span>
                    <span className="text-[11px] text-slate-400 mt-1">Accepts standard .csv exports</span>
                  </>
                )}
              </div>
            </div>
          </div>

          <div className="mt-4 pt-4 border-t border-slate-100 flex items-center justify-between">
            <button
              id="upload-grant-btn"
              onClick={() => {
                if (grantFile) onUpload(grantFile, 'grant');
              }}
              disabled={!grantFile || isProcessing}
              className="inline-flex items-center space-x-1 px-3.5 py-1.5 text-xs font-semibold bg-violet-600 hover:bg-violet-700 text-white rounded-lg transition disabled:opacity-40"
            >
              {isProcessing ? (
                <>
                  <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                  <span>Processing...</span>
                </>
              ) : (
                <>
                  <Play className="w-3 h-3 fill-current" />
                  <span>Run Pipeline Migration</span>
                </>
              )}
            </button>
          </div>
        </div>
      </div>

      {/* Migration Results Banner */}
      {latestMigration && (
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-5 animate-in fade-in duration-300">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center space-x-2">
              <CheckCircle2 className="w-5 h-5 text-emerald-600" />
              <h3 className="font-semibold text-slate-900 text-sm">
                Latest Pipeline Execution: {latestMigration.source}
              </h3>
            </div>
            <button
              onClick={onViewCentral}
              className="inline-flex items-center space-x-1 text-xs font-semibold text-indigo-600 hover:text-indigo-800"
            >
              <span>View in Central Database</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>

          {/* Quick Metrics Grid */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-4 text-center">
            <div className="bg-slate-50 p-2.5 rounded-lg border border-slate-100">
              <div className="text-xs text-slate-500">Rows Ingested</div>
              <div className="text-lg font-bold text-slate-900">{latestMigration.total_rows}</div>
            </div>
            <div className="bg-emerald-50 p-2.5 rounded-lg border border-emerald-100">
              <div className="text-xs text-emerald-700">New Students Created</div>
              <div className="text-lg font-bold text-emerald-800">{latestMigration.new_students}</div>
            </div>
            <div className="bg-amber-50 p-2.5 rounded-lg border border-amber-100">
              <div className="text-xs text-amber-700">Existing Students Matched</div>
              <div className="text-lg font-bold text-amber-800">{latestMigration.existing_students_matched}</div>
            </div>
            <div className="bg-indigo-50 p-2.5 rounded-lg border border-indigo-100">
              <div className="text-xs text-indigo-700">Sub-Table Rows Created</div>
              <div className="text-lg font-bold text-indigo-800">{latestMigration.records_inserted}</div>
            </div>
          </div>

          {/* Detailed Ingestion Log */}
          <div className="border border-slate-200 rounded-lg overflow-hidden">
            <div className="bg-slate-50 px-3 py-1.5 border-b border-slate-200 text-xs font-medium text-slate-700">
              Ingested Records & Linkage Audit
            </div>
            <div className="divide-y divide-slate-100 max-h-48 overflow-y-auto">
              {latestMigration.details.map((d, i) => (
                <div key={i} className="px-3 py-2 text-xs flex items-center justify-between hover:bg-slate-50">
                  <div className="flex items-center space-x-2">
                    <span className="font-mono font-bold text-indigo-700 bg-indigo-50 px-1.5 py-0.5 rounded border border-indigo-200">
                      {d.student_id}
                    </span>
                    <span className="font-medium text-slate-800">{d.student_name}</span>
                    <span className="text-slate-400">({d.email})</span>
                  </div>
                  <div className="flex items-center space-x-2">
                    {d.is_new ? (
                      <span className="px-2 py-0.5 bg-emerald-100 text-emerald-800 text-[10px] font-semibold rounded-full">
                        New Student Added
                      </span>
                    ) : (
                      <span className="px-2 py-0.5 bg-amber-100 text-amber-800 text-[10px] font-semibold rounded-full">
                        Deduplicated & Linked
                      </span>
                    )}
                    <span className="text-slate-500 text-[11px]">Mentor: {d.mentor || 'N/A'}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
