'use client'

import React, { useState, useEffect } from 'react'
import AutoResizeTextarea from '@/components/AutoResize'

export default function Component() {
  const trialObject = { sub_cancer: '', ncts: '' }

  const indicationObject = {
    extracted_cancer: '', description: '', line_of_therapy: '', previous_tx: '',
    combined_with: '', stage: '', gene_specificity: '', rair_eligibility: '',
    resection_status: '', other: '', trials: [{ ...trialObject }]
  }

  const [drugData, setDrugData] = useState({ 'SetID': null })
  const [indications, setIndications] = useState([{ ...indicationObject }])
  const [playerName, setPlayerName] = useState('DEFAULT')
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false)
  const [brandName, setBrandName] = useState('')
  const [pendingCount, setPendingCount] = useState(null)

  const fetchPendingCount = async () => {
    try { const res = await fetch('/api/pending-count?game=ncts'); const data = await res.json(); setPendingCount(data.count) }
    catch { setPendingCount(null) }
  }

  const fetchData = async () => {
    try {
      const response = await fetch(`/api/ncts/fetch`)
      const drugDataFetched = await response.json()
      const fetchedIndications = drugDataFetched['indications']
      const updatedIndications = fetchedIndications.map(indication => ({
        ...indication,
        trials: indication.trials || [{ ...trialObject }]
      }));
      setDrugData({
        'SetID': drugDataFetched['_id'],
        'Generic Name': drugDataFetched['generic_name'],
        'F-Code': drugDataFetched['fcode'],
        'NCTs': drugDataFetched['ncts'].replaceAll(", ", "\n")
      } || drugData)
      setIndications(updatedIndications)
      setBrandName(drugDataFetched['brand_name'])
      setHasUnsavedChanges(false)
      return drugDataFetched['_id']
    } catch (error) {
      console.error('Failed to fetch data:', error)
    }
  }

  const lock = async (setId) => {
    try { await fetch('/api/ncts/lock', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ setId }) }) }
    catch (error) { console.log('Failed to lock') }
  }
  const unlock = async (setId) => {
    try { await fetch('/api/ncts/unlock', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ setId }) }) }
    catch (error) { console.log('Failed to unlock:', error) }
  }
  const flag = async (setId) => {
    try { await fetch('/api/ncts/flag', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ setId }) }) }
    catch (error) { console.log('Failed to flag:', error) }
  }

  async function handleNext() { const prevSetId = drugData['SetID']; const setId = await fetchData(); await unlock(prevSetId); await lock(setId); fetchPendingCount() }
  async function handleSkip() { const prevSetId = drugData['SetID']; const setId = await fetchData(); await flag(prevSetId); await lock(setId); fetchPendingCount() }

  useEffect(() => {
    if (confirm("Ready to start? Let's go!")) { fetchData().then((setId) => { lock(setId) }); fetchPendingCount() }
    else { window.close() }
  }, [])

  const handleIndicationChange = (index, trial_index, field, value) => {
    const newIndications = [...indications]
    newIndications[index] = {
      ...newIndications[index],
      trials: newIndications[index].trials.map((trial, i) =>
        i === trial_index ? { ...trial, [field]: value } : trial
      )
    }
    setIndications(newIndications)
    setHasUnsavedChanges(true)
  }

  const handleBrandChange = (value) => { setBrandName(value); setHasUnsavedChanges(true) }

  const addNewRow = (index, trial_index) => {
    const newIndications = [...indications]
    newIndications[index] = {
      ...newIndications[index],
      trials: [
        ...newIndications[index].trials.slice(0, trial_index + 1),
        { ...trialObject },
        ...newIndications[index].trials.slice(trial_index + 1)
      ]
    }
    setIndications(newIndications)
  }

  const handlePlayerChange = (value) => { setPlayerName(value) }

  const handleSave = async () => {
    if (playerName == 'DEFAULT') alert('Please select a player name from the dropdown')
    else {
      const confirmation = confirm('Are you sure you want to submit')
      if (confirmation) {
        try {
          const response = await fetch('/api/ncts/save-ncts', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ drugData, indications, playerName, brandName })
          })
          if (!response.ok) throw new Error('Failed to save')
          setIndications([{ ...indicationObject }])
          await handleNext();
        } catch (error) { console.log('Failed to save:', error) }
      }
    }
  }

  const handleExit = async () => {
    await fetch('/api/ncts/cleanup', { method: 'POST', headers: { 'Content-Type': 'application/json' } })
    setDrugData({ 'SetID': null }); setIndications([{ ...indicationObject }]); setBrandName('')
    setPlayerName('DEFAULT'); setHasUnsavedChanges(false)
  }

  const READONLY_FIELDS = [
    { key: 'extracted_cancer', label: 'Defined Cancer' },
    { key: 'description', label: 'Description' },
    { key: 'line_of_therapy', label: 'Line of Therapy' },
    { key: 'previous_tx', label: 'Previously Treated With' },
    { key: 'combined_with', label: 'In Combination With' },
    { key: 'stage', label: 'Stage' },
    { key: 'gene_specificity', label: 'Gene / Biomarker' },
    { key: 'rair_eligibility', label: 'Eligibility (RAIR)' },
    { key: 'resection_status', label: 'Resection Status' },
    { key: 'other', label: 'Other' },
  ]

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100">
      <header className="sticky top-0 z-50 bg-white/80 backdrop-blur border-b border-slate-200 px-6 py-3 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-teal-600 flex items-center justify-center">
            <span className="text-white font-bold text-sm">NC</span>
          </div>
          <h1 className="text-lg font-semibold text-slate-800">NCTs Game</h1>
          {pendingCount !== null && (
            <span className="px-3 py-1 text-xs font-semibold rounded-full bg-rose-50 text-rose-700 border border-rose-200">{pendingCount} pending</span>
          )}
          {drugData['Generic Name'] && (
            <span className="ml-2 px-3 py-1 text-xs font-medium rounded-full bg-teal-50 text-teal-700 border border-teal-200">
              {drugData['Generic Name']} / {brandName}
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <select className="px-3 py-1.5 text-sm bg-amber-50 border border-amber-200 text-amber-800 rounded-lg font-medium focus:ring-2 focus:ring-amber-300 focus:outline-none" value={playerName} onChange={e => handlePlayerChange(e.target.value)}>
            <option value='DEFAULT'>Choose player</option>
            <option value='tom'>Tom</option><option value='raena'>Raena</option><option value='yash'>Yash</option><option value='sneha'>Sneha</option><option value='daksh'>Daksh</option>
          </select>
          <button className="px-3 py-1.5 text-sm bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition font-medium" onClick={handleSave}>{hasUnsavedChanges ? 'Save Changes' : 'Approve'}</button>
          <button className="px-3 py-1.5 text-sm bg-amber-500 text-white rounded-lg hover:bg-amber-600 transition font-medium" onClick={() => handleSkip()}>Flag</button>
          <button className="px-3 py-1.5 text-sm bg-red-500 text-white rounded-lg hover:bg-red-600 transition font-medium" onClick={() => handleExit()}>Exit</button>
        </div>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-5 gap-0 h-[calc(100vh-57px)]">
        <div className="lg:col-span-3 overflow-y-auto p-5 space-y-4">

          {/* Drug Info */}
          <div className="rounded-xl border border-teal-200 bg-gradient-to-br from-teal-50 to-emerald-50 p-5">
            <div className="flex items-center gap-2 mb-3">
              <div className="w-2 h-2 rounded-full bg-teal-500"></div>
              <h2 className="text-xs font-semibold text-teal-700 uppercase tracking-wide">Drug Information</h2>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-x-6 gap-y-2">
              {Object.entries(drugData).map(([key, value]) => (
                <div key={key} className={`flex flex-col ${key === 'NCTs' ? 'md:col-span-2' : ''}`}>
                  <span className="text-[11px] font-medium text-teal-600 uppercase tracking-wide">{key}</span>
                  <span className="text-sm text-slate-700 whitespace-pre-line">{value || '—'}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Brand Name */}
          <div className="rounded-xl border border-slate-200 bg-white p-5">
            <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1">Brand Name</label>
            <input className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:ring-2 focus:ring-teal-200 focus:border-teal-300 focus:outline-none transition" value={brandName} onChange={(e) => handleBrandChange(e.target.value)} placeholder="Enter Brand Name" />
          </div>

          {/* Indications */}
          {indications.map((indication, index) => (
            <div key={`indication-${index}`} className="rounded-xl border-2 border-teal-200 bg-white p-5">
              <div className="flex items-center gap-2 mb-4">
                <div className="w-6 h-6 rounded-full bg-teal-600 flex items-center justify-center">
                  <span className="text-white text-xs font-bold">{index + 1}</span>
                </div>
                <h2 className="text-sm font-semibold text-slate-800">Indication {indication.extracted_cancer ? `— ${indication.extracted_cancer}` : ''}</h2>
              </div>

              <div className="space-y-4">
                {/* Clinical Trials */}
                <div>
                  <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">Clinical Trials</label>
                  {indication.trials.map((trial, trial_index) => (
                    <div key={`trial${trial_index}`} className="mb-2">
                      <div className="grid grid-cols-2 gap-2">
                        <div>
                          <div className="text-[10px] text-slate-400 mb-0.5">Sub Cancer</div>
                          <textarea rows="2" className="w-full p-2 text-sm border border-slate-200 rounded-lg focus:ring-2 focus:ring-teal-200 focus:outline-none" value={trial.sub_cancer} onChange={(e) => handleIndicationChange(index, trial_index, 'sub_cancer', e.target.value)} placeholder="Enter Sub Cancer" />
                        </div>
                        <div>
                          <div className="text-[10px] text-slate-400 mb-0.5">NCTs</div>
                          <textarea rows="2" className="w-full p-2 text-sm border border-slate-200 rounded-lg focus:ring-2 focus:ring-teal-200 focus:outline-none" value={trial.ncts} onChange={(e) => handleIndicationChange(index, trial_index, 'ncts', e.target.value)} placeholder="Enter NCTs" />
                        </div>
                      </div>
                      {trial_index === indication.trials.length - 1 && (
                        <button className="w-full mt-1 p-1.5 rounded-lg bg-slate-50 hover:bg-slate-100 text-xs text-slate-500 transition" onClick={() => addNewRow(index, trial_index)}>+ Add Trial Row</button>
                      )}
                    </div>
                  ))}
                </div>

                {/* Read-only indication fields */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {READONLY_FIELDS.filter(f => indication[f.key]).map(field => (
                    <div key={field.key} className={field.key === 'description' || field.key === 'other' ? 'md:col-span-2' : ''}>
                      <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1">{field.label}</label>
                      <AutoResizeTextarea
                        key={`${field.key}-${index}-${indication[field.key]}`}
                        content={indication[field.key]}
                        disabled={true}
                        placeholder={field.label}
                      />
                    </div>
                  ))}
                </div>
              </div>
            </div>
          ))}

          <div className="h-8"></div>
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
