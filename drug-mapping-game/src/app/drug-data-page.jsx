'use client'

import { useState, useEffect } from 'react'
import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { Input } from '@/components/ui/input'
import { PlusCircle } from 'lucide-react'

export default function Component() {
  const [drugData, setDrugData] = useState({
    setid: "LINK123",
    genericName: "Sample Generic",
    brandName: "Sample Brand",
    fcode: "F123",
    moa: "Sample MOA"
  })

  const [indications, setIndications] = useState([
    { title: '', description: '' }
  ])

  const [oldIndications, setOldIndications] = useState([
    "Treatment of hypertension",
    "Management of chronic heart failure",
    "Reduction of cardiovascular mortality in patients with left ventricular dysfunction following myocardial infarction",
    "Prevention of stroke in patients with hypertension and left ventricular hypertrophy",
    "Treatment of diabetic nephropathy in patients with type 2 diabetes and hypertension",
    "Management of proteinuria in patients with chronic kidney disease",
    "Reduction of blood pressure in pediatric patients with hypertension",
    "Treatment of essential tremor",
    "Prophylaxis of migraine headaches",
    "Management of anxiety disorders",
    "Adjunctive therapy in the treatment of partial seizures in adults with epilepsy",
    "Treatment of neuropathic pain associated with diabetic peripheral neuropathy",
    "Management of fibromyalgia",
    "Treatment of postherpetic neuralgia",
    "Adjunctive therapy for adults with partial onset seizures",
    "Management of generalized anxiety disorder",
    "Treatment of social anxiety disorder",
    "Management of panic disorder with or without agoraphobia",
    "Adjunctive treatment of major depressive disorder",
    "Management of overactive bladder"
  ])

  const [openFDA, setOpenFDA] = useState(`
    BOXED WARNING:
    WARNING: FETAL TOXICITY
    • When pregnancy is detected, discontinue drug as soon as possible.
    • Drugs that act directly on the renin-angiotensin system can cause injury and death to the developing fetus.

    INDICATIONS AND USAGE:
    Sample Generic (brandname) is an angiotensin II receptor blocker (ARB) indicated for:
    • Treatment of hypertension, to lower blood pressure in adults and children 6 years and older. Lowering blood pressure reduces the risk of fatal and nonfatal cardiovascular events, primarily strokes and myocardial infarctions.
    • Reduction of the risk of stroke in patients with hypertension and left ventricular hypertrophy. There is evidence that this benefit does not apply to Black patients.

    DOSAGE AND ADMINISTRATION:
    • May be administered with or without food
    • Recommended starting dose in adults is 50 mg once daily
    • Can be used alone or in combination with other antihypertensive agents

    DOSAGE FORMS AND STRENGTHS:
    • Tablets: 25 mg, 50 mg, 100 mg

    CONTRAINDICATIONS:
    • Do not co-administer aliskiren with Sample Generic in patients with diabetes.

    WARNINGS AND PRECAUTIONS:
    • Avoid fetal or neonatal exposure
    • Hypotension: Correct volume or salt depletion prior to administration of Sample Generic
    • Monitor renal function and potassium in susceptible patients

    ADVERSE REACTIONS:
    Most common adverse reactions (incidence ≥2% and greater than placebo) are:
    • Dizziness
    • Upper respiratory infection
    • Nasal congestion
    • Back pain
    • Diarrhea
    • Fatigue
    • Pain in extremity

    DRUG INTERACTIONS:
    • Dual blockade of the renin-angiotensin system: Increased risk of renal impairment, hypotension, and hyperkalemia
    • Lithium: Increases in serum lithium concentrations and lithium toxicity have been reported
    • NSAIDs: Increased risk of renal impairment and loss of antihypertensive effect
    • Potassium-sparing diuretics, potassium supplements, salt substitutes: Monitor serum potassium levels

    USE IN SPECIFIC POPULATIONS:
    • Lactation: Breastfeeding is not recommended
    • Pediatric Use: Use of Sample Generic in children < 1 year of age is not recommended
    • Geriatric Use: No overall differences in efficacy or safety were observed between these patients and younger patients

    This is a summary of the most important information about Sample Generic. For more detailed information, talk with your healthcare provider.
  `)

  const [openAI, setOpenAI] = useState({
    "Current Indications": "Hypertension treatment, Chronic heart failure management, Cardiovascular mortality reduction post-myocardial infarction, Stroke prevention in hypertensive patients with left ventricular hypertrophy, Diabetic nephropathy treatment, Proteinuria management in chronic kidney disease",
    "Mechanism of Action": "Angiotensin II Receptor Blocker (ARB). ARBs work by blocking the action of angiotensin II, a hormone that causes blood vessels to narrow, thereby reducing blood pressure.",
    "Potential New Indications": "Cognitive Function Improvement, COVID-19 Treatment, Aortic Aneurysm Prevention, Cancer Therapy Adjunct, Atrial Fibrillation Prevention, Migraine Prophylaxis, Parkinson's Disease, Osteoporosis",
    "Considerations for New Indications": "Further clinical trials necessary, Monitor kidney function and potassium levels, Investigate potential interactions, Consider contraindication with aliskiren in diabetic patients",
    "Conclusion": "While current indications focus on cardiovascular and renal conditions, the drug's mechanism suggests potential for broader applications. Extensive research and clinical trials required for validation and safety assurance."
  })

  useEffect(() => {
    // Fetch data for the right panels
    const fetchData = async () => {
      try {
        const response = await fetch(`/api/drug-data?setid=${drugData.setid}`)
        const data = await response.json()
        setOldIndications(data.oldIndications || oldIndications)
        setOpenFDA(data.openFDA || openFDA)
        setOpenAI(data.openAI || openAI)
      } catch (error) {
        console.error('Failed to fetch data:', error)
      }
    }

    fetchData()
  }, [drugData.setid])

  const handleIndicationChange = (index, field, value) => {
    const newIndications = [...indications]
    newIndications[index] = { ...newIndications[index], [field]: value }
    setIndications(newIndications)
  }

  const addNewRow = (index) => {
    const newIndications = [...indications]
    newIndications.splice(index + 1, 0, { title: '', description: '' })
    setIndications(newIndications)
  }

  const handleSave = async () => {
    try {
      const response = await fetch('/api/save-indications', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ drugData, indications })
      })
      if (!response.ok) throw new Error('Failed to save')
      // Handle success (e.g., show a success message)
      console.log('Data saved successfully')
    } catch (error) {
      // Handle error (e.g., show an error message)
      console.error('Failed to save:', error)
    }
  }

  return (
    <div className="min-h-screen bg-background p-6">
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left Section */}
        <div className="space-y-6">
          {/* Drug Information Card */}
          <Card className="p-6">
            <dl className="space-y-2">
              <div className="flex justify-between">
                <dt className="font-medium">Setid:</dt>
                <dd className="text-muted-foreground">{drugData.setid}</dd>
              </div>
              <div className="flex justify-between">
                <dt className="font-medium">Drug name - Generic:</dt>
                <dd className="text-muted-foreground">{drugData.genericName}</dd>
              </div>
              <div className="flex justify-between">
                <dt className="font-medium">Drug name - brand:</dt>
                <dd className="text-muted-foreground">{drugData.brandName}</dd>
              </div>
              <div className="flex justify-between">
                <dt className="font-medium">Fcode:</dt>
                <dd className="text-muted-foreground">{drugData.fcode}</dd>
              </div>
              <div className="flex justify-between">
                <dt className="font-medium">MOA:</dt>
                <dd className="text-muted-foreground">{drugData.moa}</dd>
              </div>
            </dl>
          </Card>

          {/* Indications Form */}
          <Card className="p-6">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Indication Title</TableHead>
                  <TableHead>Description</TableHead>
                  <TableHead className="w-[50px]"></TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {indications.map((indication, index) => (
                  <TableRow key={index}>
                    <TableCell>
                      <Input
                        value={indication.title}
                        onChange={(e) => handleIndicationChange(index, 'title', e.target.value)}
                        placeholder="Enter title"
                      />
                    </TableCell>
                    <TableCell>
                      <Input
                        value={indication.description}
                        onChange={(e) => handleIndicationChange(index, 'description', e.target.value)}
                        placeholder="Enter description"
                      />
                    </TableCell>
                    <TableCell>
                      <Button
                        size="icon"
                        variant="ghost"
                        onClick={() => addNewRow(index)}
                      >
                        <PlusCircle className="h-4 w-4" />
                        <span className="sr-only">Add new row</span>
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
            <div className="mt-4 flex justify-end space-x-4">
              <Button onClick={handleSave}>Save</Button>
              <Button onClick={() => addNewRow(indications.length - 1)}>Next</Button>
            </div>
          </Card>
        </div>

        {/* Right Section */}
        <div className="grid grid-rows-3 gap-6 h-[calc(100vh-3rem)]">
          <Card className="p-6 overflow-hidden flex flex-col">
            <h2 className="mb-4 text-lg font-semibold">Old Indications</h2>
            <div className="overflow-y-auto flex-grow">
              <ul className="list-disc pl-5 text-sm text-muted-foreground">
                {oldIndications.map((indication, index) => (
                  <li key={index} className="mb-2">{indication}</li>
                ))}
              </ul>
            </div>
          </Card>
          
          <Card className="p-6 overflow-hidden flex flex-col">
            <h2 className="mb-4 text-lg font-semibold">OpenFDA</h2>
            <div className="overflow-y-auto flex-grow">
              <p className="text-sm text-muted-foreground whitespace-pre-line">{openFDA}</p>
            </div>
          </Card>
          
          <Card className="p-6 overflow-hidden flex flex-col">
            <h2 className="mb-4 text-lg font-semibold">OpenAI Indications</h2>
            <div className="overflow-y-auto flex-grow">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Category</TableHead>
                    <TableHead>Description</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {Object.entries(openAI).map(([key, value]) => (
                    <TableRow key={key}>
                      <TableCell className="font-medium">{key}</TableCell>
                      <TableCell>{value}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </Card>
        </div>
      </div>
    </div>
  )
}