'use client'

import React, { useState, useEffect } from 'react'
import AutoResizeTextarea from '@/components/AutoResize'
import cloneDeep from 'lodash/cloneDeep'

export default function Component() {
  const trialObject = {
    sub_cancer: '',
    ncts: ''
  }

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
    other: '',
    broad_cancer: [],
    trials: [ { ...trialObject } ]
  }

  const [drugData, setDrugData] = useState({ 'SetID': null })
  const [indications, setIndications] = useState([
    { ...indicationObject }
  ])
  const [prInfo, setPrInfo] = useState({})
  const [currentSetId, setCurrentSetId] = useState(null)
  const [playerName, setPlayerName] = useState('DEFAULT')
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false)
  const [brandName, setBrandName] = useState('')
  const [packager, setPackager] = useState('')
  const [oldIndications, setOldIndications] = useState([])
  const [moa, setMoa] = useState('')
  const [short_moa, setShortMoa] = useState('')
  const [fcode, setFcode] = useState('')
  const [effectiveDate, setEffectiveDate] = useState('')
  const [drugComments, setDrugComments] = useState('')
  const [showInfo, setShowInfo] = useState(false)
  const [isEditingOldNcts, setIsEditingOldNcts] = useState(false)
  const [setIdInput, setSetIdInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [sidebarTab, setSidebarTab] = useState('dailymed')
  const [pendingCount, setPendingCount] = useState(null)

  const handleShortMoaChange = (value) => {
    setShortMoa(value)
    setHasUnsavedChanges(true)
  }

  const BROAD_CANCER_OPTIONS = [
    "Adrenal Cancer and Neuroendocrine Tumors",
    "Ampullary Adenocarcinoma",
    "Anal Cancer",
    "Appendix Cancer",
    "Bladder Cancer",
    "Bone and Joint Cancers",
    "Brain and Other Nervous System",
    "Breast Cancer",
    "Castleman Disease",
    "Colorectal Cancer",
    "Esophageal Cancer",
    "Gallbladder Cancer",
    "Gastric (Stomach) Cancer",
    "Gastrointestinal Stromal Tumors",
    "Gestational Cancers",
    "Gynecological Cancers",
    "Head and Neck Cancers",
    "Hematological Malignancies",
    "Kidney (Renal) and Urethral Cancers",
    "Liver and Bile Duct Cancers",
    "Lung Cancers",
    "Mesothelioma",
    "Neuroblastoma",
    "Occult Primary",
    "Ocular Cancers",
    "Pancreatic Cancer",
    "Pediatric Cancers",
    "Penile Cancer",
    "Prostate Cancer",
    "Skin Cancers",
    "Small Instestine Cancers",
    "Soft Tissue Cancers (including Heart)",
    "Specific Syndromes",
    "Testicular Cancer",
    "Thymic Cancers",
    "Thyroid Cancer"
  ]

  const fetchData = async () => {
    try {
      const url = setIdInput?.trim() ? `/api/pr-trigger/play?setId=${encodeURIComponent(setIdInput.trim())}` : `/api/pr-trigger/play`
      const response = await fetch(url)
      const drugDataFetched = await response.json()
      const normalizedEffectiveDate = drugDataFetched['effective_date']
        ? `${drugDataFetched['effective_date']}`
        : ''
      setDrugData({
        'SetID': drugDataFetched['_id'],
        'Generic Name': drugDataFetched['generic_name'],
        'Brand Name': drugDataFetched['brand_name'],
        'SPL Title': drugDataFetched['dailymed_spl_title'],
        'moa': drugDataFetched['moa'],
        'F-Code': drugDataFetched['fcode'] || '',
        'Effective Date': normalizedEffectiveDate
      } || drugData)
      setOldIndications(drugDataFetched['indications'] || [])
      setIndications([cloneDeep(indicationObject)])
      setPrInfo({
        'Generic Name': drugDataFetched['generic_name'] || '',
        'Application Number': drugDataFetched['application_number'] || drugDataFetched['NDA_AppNo'] || '',
        'Brand Name': drugDataFetched['brand_name'] || '',
        'Packager': drugDataFetched['packager'] || '',
        'Approval Date': drugDataFetched['pr_approval_date'] || '',
        'Extracted Cancer': drugDataFetched['pr_extracted_cancer'] || '',
        'Pharm Class':  Array.isArray(drugDataFetched['pharm_class'])
        ? drugDataFetched['pharm_class'].join(', ')
        : (drugDataFetched['pharm_class'] || ''),
        'Press Release NCTS': Array.isArray(drugDataFetched['ncts'])
          ? drugDataFetched['ncts'].join(', ')
          : (drugDataFetched['ncts'] || ''),
        'moa': drugDataFetched['moa'] || '',
        'Source Link for Press': drugDataFetched['pr_source_link'] || '',
      })
      setCurrentSetId(drugDataFetched['_id'])
      setBrandName(drugDataFetched['brand_name'])
      setMoa(drugDataFetched['moa'] || '')
      setShortMoa(drugDataFetched['short_moa'] || '')
      setPackager(drugDataFetched['packager'] || '')
      setFcode(drugDataFetched['fcode'] || '')
      setEffectiveDate(normalizedEffectiveDate)
      setDrugComments(drugDataFetched['game_comments'] || '')
      setHasUnsavedChanges(false)
      return drugDataFetched['_id']
    } catch (error) {
      console.error('Failed to fetch data:', error)
    }
  }

  const lock = async (setId) => {
    try {
      await fetch('/api/pr-trigger/lock', {
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
      await fetch('/api/pr-trigger/unlock', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ setId })
      })
    } catch (error) {
      console.log('Failed to unlock:', error)
    }
  }

  async function handleNext() {
    const prevSetId = drugData['SetID'];
    const setId = await fetchData();
    await unlock(prevSetId)
    await lock(setId);
    fetchPendingCount();
  }

  const fetchPendingCount = async () => {
    try {
      const res = await fetch('/api/pending-count?game=pr-trigger')
      const data = await res.json()
      setPendingCount(data.count)
    } catch { setPendingCount(null) }
  }

  useEffect(() => {
    if (confirm("Ready to start? Let's go!")) {
      fetch('/api/pr-trigger/cleanup', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      }).then(() => {
        fetchData().then((setId) => { if (!setIdInput?.trim()) { lock(setId) } });
        fetchPendingCount();
      })
    } else {
      window.close()
    }
  }, [])

  const handleTrialChange = (index, trial_index, field, value) => {
    const newIndications = cloneDeep(indications);
    newIndications[index].trials[trial_index][field] = value;
    setIndications(newIndications);
    setHasUnsavedChanges(true);
  };

  const handleIndicationChange = (index, field, value) => {
    const newIndications = cloneDeep(indications);
    newIndications[index][field] = value;
    setIndications(newIndications);
    setHasUnsavedChanges(true);
  }

  const handleBroadCancerChange = (index, selectedList) => {
    const newIndications = cloneDeep(indications);
    newIndications[index].broad_cancer = selectedList;
    setIndications(newIndications);
    setHasUnsavedChanges(true);
  }

  const handleBrandChange = (value) => { setBrandName(value); setHasUnsavedChanges(true) }
  const handleMoaChange = (value) => { setMoa(value); setHasUnsavedChanges(true) }
  const handlePackagerChange = (value) => { setPackager(value); setHasUnsavedChanges(true) }
  const handleFcodeChange = (value) => { setFcode(value); setHasUnsavedChanges(true) }
  const handleEffectiveDateChange = (value) => { setEffectiveDate(value); setHasUnsavedChanges(true) }
  const handleCommentChange = (value) => { setDrugComments(value); setHasUnsavedChanges(true) }
  const handleToggleEditOldNcts = () => { setIsEditingOldNcts(!isEditingOldNcts) }

  const handleOldTrialChange = (indicationIndex, trialIndex, field, value) => {
    const newIndications = [...oldIndications]
    if (!newIndications[indicationIndex].trials) newIndications[indicationIndex].trials = []
    if (!newIndications[indicationIndex].trials[trialIndex]) newIndications[indicationIndex].trials[trialIndex] = {}
    if (field === 'ncts') {
      const nctValues = value.split(/[\n,]/).map(n => n.trim()).filter(n => n)
      newIndications[indicationIndex].trials[trialIndex][field] = nctValues.map(nctId => ({ nctId }))
    } else {
      newIndications[indicationIndex].trials[trialIndex][field] = value
    }
    setOldIndications(newIndications)
    setHasUnsavedChanges(true)
  }

  const handleOldIndicationFieldChange = (index, field, value) => {
    const newIndications = [...oldIndications]
    newIndications[index] = { ...newIndications[index], [field]: value }
    setOldIndications(newIndications)
    setHasUnsavedChanges(true)
  }

  const handleDeleteOldIndication = (indIdx) => {
    const updated = cloneDeep(oldIndications)
    updated.splice(indIdx, 1)
    setOldIndications(updated)
  }

  const handleSaveOldNcts = async () => {
    try {
      const response = await fetch('/api/pr-trigger/save-old', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ setId: currentSetId, oldIndications })
      })
      if (!response.ok) throw new Error('Failed to save old NCTs')
      alert('Old NCTs saved successfully')
      setIsEditingOldNcts(false)
    } catch (e) {
      alert('Error saving old NCTs: ' + e.message)
    }
  }

  const handleNeedsReview = async () => {
    if (playerName === 'DEFAULT') { alert('Please select a player name before marking for review'); return }
    if (confirm('Mark this drug as needing review? It will be approved but flagged for review.')) {
      try {
        const response = await fetch('/api/pr-trigger/save', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ drugData, indications, playerName, brandName, moa, packager, drugComments, fcode, effectiveDate, needsReview: true })
        });
        if (!response.ok) throw new Error('Failed to mark for review');
        await handleNext();
      } catch (error) {
        console.error('Review marking error:', error);
        alert('Failed to mark for review: ' + error.message);
      }
    }
  }

  const handleReview = async () => {
    if (playerName === 'DEFAULT') { alert('Please select a player name before reviewing'); return }
    if (confirm('Remove needs review flag and resubmit this drug?')) {
      try {
        const response = await fetch('/api/pr-trigger/save', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ drugData, indications, playerName, brandName, moa, packager, drugComments, fcode, effectiveDate, removeNeedsReview: true })
        });
        if (!response.ok) throw new Error('Failed to review and resubmit');
        await handleNext();
      } catch (error) {
        console.error('Review error:', error);
        alert('Failed to review: ' + error.message);
      }
    }
  }

  const addNewRow = () => {
    setIndications(prevIndications => [...cloneDeep(prevIndications), cloneDeep(indicationObject)]);
    setHasUnsavedChanges(true);
  };

  const addNewTrialRow = (index, trial_index) => {
    const newIndications = cloneDeep(indications);
    newIndications[index].trials.splice(trial_index + 1, 0, cloneDeep(trialObject));
    setIndications(newIndications);
  };

  const handlePlayerChange = (value) => { setPlayerName(value) }

  // AI Autofill - sends description + all press release context to GPT-4o
  const handleAutofill = async (index) => {
    const desc = indications[index]['description'] || '';
    const cancer = indications[index]['extracted_cancer'] || prInfo['Extracted Cancer'] || '';
    if (desc.length <= 50) { alert('Description is too short to send to AI. Please paste the full indication text.'); return }
    try {
      setIsLoading(true)

      // Run both in parallel: OpenAI autofill + Gemini NCT extraction from DailyMed Section 14
      const [autofillResponse, nctResponse] = await Promise.all([
        fetch('/api/pr-trigger/autofill', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            cancer,
            desc,
            moa: prInfo['moa'] || moa || '',
            ncts: prInfo['Press Release NCTS'] || '',
            pharmClass: prInfo['Pharm Class'] || '',
            sourceLink: prInfo['Source Link for Press'] || '',
            approvalDate: prInfo['Approval Date'] || '',
            brandName: prInfo['Brand Name'] || brandName || '',
            genericName: prInfo['Generic Name'] || drugData['Generic Name'] || ''
          })
        }),
        fetch('/api/pr-trigger/extract-ncts', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ setId: drugData['SetID'], indicationDescription: desc })
        })
      ])

      const result = await autofillResponse.json();
      if (result.error) { alert('AI autofill failed: ' + result.error); setIsLoading(false); return }

      const newIndications = cloneDeep(indications)
      // Merge autofill result into indication
      const { broad_cancer, trials, ...scalarFields } = result
      newIndications[index] = { ...newIndications[index], ...scalarFields }
      if (Array.isArray(broad_cancer) && broad_cancer.length > 0) {
        newIndications[index].broad_cancer = broad_cancer
      }
      if (Array.isArray(trials) && trials.length > 0) {
        newIndications[index].trials = trials.map(t => ({
          sub_cancer: t.sub_cancer || '',
          ncts: t.ncts || ''
        }))
      }

      // Merge Gemini NCT extraction — all NCTs from DailyMed Section 14
      try {
        const nctResult = await nctResponse.json();
        if (nctResult.ncts && nctResult.ncts.length > 0) {
          // Build trial rows from all NCTs found in Section 14
          const nctTrials = nctResult.ncts.map(nct => ({
            sub_cancer: nct.indication || '',
            ncts: `${nct.nctId}${nct.trialName ? ` (${nct.trialName})` : ''}`
          }))
          // If autofill already set trials, merge; otherwise replace
          const existingTrials = newIndications[index].trials || []
          const hasContent = existingTrials.some(t => t.sub_cancer?.trim() || t.ncts?.trim())
          if (hasContent) {
            // Append NCTs that aren't already in the autofill trials
            const existingNctIds = existingTrials.map(t => t.ncts || '').join(' ').toUpperCase()
            const uniqueNewTrials = nctTrials.filter(t => !existingNctIds.includes(t.ncts.split(' ')[0].toUpperCase()))
            newIndications[index].trials = [...existingTrials, ...uniqueNewTrials]
          } else {
            newIndications[index].trials = nctTrials
          }
        }
        console.log('NCT extraction from Section 14:', nctResult.ncts)
      } catch (nctError) {
        console.warn('NCT extraction failed (non-blocking):', nctError)
      }

      setIndications(newIndications)
      setHasUnsavedChanges(true)
      setIsLoading(false)
    } catch (error) {
      console.error('Autofill error:', error);
      alert('AI autofill failed. Check console for details.');
      setIsLoading(false)
    }
  }

  const handleSave = async () => {
    if (playerName === 'DEFAULT') { alert('Please select a player name from the dropdown'); return }
    const confirmation = confirm('Are you sure you want to submit?')
    if (!confirmation) return
    try {
      const saveResponse = await fetch('/api/pr-trigger/save', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ drugData, indications, playerName, brandName, moa, packager, drugComments, fcode, effectiveDate })
      })
      if (!saveResponse.ok) throw new Error('Failed to save data')
      setDrugComments('')
      setIndications([cloneDeep(indicationObject)])
      setHasUnsavedChanges(false)
      alert('Changes saved successfully!')
      await handleNext()
    } catch (error) {
      console.error('Error during save process:', error)
      alert('Failed to save: ' + error.message)
    }
  }

  const handleExit = async () => {
    await fetch('/api/pr-trigger/cleanup', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' }
    })
    setDrugData({ 'SetID': null })
    setIndications([cloneDeep(indicationObject)])
    setBrandName('')
    setMoa('')
    setPackager('')
    setPlayerName('DEFAULT')
    setDrugComments('')
    setCurrentSetId(null)
    setHasUnsavedChanges(false)
  }

  // --- RENDER ---
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100">
      {/* Top Nav Bar */}
      <header className="sticky top-0 z-50 bg-white/80 backdrop-blur border-b border-slate-200 px-6 py-3 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-indigo-600 flex items-center justify-center">
            <span className="text-white font-bold text-sm">PR</span>
          </div>
          <h1 className="text-lg font-semibold text-slate-800">Press Release Trigger</h1>
          {pendingCount !== null && (
            <span className="px-3 py-1 text-xs font-semibold rounded-full bg-rose-50 text-rose-700 border border-rose-200">
              {pendingCount} pending
            </span>
          )}
          {drugData['Generic Name'] && (
            <span className="ml-2 px-3 py-1 text-xs font-medium rounded-full bg-indigo-50 text-indigo-700 border border-indigo-200">
              {drugData['Generic Name']} / {brandName || drugData['Brand Name']}
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
            {hasUnsavedChanges ? 'Save Changes' : 'Submit'}
          </button>
          <button className="px-3 py-1.5 text-sm bg-violet-500 text-white rounded-lg hover:bg-violet-600 transition font-medium" onClick={handleNeedsReview}>Needs Review</button>
          <button className="px-3 py-1.5 text-sm bg-amber-500 text-white rounded-lg hover:bg-amber-600 transition font-medium" onClick={handleReview}>Review</button>
          <button className="px-3 py-1.5 text-sm bg-slate-700 text-white rounded-lg hover:bg-slate-800 transition font-medium" onClick={() => handleNext()}>Skip</button>
          <button className="px-3 py-1.5 text-sm bg-emerald-500 text-white rounded-lg hover:bg-emerald-600 transition font-medium" onClick={() => window.open('/pr-trigger/stats', '_blank')}>Stats</button>
          <button className="px-3 py-1.5 text-sm bg-red-500 text-white rounded-lg hover:bg-red-600 transition font-medium" onClick={() => handleExit()}>Exit</button>
        </div>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-5 gap-0 h-[calc(100vh-57px)]">
        {/* Left Panel - Scrollable */}
        <div className="lg:col-span-3 overflow-y-auto p-5 space-y-4">

          {/* Jump to SetID */}
          <div className="flex items-center gap-2">
            <input
              className="flex-1 px-4 py-2.5 text-sm border border-slate-200 rounded-xl bg-white focus:ring-2 focus:ring-indigo-300 focus:border-indigo-300 focus:outline-none transition placeholder-slate-400"
              placeholder="Enter SetID to jump to a specific drug..."
              value={setIdInput}
              onChange={(e) => setSetIdInput(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter') { fetchData() } }}
            />
            <button className="px-5 py-2.5 text-sm bg-slate-800 text-white rounded-xl hover:bg-slate-900 transition font-medium" onClick={() => fetchData()}>Go</button>
            <button
              className="px-4 py-2.5 text-sm text-slate-500 border border-slate-200 rounded-xl hover:bg-slate-50 transition"
              onClick={() => setShowInfo(!showInfo)}
            >
              {showInfo ? 'Hide Guide' : 'Guide'}
            </button>
          </div>

          {/* Info Guide */}
          {showInfo && (
            <div className="rounded-xl border border-indigo-100 bg-indigo-50/50 p-5">
              <h3 className="text-sm font-semibold text-indigo-800 mb-3">Button Guide</h3>
              <div className="grid grid-cols-2 gap-2 text-xs">
                {[
                  { label: 'Submit', color: 'bg-indigo-600', desc: 'Saves and approves the drug' },
                  { label: 'Needs Review', color: 'bg-violet-500', desc: 'Approves but flags for review' },
                  { label: 'Review', color: 'bg-amber-500', desc: 'Removes review flag, resubmits' },
                  { label: 'Skip', color: 'bg-slate-700', desc: 'Next drug without saving' },
                  { label: 'AI Autofill', color: 'bg-gradient-to-r from-indigo-500 to-purple-500', desc: 'GPT-4o extracts all fields from description + context' },
                  { label: 'Exit', color: 'bg-red-500', desc: 'Exit the game' },
                ].map(item => (
                  <div key={item.label} className="flex items-start gap-2">
                    <span className={`shrink-0 mt-0.5 px-2 py-0.5 ${item.color} text-white rounded text-[10px] font-medium`}>{item.label}</span>
                    <span className="text-slate-600">{item.desc}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Drug Info Card (Blue) */}
          <div className="rounded-xl border border-sky-200 bg-gradient-to-br from-sky-50 to-blue-50 p-5">
            <div className="flex items-center gap-2 mb-3">
              <div className="w-2 h-2 rounded-full bg-sky-500"></div>
              <h2 className="text-xs font-semibold text-sky-700 uppercase tracking-wide">Drug Information (DailyMed)</h2>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-x-6 gap-y-2">
              {Object.entries(drugData).map(([key, value]) => (
                <div key={key} className={`flex flex-col ${key === 'moa' ? 'md:col-span-2' : ''}`}>
                  <span className="text-[11px] font-medium text-sky-600 uppercase tracking-wide">{key}</span>
                  <span className="text-sm text-slate-700 whitespace-pre-line break-words">{value || '—'}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Press Release Card (Yellow) */}
          <div className="rounded-xl border border-amber-200 bg-gradient-to-br from-amber-50 to-yellow-50 p-5">
            <div className="flex items-center gap-2 mb-3">
              <div className="w-2 h-2 rounded-full bg-amber-500"></div>
              <h2 className="text-xs font-semibold text-amber-700 uppercase tracking-wide">Press Release Info (Provisional)</h2>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-x-6 gap-y-2">
              {Object.entries(prInfo).map(([key, value]) => (
                <div key={key} className={`flex flex-col ${(key === 'moa' || key === 'Source Link for Press') ? 'md:col-span-2' : ''}`}>
                  <span className="text-[11px] font-medium text-amber-600 uppercase tracking-wide">{key}</span>
                  {key === 'Source Link for Press' && value ? (
                    <a href={value} target="_blank" rel="noopener noreferrer" className="text-sm text-indigo-600 hover:underline break-all">{value}</a>
                  ) : (
                    <span className="text-sm text-slate-700 whitespace-pre-line break-words">{value || '—'}</span>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* Editable Drug Fields (Red -> now clean cards) */}
          <div className="rounded-xl border border-slate-200 bg-white p-5">
            <div className="flex items-center gap-2 mb-4">
              <div className="w-2 h-2 rounded-full bg-rose-500"></div>
              <h2 className="text-xs font-semibold text-rose-600 uppercase tracking-wide">Editable Drug Fields</h2>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {[
                { label: 'Brand Name', value: brandName, onChange: handleBrandChange },
                { label: 'Packager', value: packager, onChange: handlePackagerChange },
                { label: 'F-Code', value: fcode, onChange: handleFcodeChange },
                { label: 'Effective Date', value: effectiveDate, onChange: handleEffectiveDateChange },
              ].map(field => (
                <div key={field.label}>
                  <label className="block text-xs font-medium text-slate-500 mb-1">{field.label}</label>
                  <input
                    className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:ring-2 focus:ring-indigo-300 focus:border-indigo-300 focus:outline-none transition"
                    value={field.value}
                    onChange={(e) => field.onChange(e.target.value)}
                    placeholder={`Enter ${field.label}`}
                  />
                </div>
              ))}
              <div className="md:col-span-2">
                <label className="block text-xs font-medium text-slate-500 mb-1">MOA</label>
                <textarea
                  rows="3"
                  className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:ring-2 focus:ring-indigo-300 focus:border-indigo-300 focus:outline-none transition resize-none"
                  value={moa}
                  onChange={(e) => handleMoaChange(e.target.value)}
                  placeholder="Enter MOA"
                />
              </div>
              <div className="md:col-span-2">
                <label className="block text-xs font-medium text-slate-500 mb-1">Short MOA</label>
                <input
                  className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:ring-2 focus:ring-indigo-300 focus:border-indigo-300 focus:outline-none transition"
                  value={short_moa}
                  onChange={(e) => handleShortMoaChange(e.target.value)}
                  placeholder="Enter Short MOA"
                />
              </div>
            </div>
          </div>

          {/* Old Indications */}
          {oldIndications.length > 0 && (
            <div className="rounded-xl border border-slate-200 bg-white p-5">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                  <div className="w-2 h-2 rounded-full bg-slate-400"></div>
                  <h2 className="text-xs font-semibold text-slate-600 uppercase tracking-wide">Existing Indications ({oldIndications.length})</h2>
                </div>
                <div className="flex gap-2">
                  <button className="px-3 py-1.5 text-xs rounded-lg bg-slate-100 text-slate-700 hover:bg-slate-200 transition font-medium" onClick={handleToggleEditOldNcts}>
                    {isEditingOldNcts ? 'Cancel Edit' : 'Edit'}
                  </button>
                  {isEditingOldNcts && (
                    <button className="px-3 py-1.5 text-xs rounded-lg bg-indigo-600 text-white hover:bg-indigo-700 transition font-medium" onClick={handleSaveOldNcts}>Save Changes</button>
                  )}
                </div>
              </div>
              <div className="space-y-3">
                {oldIndications.map((indication, index) => (
                  <div key={`${currentSetId}-old-indication-${index}`} className="rounded-lg border border-slate-100 bg-slate-50/50 p-4">
                    <div className="flex justify-between items-center mb-3">
                      <span className="text-xs font-semibold text-slate-500">#{index + 1} — {indication.extracted_cancer || 'Untitled'}</span>
                      {isEditingOldNcts && (
                        <button className="text-[10px] px-2 py-1 rounded bg-red-100 text-red-600 hover:bg-red-200 transition" onClick={() => handleDeleteOldIndication(index)}>Delete</button>
                      )}
                    </div>

                    {isEditingOldNcts ? (
                      <div className="space-y-3">
                        <div className="rounded-lg border border-slate-200 bg-white p-3">
                          <div className="text-xs font-medium text-slate-500 mb-2">Clinical Trials</div>
                          {(indication.trials || []).map((trial, trialIndex) => (
                            <div key={`old-trial-${index}-${trialIndex}`} className="mb-3">
                              <div className="grid grid-cols-2 gap-2 mb-1">
                                <div>
                                  <div className="text-[10px] text-slate-400 mb-0.5">Sub Cancer</div>
                                  <textarea rows="2" className="w-full p-2 text-sm border border-slate-200 rounded-lg" value={trial.sub_cancer || ''} onChange={(e) => handleOldTrialChange(index, trialIndex, 'sub_cancer', e.target.value)} placeholder="Sub Cancer" />
                                </div>
                                <div>
                                  <div className="text-[10px] text-slate-400 mb-0.5">NCTs</div>
                                  <textarea rows="2" className="w-full p-2 text-sm border border-slate-200 rounded-lg" value={Array.isArray(trial.ncts) ? trial.ncts.map(n => n.nctId).join('\n') : trial.ncts || ''} onChange={(e) => handleOldTrialChange(index, trialIndex, 'ncts', e.target.value)} placeholder="NCTs" />
                                </div>
                              </div>
                              <button className="text-[10px] px-2 py-0.5 rounded bg-red-50 text-red-500 hover:bg-red-100" onClick={() => { const newTrials = [...indication.trials]; newTrials.splice(trialIndex, 1); handleOldIndicationFieldChange(index, 'trials', newTrials) }}>Remove Trial</button>
                            </div>
                          ))}
                          <button className="w-full p-1.5 rounded-lg bg-slate-50 hover:bg-slate-100 text-xs text-slate-600 transition" onClick={() => { const newTrials = [...(indication.trials || []), { sub_cancer: '', ncts: '' }]; handleOldIndicationFieldChange(index, 'trials', newTrials) }}>+ Add Trial</button>
                        </div>
                        <div className="grid grid-cols-2 gap-3">
                          <div>
                            <div className="text-[10px] text-slate-400 mb-0.5">Extracted Cancer</div>
                            <textarea rows="2" className="w-full p-2 text-sm border border-slate-200 rounded-lg" value={indication.extracted_cancer || ''} onChange={(e) => handleOldIndicationFieldChange(index, 'extracted_cancer', e.target.value)} />
                          </div>
                          <div>
                            <div className="text-[10px] text-slate-400 mb-0.5">Broad Cancer</div>
                            <div className="flex flex-wrap gap-1 mb-1">
                              {Array.isArray(indication.broad_cancer) && indication.broad_cancer.map((bc, bcIdx) => (
                                <span key={`old-bc-chip-${index}-${bcIdx}`} className="px-2 py-0.5 text-[10px] rounded-full bg-indigo-50 text-indigo-600 border border-indigo-200">{bc}</span>
                              ))}
                            </div>
                            <select multiple className="w-full p-2 text-xs border border-slate-200 rounded-lg bg-slate-50" value={Array.isArray(indication.broad_cancer) ? indication.broad_cancer : []} onChange={(e) => { const selected = Array.from(e.target.selectedOptions).map(o => o.value); handleOldIndicationFieldChange(index, 'broad_cancer', selected) }}>
                              {BROAD_CANCER_OPTIONS.map((opt) => (<option key={`old-bc-opt-${index}-${opt}`} value={opt}>{opt}</option>))}
                            </select>
                          </div>
                          <div className="col-span-2">
                            <div className="text-[10px] text-slate-400 mb-0.5">Description</div>
                            <textarea rows="3" className="w-full p-2 text-sm border border-slate-200 rounded-lg" value={indication.description || ''} onChange={(e) => handleOldIndicationFieldChange(index, 'description', e.target.value)} />
                          </div>
                          {['line_of_therapy', 'previous_tx', 'combined_with', 'stage', 'gene_specificity', 'rair_eligibility', 'resection_status'].map(field => (
                            <div key={`old-edit-${index}-${field}`}>
                              <div className="text-[10px] text-slate-400 mb-0.5">{field.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}</div>
                              <input className="w-full p-2 text-sm border border-slate-200 rounded-lg" value={indication[field] || ''} onChange={(e) => handleOldIndicationFieldChange(index, field, e.target.value)} />
                            </div>
                          ))}
                          <div className="col-span-2">
                            <div className="text-[10px] text-slate-400 mb-0.5">Other</div>
                            <textarea rows="2" className="w-full p-2 text-sm border border-slate-200 rounded-lg" value={indication.other || ''} onChange={(e) => handleOldIndicationFieldChange(index, 'other', e.target.value)} />
                          </div>
                        </div>
                      </div>
                    ) : (
                      <div className="space-y-2">
                        {indication.trials && indication.trials.length > 0 && (
                          <div>
                            {indication.trials.map((trial, tIdx) => (
                              <div key={`view-trial-${index}-${tIdx}`} className="text-xs p-2 rounded bg-white border border-slate-100 mb-1">
                                <span className="font-medium text-slate-500">Sub Cancer:</span> {trial.sub_cancer || '—'} &nbsp;|&nbsp;
                                <span className="font-medium text-slate-500">NCTs:</span> {Array.isArray(trial.ncts) ? trial.ncts.map(n => n.nctId).join(', ') : trial.ncts || '—'}
                              </div>
                            ))}
                          </div>
                        )}
                        <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs">
                          {[
                            ['Description', indication.description, true],
                            ['Broad Cancer', Array.isArray(indication.broad_cancer) ? indication.broad_cancer.join(', ') : indication.broad_cancer],
                            ['Line of Therapy', indication.line_of_therapy],
                            ['Previous Tx', indication.previous_tx],
                            ['Combined With', indication.combined_with],
                            ['Stage', indication.stage],
                            ['Gene/Biomarker', indication.gene_specificity],
                            ['RAIR Eligibility', indication.rair_eligibility],
                            ['Resection Status', indication.resection_status],
                            ['Other', indication.other, true],
                          ].map(([label, val, wide]) => (
                            <div key={`view-${index}-${label}`} className={wide ? 'col-span-2' : ''}>
                              <span className="font-medium text-slate-400">{label}:</span>{' '}
                              <span className="text-slate-600">{val || '—'}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* New Indications Form */}
          {indications.map((indication, index) => (
            <div key={`${currentSetId}-indication-${index}`} className="rounded-xl border-2 border-indigo-200 bg-white p-5">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                  <div className="w-6 h-6 rounded-full bg-indigo-600 flex items-center justify-center">
                    <span className="text-white text-xs font-bold">{index + 1}</span>
                  </div>
                  <h2 className="text-sm font-semibold text-slate-800">New Indication {indication.extracted_cancer ? `— ${indication.extracted_cancer}` : ''}</h2>
                </div>
                <button
                  className={`px-4 py-2 text-xs font-semibold rounded-lg text-white transition ${isLoading ? 'bg-slate-400 cursor-wait' : 'bg-gradient-to-r from-indigo-500 to-purple-500 hover:from-indigo-600 hover:to-purple-600 shadow-sm'}`}
                  onClick={() => handleAutofill(index)}
                  disabled={isLoading}
                >
                  {isLoading ? 'AI Processing...' : 'AI Autofill'}
                </button>
              </div>

              <div className="space-y-4">
                {/* Clinical Trials */}
                <div>
                  <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">Clinical Trials</label>
                  {indication.trials.map((trial, trial_index) => (
                    <div key={`${currentSetId}-indication-${index}-trial${trial_index}`} className="mb-2">
                      <div className="grid grid-cols-2 gap-2">
                        <div>
                          <div className="text-[10px] text-slate-400 mb-0.5">Sub Cancer</div>
                          <textarea rows="2" className="w-full p-2 text-sm border border-slate-200 rounded-lg focus:ring-2 focus:ring-indigo-200 focus:outline-none" value={trial.sub_cancer} onChange={(e) => handleTrialChange(index, trial_index, 'sub_cancer', e.target.value)} placeholder="Enter Sub Cancer" />
                        </div>
                        <div>
                          <div className="text-[10px] text-slate-400 mb-0.5">NCTs</div>
                          <textarea rows="2" className="w-full p-2 text-sm border border-slate-200 rounded-lg focus:ring-2 focus:ring-indigo-200 focus:outline-none" value={trial.ncts} onChange={(e) => handleTrialChange(index, trial_index, 'ncts', e.target.value)} placeholder="Enter NCTs" />
                        </div>
                      </div>
                      {trial_index === indication.trials.length - 1 && (
                        <button className="w-full mt-1 p-1.5 rounded-lg bg-slate-50 hover:bg-slate-100 text-xs text-slate-500 transition" onClick={() => addNewTrialRow(index, trial_index)}>+ Add Trial Row</button>
                      )}
                    </div>
                  ))}
                </div>

                {/* Extracted Cancer */}
                <div>
                  <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1">Defined Cancer</label>
                  <AutoResizeTextarea key={`${currentSetId}-indication-${index}-extractedcancer`} content={indication.extracted_cancer} disabled={false} onChange={(value) => handleIndicationChange(index, 'extracted_cancer', value)} placeholder="Defined Cancer" />
                </div>

                {/* Broad Cancer Categories */}
                <div>
                  <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1">Broad Cancer Categories</label>
                  <div className="flex flex-wrap gap-1.5 mb-2">
                    {Array.isArray(indication.broad_cancer) && indication.broad_cancer.map((bc, bcIdx) => (
                      <span key={`${currentSetId}-indication-${index}-bc-chip-${bcIdx}`} className="px-2.5 py-1 text-xs rounded-full bg-indigo-50 text-indigo-700 border border-indigo-200 font-medium">{bc}</span>
                    ))}
                  </div>
                  <select
                    multiple
                    className="w-full p-2 text-sm border border-slate-200 rounded-lg bg-slate-50 focus:ring-2 focus:ring-indigo-200 focus:outline-none"
                    value={Array.isArray(indication.broad_cancer) ? indication.broad_cancer : []}
                    onChange={(e) => { const selected = Array.from(e.target.selectedOptions).map(o => o.value); handleBroadCancerChange(index, selected) }}
                  >
                    {BROAD_CANCER_OPTIONS.map((opt) => (<option key={`${currentSetId}-indication-${index}-bc-opt-${opt}`} value={opt}>{opt}</option>))}
                  </select>
                  <div className="text-[10px] text-slate-400 mt-1">Hold Cmd/Ctrl to select multiple.</div>
                </div>

                {/* Description */}
                <div>
                  <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1">Description</label>
                  <AutoResizeTextarea key={`${currentSetId}-indication-${index}-description`} content={indication.description} disabled={false} onChange={(value) => handleIndicationChange(index, 'description', value)} placeholder="Paste the full indication description here, then click AI Autofill" />
                </div>

                {/* Structured Fields - 2 column grid */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {[
                    { key: 'line_of_therapy', label: 'Line of Therapy', placeholder: 'e.g. First-Line, Second-Line, Adjuvant' },
                    { key: 'previous_tx', label: 'Previously Treated With', placeholder: 'Prior treatments required' },
                    { key: 'combined_with', label: 'In Combination With', placeholder: 'Combination drugs' },
                    { key: 'stage', label: 'Stage', placeholder: 'e.g. Metastatic, Early-stage' },
                    { key: 'gene_specificity', label: 'Gene / Biomarker', placeholder: 'e.g. BRAF V600E, HER2+' },
                    { key: 'rair_eligibility', label: 'Eligibility (RAIR)', placeholder: 'e.g. FDA-authorized test' },
                    { key: 'resection_status', label: 'Resection Status', placeholder: 'e.g. Resected, Unresectable' },
                  ].map(field => (
                    <div key={`${currentSetId}-indication-${index}-${field.key}`}>
                      <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1">{field.label}</label>
                      <AutoResizeTextarea
                        key={`${currentSetId}-indication-${index}-${field.key}-textarea`}
                        content={indication[field.key]}
                        disabled={false}
                        onChange={(value) => handleIndicationChange(index, field.key, value)}
                        placeholder={field.placeholder}
                      />
                    </div>
                  ))}
                  <div className="md:col-span-2">
                    <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1">Other</label>
                    <AutoResizeTextarea key={`${currentSetId}-indication-${index}-other`} content={indication.other} disabled={false} onChange={(value) => handleIndicationChange(index, 'other', value)} placeholder="Additional relevant information" />
                  </div>
                </div>
              </div>
            </div>
          ))}

          {/* Add Indication Button */}
          <button
            className="w-full p-3 rounded-xl border-2 border-dashed border-indigo-300 text-indigo-600 font-semibold text-sm hover:bg-indigo-50 transition"
            onClick={addNewRow}
          >
            + Add New Indication
          </button>

          {/* Comments */}
          <div className="rounded-xl border border-slate-200 bg-white p-5">
            <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">Comments</label>
            <AutoResizeTextarea key={`${currentSetId}-comments`} content={drugComments} disable={false} onChange={(value) => handleCommentChange(value)} placeholder='Enter comments about this drug...' />
          </div>

          <div className="h-8"></div>
        </div>

        {/* Right Panel - DailyMed iframe */}
        {drugData['SetID'] && (
          <div className="lg:col-span-2 border-l border-slate-200 bg-white flex flex-col">
            <div className="flex border-b border-slate-200">
              <button
                className={`flex-1 px-4 py-2.5 text-xs font-medium transition ${sidebarTab === 'dailymed' ? 'text-indigo-700 border-b-2 border-indigo-600 bg-indigo-50/50' : 'text-slate-500 hover:text-slate-700'}`}
                onClick={() => setSidebarTab('dailymed')}
              >
                DailyMed
              </button>
              <button
                className={`flex-1 px-4 py-2.5 text-xs font-medium transition ${sidebarTab === 'fda' ? 'text-indigo-700 border-b-2 border-indigo-600 bg-indigo-50/50' : 'text-slate-500 hover:text-slate-700'}`}
                onClick={() => setSidebarTab('fda')}
              >
                FDA Source
              </button>
            </div>
            {sidebarTab === 'dailymed' ? (
              <iframe src={`https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=${drugData['SetID']}#anch_dj_dj-dj_13`} className='w-full flex-1' />
            ) : (
              prInfo['Source Link for Press'] ? (
                <iframe src={prInfo['Source Link for Press']} className='w-full flex-1' />
              ) : (
                <div className="flex items-center justify-center flex-1 text-sm text-slate-400">No FDA source link available</div>
              )
            )}
          </div>
        )}
      </div>
    </div>
  )
}
