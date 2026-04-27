'use client'

import React, { useState, useEffect } from 'react'

export default function FixMoa() {
  const [drugData, setDrugData] = useState({ 'SetID': null })
  const [shortMoa, setShortMoa] = useState('')
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false)
  const [setIdInput, setSetIdInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState('')

  const fetchData = async () => {
    try {
      setLoading(true)
      const url = setIdInput?.trim()
        ? `/api/pr-trigger/fix_moa/fetch?setId=${encodeURIComponent(setIdInput.trim())}`
        : '/api/pr-trigger/fix_moa/fetch'
      const response = await fetch(url)
      const drugDataFetched = await response.json()
      if (!drugDataFetched || !drugDataFetched._id) { setMessage('No more drugs need MOA updates!'); setDrugData({ 'SetID': null }); return }
      setDrugData({
        'SetID': drugDataFetched._id, 'Application Number': drugDataFetched.application_number || '',
        'Generic Name': drugDataFetched.generic_name || '', 'Brand Name': drugDataFetched.brand_name || '',
        'SPL Title': drugDataFetched.spl_title || '', 'MOA': drugDataFetched.moa || '',
      })
      setShortMoa(drugDataFetched.short_moa || ''); setHasUnsavedChanges(false); setMessage('')
    } catch (error) { console.error('Error fetching drug data:', error); setMessage('Error fetching drug data') }
    finally { setLoading(false) }
  }

  const handleSave = async () => {
    try {
      setLoading(true)
      const response = await fetch('/api/pr-trigger/fix_moa/save', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ setId: drugData.SetID, shortMoa })
      })
      if (!response.ok) throw new Error('Failed to save')
      setHasUnsavedChanges(false); setMessage('Changes saved successfully!'); await fetchData()
    } catch (error) { console.error('Error saving changes:', error); setMessage('Error saving changes') }
    finally { setLoading(false) }
  }

  const handleNext = () => {
    if (hasUnsavedChanges) { if (window.confirm('Unsaved changes. Skip without saving?')) fetchData() }
    else fetchData()
  }

  const handleExit = () => {
    if (hasUnsavedChanges) { if (window.confirm('Unsaved changes. Exit without saving?')) window.location.href = '/' }
    else window.location.href = '/'
  }

  useEffect(() => { fetchData() }, [])

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100">
      <header className="sticky top-0 z-50 bg-white/80 backdrop-blur border-b border-slate-200 px-6 py-3 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-pink-600 flex items-center justify-center">
            <span className="text-white font-bold text-sm">MA</span>
          </div>
          <h1 className="text-lg font-semibold text-slate-800">Fix MOA</h1>
          {drugData['Generic Name'] && (
            <span className="ml-2 px-3 py-1 text-xs font-medium rounded-full bg-pink-50 text-pink-700 border border-pink-200">
              {drugData['Generic Name']} / {drugData['Brand Name']}
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <button className="px-3 py-1.5 text-sm bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition font-medium" onClick={handleSave} disabled={loading}>{loading ? 'Saving...' : 'Save'}</button>
          <button className="px-3 py-1.5 text-sm bg-slate-700 text-white rounded-lg hover:bg-slate-800 transition font-medium" onClick={handleNext} disabled={loading}>Skip</button>
          <button className="px-3 py-1.5 text-sm bg-red-500 text-white rounded-lg hover:bg-red-600 transition font-medium" onClick={handleExit} disabled={loading}>Exit</button>
        </div>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-5 gap-0 h-[calc(100vh-57px)]">
        <div className="lg:col-span-3 overflow-y-auto p-5 space-y-4">
          <div className="flex items-center gap-2">
            <input className="flex-1 px-4 py-2.5 text-sm border border-slate-200 rounded-xl bg-white focus:ring-2 focus:ring-indigo-300 focus:border-indigo-300 focus:outline-none transition placeholder-slate-400" placeholder="Enter SetID to jump to a specific drug..." value={setIdInput} onChange={(e) => setSetIdInput(e.target.value)} onKeyDown={(e) => { if (e.key === 'Enter') fetchData() }} />
            <button className="px-5 py-2.5 text-sm bg-slate-800 text-white rounded-xl hover:bg-slate-900 transition font-medium" onClick={fetchData}>Go</button>
          </div>

          {message && (
            <div className={`px-4 py-3 rounded-xl text-sm font-medium ${message.includes('Error') ? 'bg-red-50 text-red-700 border border-red-200' : 'bg-emerald-50 text-emerald-700 border border-emerald-200'}`}>
              {message}
            </div>
          )}

          <div className="rounded-xl border border-sky-200 bg-gradient-to-br from-sky-50 to-blue-50 p-5">
            <div className="flex items-center gap-2 mb-3">
              <div className="w-2 h-2 rounded-full bg-sky-500"></div>
              <h2 className="text-xs font-semibold text-sky-700 uppercase tracking-wide">Drug Information</h2>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-x-6 gap-y-2">
              {Object.entries(drugData).map(([key, value]) => (
                <div key={key} className={`flex flex-col ${key === 'MOA' || key === 'SPL Title' ? 'md:col-span-2' : ''}`}>
                  <span className="text-[11px] font-medium text-sky-600 uppercase tracking-wide">{key}</span>
                  <span className="text-sm text-slate-700 whitespace-pre-line">{value || '—'}</span>
                </div>
              ))}
            </div>
          </div>

          <div className="rounded-xl border border-slate-200 bg-white p-5">
            <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">Short MOA</label>
            <textarea
              rows="4"
              className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:ring-2 focus:ring-indigo-200 focus:border-indigo-300 focus:outline-none transition resize-none"
              value={shortMoa}
              onChange={(e) => { setShortMoa(e.target.value); setHasUnsavedChanges(true) }}
              placeholder="Enter a short, concise mechanism of action"
            />
          </div>
        </div>

        {drugData['SetID'] && (
          <div className="lg:col-span-2 border-l border-slate-200 bg-white">
            <div className="px-4 py-2.5 border-b border-slate-200 text-xs font-medium text-indigo-700 bg-indigo-50/50">DailyMed Reference</div>
            <iframe src={`https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=${drugData['SetID']}#anch_dj_dj-dj_13`} className='w-full h-[calc(100vh-97px)]' />
          </div>
        )}
      </div>
    </div>
  )
}
