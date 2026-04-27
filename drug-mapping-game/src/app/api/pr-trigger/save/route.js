import { NextResponse } from 'next/server'
import clientPromise from '@/lib/mongodb'
import { DB_NAME, COLLECTION_NAME } from '@/lib/config'

export async function POST(request) {
  try {
    const {
      drugData,
      indications,
      playerName,
      brandName,
      moa,
      packager,
      drugComments,
      needsReview,
      removeNeedsReview,
      fcode,
      effectiveDate
    } = await request.json()
    const setId = drugData['SetID']

    // Clean up indications data
    const cleanIndications = indications.filter(ind => {
      // Remove empty indications
      const hasContent = Object.values(ind).some(val => val && val.toString().trim().length > 0)
      if (!hasContent) return false

      // Clean up trials data
      if (ind.trials) {
        ind.trials = ind.trials.filter(trial => {
          return trial.sub_cancer?.trim() || trial.ncts?.trim()
        })
        ind.trials.forEach(trial => {
          trial.sub_cancer = trial.sub_cancer?.trim() || ''
          trial.ncts = trial.ncts?.trim().replaceAll("\n", ", ") || ''
        })
      }

      return true
    })

    const client = await clientPromise
    const db = client.db(DB_NAME)

    // Get existing document to preserve any existing indications
    const existingDoc = await db.collection(COLLECTION_NAME).findOne({ '_id': setId })
    const existingIndications = existingDoc?.indications || []

    // Merge existing and new indications
    const mergedIndications = [...existingIndications, ...cleanIndications]

    // Prepare update object
    const updateData = {
      brand_name: brandName?.trim() || '',
      moa: moa?.trim() || '',
      packager: packager?.trim() || '',
      fcode: fcode?.trim() || '',
      effective_date: effectiveDate?.trim() || '',
      indications: mergedIndications,
      approved: 'Y',
      submitted_by: playerName,
      submitted_at: new Date(),
      comments: drugComments?.trim() || '',
      locked: 'N'
    }

    // Handle needs review flag
    if (needsReview) {
      updateData.needs_review = 'Y'
      updateData.needs_review_at = new Date()
    } else if (removeNeedsReview) {
      updateData.needs_review = 'N'
      updateData.reviewed_at = new Date()
      updateData.reviewed_by = playerName
    }

    // Update the document
    const result = await db.collection(COLLECTION_NAME).updateOne(
      { '_id': setId },
      {
        $set: updateData,
        $unset: removeNeedsReview ? { needs_review_at: "" } : {}
      }
    )

    if (!result.acknowledged) {
      return NextResponse.json({ success: false, error: 'Failed to update document' })
    }

    return NextResponse.json({ success: true })
  } catch (error) {
    console.error('Failed to save data:', error)
    return NextResponse.json({ success: false, error: error.message }, { status: 500 })
  }
}
