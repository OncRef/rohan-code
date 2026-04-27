"use client";
import React from 'react';
import { useState, useEffect } from 'react';

const Page = () => {
    const [playerName, setPlayerName] = useState('DEFAULT');
    const [data, setData] = useState([]);
    const [filter, setFilter] = useState('');
    const [loading, setLoading] = useState(false);

    async function getData(selectedPlayer, selectedFilter) {
        setLoading(true);
        try {
            const params = new URLSearchParams();
            if (selectedPlayer) params.set('player', selectedPlayer);
            if (selectedFilter) params.set('filter', selectedFilter);
            const response = await fetch(`/api/pr-trigger/stats?${params.toString()}`, { method: "GET" });
            const result = await response.json();
            setData(result.data || []);
        } catch (error) { console.error('Error fetching data:', error); setData([]) }
        finally { setLoading(false) }
    }

    useEffect(() => {
        if (playerName !== "DEFAULT") getData(playerName, filter);
        else getData('', filter);
    }, [playerName, filter]);

    return (
        <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100">
            <header className="sticky top-0 z-50 bg-white/80 backdrop-blur border-b border-slate-200 px-6 py-4">
                <div className="max-w-6xl mx-auto flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-lg bg-indigo-600 flex items-center justify-center">
                            <span className="text-white font-bold text-sm">ST</span>
                        </div>
                        <h1 className="text-lg font-semibold text-slate-800">PR Trigger Stats</h1>
                        <span className="px-3 py-1 text-xs font-medium rounded-full bg-indigo-50 text-indigo-700 border border-indigo-200">
                            {data.length} drugs
                        </span>
                    </div>
                    <div className="flex items-center gap-3">
                        <select className="px-3 py-1.5 text-sm bg-amber-50 border border-amber-200 text-amber-800 rounded-lg font-medium focus:ring-2 focus:ring-amber-300 focus:outline-none" value={playerName} onChange={e => setPlayerName(e.target.value)}>
                            <option value='DEFAULT'>All players</option>
                            <option value='tom'>Tom</option><option value='raena'>Raena</option><option value='yash'>Yash</option><option value='sneha'>Sneha</option><option value='daksh'>Daksh</option>
                        </select>
                        <select className="px-3 py-1.5 text-sm bg-slate-50 border border-slate-200 text-slate-700 rounded-lg font-medium focus:ring-2 focus:ring-slate-300 focus:outline-none" value={filter} onChange={e => setFilter(e.target.value)}>
                            <option value=''>All</option>
                            <option value='needs_review'>Needs Review</option>
                            <option value='approved'>Approved</option>
                            <option value='not_approved'>Not Approved</option>
                            <option value='locked'>Locked</option>
                        </select>
                    </div>
                </div>
            </header>

            <div className="max-w-6xl mx-auto p-6">
                {loading ? (
                    <div className="text-center py-20 text-slate-400 text-sm">Loading...</div>
                ) : data && data.length > 0 ? (
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        {data.map((drug, index) => (
                            <div key={index} className="rounded-xl border border-slate-200 bg-white overflow-hidden hover:shadow-lg transition">
                                <div className="px-5 py-4 border-b border-slate-100">
                                    <div className='flex items-center justify-between mb-1'>
                                        <h2 className="text-base font-semibold text-slate-800">{drug.generic_name || 'Unknown Drug'}</h2>
                                        <div className="flex gap-1.5">
                                            <span className={`px-2 py-0.5 rounded-full text-[10px] font-medium ${drug.approved === 'Y' ? 'bg-emerald-50 text-emerald-700 border border-emerald-200' : 'bg-red-50 text-red-700 border border-red-200'}`}>
                                                {drug.approved === 'Y' ? 'Approved' : 'Pending'}
                                            </span>
                                            <span className={`px-2 py-0.5 rounded-full text-[10px] font-medium ${drug.locked === 'Y' ? 'bg-amber-50 text-amber-700 border border-amber-200' : 'bg-slate-50 text-slate-500 border border-slate-200'}`}>
                                                {drug.locked === 'Y' ? 'Locked' : 'Unlocked'}
                                            </span>
                                            {drug.needs_review === 'Y' && (
                                                <span className="px-2 py-0.5 rounded-full text-[10px] font-medium bg-violet-50 text-violet-700 border border-violet-200">Review</span>
                                            )}
                                        </div>
                                    </div>
                                    <p className="text-xs text-slate-400 font-mono">{drug._id}</p>
                                    <div className="flex flex-wrap gap-x-4 gap-y-0.5 mt-1 text-xs text-slate-500">
                                        {drug.brand_name && <span>Brand: {drug.brand_name}</span>}
                                        {drug.submitted_by && <span>By: {drug.submitted_by}</span>}
                                        {drug.submitted_at && <span>{new Date(drug.submitted_at).toLocaleDateString()}</span>}
                                    </div>
                                    <div className="mt-2 flex gap-1.5">
                                        {drug.locked === 'Y' && (
                                            <button className="px-2 py-1 rounded-lg text-[10px] font-medium bg-amber-50 text-amber-700 border border-amber-200 hover:bg-amber-100 transition"
                                                onClick={async () => { await fetch('/api/pr-trigger/unlock', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ setId: drug._id }) }); getData(playerName, filter) }}>
                                                Unlock
                                            </button>
                                        )}
                                        {drug.approved === 'Y' && (
                                            <button className="px-2 py-1 rounded-lg text-[10px] font-medium bg-red-50 text-red-600 border border-red-200 hover:bg-red-100 transition"
                                                onClick={async () => { await fetch('/api/pr-trigger/unapprove', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ setId: drug._id }) }); getData(playerName, filter) }}>
                                                Unapprove
                                            </button>
                                        )}
                                    </div>
                                </div>
                                <div className="px-5 py-3">
                                    {drug.indications && drug.indications.length > 0 ? (
                                        <>
                                            <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">Indications ({drug.indications.length})</h3>
                                            {drug.indications.slice(0, 3).map((indication, idx) => (
                                                <div key={idx} className="mb-1.5">
                                                    <p className="text-xs font-medium text-slate-700">{indication.extracted_cancer || 'Unknown Cancer'}</p>
                                                    <p className='text-[11px] text-slate-400 line-clamp-1'>{indication.description || 'No description'}</p>
                                                </div>
                                            ))}
                                            {drug.indications.length > 3 && (
                                                <p className="text-[11px] text-slate-400">+ {drug.indications.length - 3} more</p>
                                            )}
                                        </>
                                    ) : (
                                        <p className="text-xs text-slate-400">No indications</p>
                                    )}
                                </div>
                            </div>
                        ))}
                    </div>
                ) : (
                    <div className="text-center py-20 text-slate-400 text-sm">Select a player to view their PR trigger data.</div>
                )}
            </div>
        </div>
    );
}

export default Page;
