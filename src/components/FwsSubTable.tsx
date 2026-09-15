import React, { useState } from 'react';
import { Search, Download, ChevronDown, ChevronUp, FileSpreadsheet, Eye, Trash2, AlertTriangle, X } from 'lucide-react';
import { FWSFundingStudent } from '../types';

interface FwsSubTableProps {
  records: FWSFundingStudent[];
  onSelectStudentId: (studentId: string) => void;
  onDeleteRecord?: (recordId: number, studentId: string) => void;
}

export const FwsSubTable: React.FC<FwsSubTableProps> = ({
  records,
  onSelectStudentId,
  onDeleteRecord,
}) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [expandedRowId, setExpandedRowId] = useState<number | null>(null);
  const [recordToDelete, setRecordToDelete] = useState<FWSFundingStudent | null>(null);

  const filtered = records.filter((r) => {
    const q = searchTerm.toLowerCase();
    return (
      r.student_id.toLowerCase().includes(q) ||
      (r.legal_first_name && r.legal_first_name.toLowerCase().includes(q)) ||
      (r.last_name && r.last_name.toLowerCase().includes(q)) ||
      (r.college && r.college.toLowerCase().includes(q)) ||
      (r.department && r.department.toLowerCase().includes(q)) ||
      (r.major && r.major.toLowerCase().includes(q)) ||
      (r.student_id_number && r.student_id_number.includes(q))
    );
  });

  const toggleRow = (id: number) => {
    setExpandedRowId(expandedRowId === id ? null : id);
  };

  return (
    <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
      {/* Header */}
      <div className="p-4 border-b border-slate-200 bg-slate-50/70 sm:flex sm:items-center sm:justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2">
            <span className="w-2.5 h-2.5 rounded-full bg-blue-500"></span>
            <h2 className="text-base font-bold text-slate-900">
              Sub-Table: <code className="text-xs bg-slate-200 px-1.5 py-0.5 rounded text-blue-900 font-mono">fws_funding_students</code>
            </h2>
          </div>
          <p className="text-xs text-slate-500 mt-0.5">
            Preserves all remaining Federal Work Study CSV fields linked via Foreign Key <code className="text-[11px] font-mono font-bold text-indigo-700">student_id</code>.
          </p>
        </div>

        <div className="mt-3 sm:mt-0 flex items-center space-x-2">
          <a
            href="/api/download/csv/fws_funding_students"
            className="inline-flex items-center space-x-1.5 px-3 py-1.5 text-xs font-medium text-slate-700 bg-white hover:bg-slate-50 border border-slate-300 rounded-lg shadow-2xs transition"
          >
            <Download className="w-3.5 h-3.5 text-slate-500" />
            <span>Export CSV</span>
          </a>
        </div>
      </div>

      {/* Search */}
      <div className="p-3 border-b border-slate-100 bg-white">
        <div className="relative w-full sm:w-80">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
          <input
            type="text"
            placeholder="Search FWS sub-table records..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-9 pr-3 py-1.5 text-xs border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-slate-50/50"
          />
        </div>
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs text-slate-700">
          <thead className="bg-slate-50 text-slate-600 font-semibold border-b border-slate-200 uppercase tracking-wider text-[11px]">
            <tr>
              <th className="py-3 px-3 w-8"></th>
              <th className="py-3 px-3">FK: Unique ID</th>
              <th className="py-3 px-3">Student Name</th>
              <th className="py-3 px-3">Student ID #</th>
              <th className="py-3 px-3">College & Major</th>
              <th className="py-3 px-3">Graduation</th>
              <th className="py-3 px-3">Award Amount</th>
              <th className="py-3 px-3">Status</th>
              <th className="py-3 px-3 text-right">Details</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {filtered.length === 0 ? (
              <tr>
                <td colSpan={9} className="text-center py-10 text-slate-400">
                  No FWS records imported yet.
                </td>
              </tr>
            ) : (
              filtered.map((row) => {
                const isExpanded = expandedRowId === row.id;
                return (
                  <React.Fragment key={row.id}>
                    <tr className={`hover:bg-blue-50/30 transition ${isExpanded ? 'bg-blue-50/20' : ''}`}>
                      <td className="py-3 px-3 text-center">
                        <button
                          onClick={() => toggleRow(row.id)}
                          className="text-slate-400 hover:text-slate-600"
                        >
                          {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                        </button>
                      </td>
                      <td className="py-3 px-3">
                        <button
                          onClick={() => onSelectStudentId(row.student_id)}
                          className="font-mono font-bold text-indigo-700 hover:text-indigo-900 bg-indigo-50 hover:bg-indigo-100 px-2 py-0.5 rounded border border-indigo-200 transition"
                          title="Click to view Central Student Profile"
                        >
                          {row.student_id}
                        </button>
                      </td>
                      <td className="py-3 px-3 font-semibold text-slate-900">
                        {row.legal_first_name} {row.last_name}
                      </td>
                      <td className="py-3 px-3 font-mono text-slate-600">
                        {row.student_id_number || '—'}
                      </td>
                      <td className="py-3 px-3">
                        <div className="font-medium text-slate-800">{row.college || '—'}</div>
                        <div className="text-[11px] text-slate-500">{row.major || row.department}</div>
                      </td>
                      <td className="py-3 px-3 text-slate-600">
                        {row.anticipated_graduation || '—'}
                      </td>
                      <td className="py-3 px-3 font-semibold text-emerald-700">
                        {row.award_amount || '—'}
                      </td>
                      <td className="py-3 px-3">
                        <span className="px-2 py-0.5 text-[10px] font-medium rounded-full bg-emerald-100 text-emerald-800">
                          {row.approval_status || 'Submitted'}
                        </span>
                      </td>
                      <td className="py-3 px-3 text-right">
                        <div className="inline-flex items-center space-x-2">
                          <button
                            onClick={() => toggleRow(row.id)}
                            className="text-xs font-medium text-blue-600 hover:text-blue-800"
                          >
                            {isExpanded ? 'Collapse' : 'Expand'}
                          </button>
                          {onDeleteRecord && (
                            <button
                              onClick={() => setRecordToDelete(row)}
                              title="Delete this FWS record (removes funding from central table)"
                              className="p-1 text-rose-600 hover:text-rose-800 hover:bg-rose-50 rounded transition"
                            >
                              <Trash2 className="w-3.5 h-3.5" />
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>

                    {/* Expandable row showing key fields */}
                    {isExpanded && (
                      <tr className="bg-slate-50/80">
                        <td colSpan={9} className="p-4 border-y border-slate-200">
                          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
                            <div className="bg-white p-3 rounded-lg border border-slate-200">
                              <h4 className="font-semibold text-slate-800 mb-2">Key FWS Details</h4>
                              <div className="grid grid-cols-2 gap-2 text-[11px]">
                                <div><span className="text-slate-400">Legal Name: </span><span className="font-medium text-slate-700">{row.legal_first_name || '—'} {row.last_name || ''}</span></div>
                                <div><span className="text-slate-400">Preferred Name: </span><span className="font-medium text-slate-700">{row.preferred_name || '—'}</span></div>
                                <div><span className="text-slate-400">Pronouns: </span><span className="font-medium text-slate-700">{row.pronouns || '—'}</span></div>
                                <div><span className="text-slate-400">Student ID #: </span><span className="font-medium text-slate-700">{row.student_id_number || '—'}</span></div>
                                <div><span className="text-slate-400">College: </span><span className="font-medium text-slate-700">{row.college || '—'}</span></div>
                                <div><span className="text-slate-400">Department: </span><span className="font-medium text-slate-700">{row.department || '—'}</span></div>
                                <div><span className="text-slate-400">Major: </span><span className="font-medium text-slate-700">{row.major || '—'}</span></div>
                                <div><span className="text-slate-400">Graduation: </span><span className="font-medium text-slate-700">{row.anticipated_graduation || '—'}</span></div>
                                <div><span className="text-slate-400">Phone: </span><span className="font-medium text-slate-700">{row.phone_number || '—'}</span></div>
                                <div><span className="text-slate-400">Award Amount: </span><span className="font-medium text-slate-700">{row.award_amount || '—'}</span></div>
                                <div><span className="text-slate-400">Status: </span><span className="font-medium text-slate-700">{row.approval_status || '—'}</span></div>
                                <div><span className="text-slate-400">Reviewer: </span><span className="font-medium text-slate-700">{row.reviewer_name || '—'}</span></div>
                              </div>
                            </div>

                            <div className="bg-white p-3 rounded-lg border border-slate-200 space-y-3">
                              <div>
                                <h4 className="font-semibold text-slate-800 mb-1">Research Duties</h4>
                                <p className="text-slate-600 whitespace-pre-line leading-relaxed">
                                  {row.research_duties_description || 'No description provided.'}
                                </p>
                              </div>
                              <div>
                                <h4 className="font-semibold text-slate-800 mb-1">Mentor & Program Details</h4>
                                <div className="grid grid-cols-2 gap-2 text-[11px]">
                                  <div><span className="text-slate-400">Faculty Mentor: </span><span className="font-medium text-slate-700">{row.faculty_mentor_first_name || '—'} {row.faculty_mentor_last_name || ''}</span></div>
                                  <div><span className="text-slate-400">Faculty College: </span><span className="font-medium text-slate-700">{row.faculty_mentor_college || '—'}</span></div>
                                  <div><span className="text-slate-400">Faculty Phone: </span><span className="font-medium text-slate-700">{row.faculty_mentor_phone || '—'}</span></div>
                                  <div><span className="text-slate-400">External Mentor: </span><span className="font-medium text-slate-700">{row.external_mentor_first_name || '—'} {row.external_mentor_last_name || ''}</span></div>
                                  <div><span className="text-slate-400">Referral Source: </span><span className="font-medium text-slate-700">{row.referral_source || '—'}</span></div>
                                  <div><span className="text-slate-400">Hire Action: </span><span className="font-medium text-slate-700">{row.initiated_hire_action || '—'}</span></div>
                                  <div><span className="text-slate-400">Voucher Created: </span><span className="font-medium text-slate-700">{row.created_voucher || '—'}</span></div>
                                  <div><span className="text-slate-400">FWS Eligible: </span><span className="font-medium text-slate-700">{row.fws_eligible || '—'}</span></div>
                                </div>
                              </div>
                            </div>
                          </div>
                        </td>
                      </tr>
                    )}
                  </React.Fragment>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      <div className="px-4 py-3 bg-slate-50 border-t border-slate-200 text-xs text-slate-500 flex justify-between items-center">
        <span>Showing {filtered.length} of {records.length} FWS records</span>
        <span>Foreign Key: <code className="font-mono text-indigo-700">student_id</code></span>
      </div>

      {/* Confirmation Modal for Sub-Table Record Deletion */}
      {recordToDelete && (
        <div className="fixed inset-0 z-50 overflow-y-auto bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl border border-slate-200 shadow-2xl max-w-md w-full p-6 animate-in fade-in zoom-in-95 duration-150">
            <div className="flex items-start space-x-3 mb-4">
              <div className="w-10 h-10 rounded-full bg-rose-100 flex items-center justify-center shrink-0 text-rose-600">
                <AlertTriangle className="w-5 h-5" />
              </div>
              <div className="flex-1">
                <h3 className="text-base font-bold text-slate-900">Delete FWS Application Record?</h3>
                <p className="text-xs text-slate-500 mt-1">
                  You are about to remove application <strong className="text-slate-800">#{recordToDelete.id}</strong> for student <code className="font-mono text-indigo-700">{recordToDelete.student_id}</code> ({recordToDelete.legal_first_name} {recordToDelete.last_name}).
                </p>
              </div>
              <button
                onClick={() => setRecordToDelete(null)}
                className="text-slate-400 hover:text-slate-600 p-1"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="bg-amber-50 border border-amber-200 rounded-xl p-3 text-xs text-amber-900 mb-5">
              <p className="font-semibold mb-1">Impact on Centralized Table:</p>
              <p className="text-[11px] text-amber-800 leading-relaxed">
                This removes the record from <code className="font-mono">fws_funding_students</code> and automatically removes the <strong>Federal Work Study</strong> funding field from the central <code className="font-mono">students_doing_research</code> profile.
              </p>
            </div>

            <div className="flex items-center justify-end space-x-2">
              <button
                onClick={() => setRecordToDelete(null)}
                className="px-3.5 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-100 rounded-lg transition"
              >
                Cancel
              </button>
              <button
                onClick={() => {
                  if (onDeleteRecord && recordToDelete) {
                    onDeleteRecord(recordToDelete.id, recordToDelete.student_id);
                  }
                  setRecordToDelete(null);
                }}
                className="px-4 py-1.5 text-xs font-semibold text-white bg-rose-600 hover:bg-rose-700 rounded-lg shadow-sm transition inline-flex items-center space-x-1.5"
              >
                <Trash2 className="w-3.5 h-3.5" />
                <span>Remove Record</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
