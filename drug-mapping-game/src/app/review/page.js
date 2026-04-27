'use client'

import React, { useState, useEffect } from 'react'

export default function Component() {
  const indicationObject = {
    extracted_cancer: '',
    description: '',
    line_of_therapy: '',
    previous_tx: '',
    combined_with: '',
    stage: '',
    gene_specificity: '',
    rair_eligibility: '',
    resection_status: '',
    other: ''
  }
  const [drugData, setDrugData] = useState({ 'SetID': null })
  const [indications, setIndications] = useState([
    { ...indicationObject }
  ])
  const [playerName, setPlayerName] = useState('raena')
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false)
  const [pendingCount, setPendingCount] = useState(null)

  const fetchPendingCount = async () => {
    try { const res = await fetch('/api/pending-count?game=review'); const data = await res.json(); setPendingCount(data.count) }
    catch { setPendingCount(null) }
  }

  const fetchData = async () => {
    try {
      const response = await fetch(`/api/review-data/fetch`)
      const drugDataFetched = await response.json()
      const fetchedIndications = drugDataFetched['indications']
      setDrugData({
        'SetID': drugDataFetched['_id'],
        'Generic Name': drugDataFetched['generic_name'],
        'Brand Name': drugDataFetched['brand_name'],
        'F-Code': drugDataFetched['fcode']
      } || drugData)
      setIndications(fetchedIndications || [{ ...indicationObject }])
      setHasUnsavedChanges(false)
      return drugDataFetched['_id']
    } catch (error) {
      console.error('Failed to fetch data:', error)
    }
  }

  const lock = async (setId) => {
    try {
      await fetch('/api/review-data/lock', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ setId })
      })
    } catch (error) {
      console.log('Failed to lock')
    }
  }

  const unlock = async (setId) => {
    try {
      await fetch('/api/review-data/unlock', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ setId })
      })
    } catch (error) {
      console.log('Failed to unlock:', error)
    }
  }

  const flag = async (setId) => {
    try {
      await fetch('/api/review-data/flag', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ setId })
      })
    } catch (error) {
      console.log('Failed to flag:', error)
    }
  }

  async function handleNext() {
    const prevSetId = drugData['SetID'];
    const setId = await fetchData();
    await unlock(prevSetId)
    await lock(setId);
    fetchPendingCount();
  }

  async function handleSkip() {
    const prevSetId = drugData['SetID'];
    const setId = await fetchData();
    await flag(prevSetId)
    await lock(setId);
    fetchPendingCount();
  }

  useEffect(() => {
    if (confirm("Ready to start? Let's go!")) {
      fetchData().then((setId) => { lock(setId) });
      fetchPendingCount();
    } else {
      window.close()
    }
  }, [])

  const handleIndicationChange = (index, field, value) => {
    const newIndications = [...indications]
    newIndications[index] = { ...newIndications[index], [field]: value }
    setIndications(newIndications)
    setHasUnsavedChanges(true)
  }

  const addNewRow = (index) => {
    const newIndications = [...indications]
    newIndications.splice(index + 1, 0, { ...indicationObject })
    setIndications(newIndications)
  }

  const handlePlayerChange = (value) => { setPlayerName(value) }

  const handleSave = async () => {
    if (playerName == 'DEFAULT') alert('Please select a player name from the dropdown')
    else {
      const confirmation = confirm('Are you sure you want to submit')
      if (confirmation) {
        try {
          const response = await fetch('/api/review-data/save-indications', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ drugData, indications, playerName })
          })
          if (!response.ok) throw new Error('Failed to save')
          setIndications([{ ...indicationObject }])
          await handleNext();
        } catch (error) {
          console.log('Failed to save:', error)
        }
      }
    }
  }

  const handleExit = async () => {
    await fetch('/api/review-data/cleanup', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' }
    })
    setDrugData({ 'SetID': null })
    setIndications([{ ...indicationObject }])
    setPlayerName('DEFAULT')
    setHasUnsavedChanges(false)
  }

  const FIELDS = [
    { key: 'extracted_cancer', label: 'Defined Cancer', placeholder: 'Enter Defined Cancer' },
    { key: 'line_of_therapy', label: 'Line of Therapy', placeholder: 'e.g. First-Line, Adjuvant' },
    { key: 'previous_tx', label: 'Previously Treated With', placeholder: 'Prior treatments required' },
    { key: 'combined_with', label: 'In Combination With', placeholder: 'Combination drugs' },
    { key: 'stage', label: 'Stage', placeholder: 'e.g. Metastatic, Early-stage' },
    { key: 'gene_specificity', label: 'Gene / Biomarker', placeholder: 'e.g. BRAF V600E, HER2+' },
    { key: 'rair_eligibility', label: 'Eligibility (RAIR)', placeholder: 'e.g. FDA-authorized test' },
    { key: 'resection_status', label: 'Resection Status', placeholder: 'e.g. Resected, Unresectable' },
    { key: 'other', label: 'Other', placeholder: 'Additional relevant info' },
  ]

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100">
      <header className="sticky top-0 z-50 bg-white/80 backdrop-blur border-b border-slate-200 px-6 py-3 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-orange-500 flex items-center justify-center">
            <span className="text-white font-bold text-sm">RV</span>
          </div>
          <h1 className="text-lg font-semibold text-slate-800">Review Game</h1>
          {pendingCount !== null && (
            <span className="px-3 py-1 text-xs font-semibold rounded-full bg-rose-50 text-rose-700 border border-rose-200">
              {pendingCount} pending
            </span>
          )}
          {drugData['Generic Name'] && (
            <span className="ml-2 px-3 py-1 text-xs font-medium rounded-full bg-orange-50 text-orange-700 border border-orange-200">
              {drugData['Generic Name']} / {drugData['Brand Name']}
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <select
            className="px-3 py-1.5 text-sm bg-amber-50 border border-amber-200 text-amber-800 rounded-lg font-medium focus:ring-2 focus:ring-amber-300 focus:outline-none"
            value={playerName}
            onChange={e => handlePlayerChange(e.target.value)}
          >
            <option value='DEFAULT'>Choose player</option>
            <option value='tom'>Tom</option>
            <option value='raena'>Raena</option>
            <option value='yash'>Yash</option>
            <option value='sneha'>Sneha</option>
            <option value='daksh'>Daksh</option>
          </select>
          <button className="px-3 py-1.5 text-sm bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition font-medium" onClick={handleSave}>
            {hasUnsavedChanges ? 'Save Changes' : 'Approve'}
          </button>
          <button className="px-3 py-1.5 text-sm bg-amber-500 text-white rounded-lg hover:bg-amber-600 transition font-medium" onClick={() => handleSkip()}>Flag</button>
          <button className="px-3 py-1.5 text-sm bg-red-500 text-white rounded-lg hover:bg-red-600 transition font-medium" onClick={() => handleExit()}>Exit</button>
        </div>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-5 gap-0 h-[calc(100vh-57px)]">
        <div className="lg:col-span-3 overflow-y-auto p-5 space-y-4">

          {/* Drug Info Card */}
          <div className="rounded-xl border border-orange-200 bg-gradient-to-br from-orange-50 to-amber-50 p-5">
            <div className="flex items-center gap-2 mb-3">
              <div className="w-2 h-2 rounded-full bg-orange-500"></div>
              <h2 className="text-xs font-semibold text-orange-700 uppercase tracking-wide">Drug Information (Review)</h2>
            </div>
            <div className="grid grid-cols-2 gap-x-6 gap-y-2">
              {Object.entries(drugData).map(([key, value]) => (
                <div key={key} className="flex flex-col">
                  <span className="text-[11px] font-medium text-orange-600 uppercase tracking-wide">{key}</span>
                  <span className="text-sm text-slate-700">{value || '—'}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Indications */}
          {indications.map((indication, index) => (
            <div key={index} className="rounded-xl border-2 border-orange-200 bg-white p-5">
              <div className="flex items-center gap-2 mb-4">
                <div className="w-6 h-6 rounded-full bg-orange-500 flex items-center justify-center">
                  <span className="text-white text-xs font-bold">{index + 1}</span>
                </div>
                <h2 className="text-sm font-semibold text-slate-800">Indication {indication.extracted_cancer ? `— ${indication.extracted_cancer}` : ''}</h2>
              </div>

              <div className="space-y-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1">Description</label>
                  <textarea
                    className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:ring-2 focus:ring-orange-200 focus:border-orange-300 focus:outline-none transition resize-none"
                    rows="3"
                    value={indication.description}
                    onChange={(e) => handleIndicationChange(index, 'description', e.target.value)}
                    placeholder="Enter Description"
                  />
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {FIELDS.map(field => (
                    <div key={field.key}>
                      <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1">{field.label}</label>
                      <input
                        className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:ring-2 focus:ring-orange-200 focus:border-orange-300 focus:outline-none transition"
                        value={indication[field.key]}
                        onChange={(e) => handleIndicationChange(index, field.key, e.target.value)}
                        placeholder={field.placeholder}
                      />
                    </div>
                  ))}
                </div>

                <button
                  className="w-full p-2.5 rounded-xl border-2 border-dashed border-slate-200 text-slate-500 font-medium text-sm hover:bg-slate-50 transition"
                  onClick={() => addNewRow(index)}
                >
                  + Add New Indication
                </button>
              </div>
            </div>
          ))}

          <div className="h-8"></div>
        </div>

        <div className="lg:col-span-2 border-l border-slate-200 bg-white">
          <div className="px-4 py-2.5 border-b border-slate-200 text-xs font-medium text-indigo-700 bg-indigo-50/50">
            DailyMed Reference
          </div>
          <iframe src={`https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=${drugData['SetID']}`} className='w-full h-[calc(100vh-97px)]' />
        </div>
      </div>
    </div>
  )
}
