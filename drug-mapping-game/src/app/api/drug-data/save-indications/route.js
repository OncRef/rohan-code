import { NextResponse } from 'next/server'
import clientPromise from '@/lib/mongodb'

function isEmpty(obj) {
  for (const prop in obj) {
    if (Object.hasOwn(obj, prop)) {
      return false;
    }
  }
  return true;
}

function areAllValuesEmpty(obj) {
  if (Array.isArray(obj)) {
    return obj.every(value => areAllValuesEmpty(value));
  }

  if (typeof obj === 'object' && obj !== null) {
    return Object.values(obj).every(value => areAllValuesEmpty(value));
  }

  return String(obj).trim() === "";
}

function areAllObjectsEmpty(list) {
  return list.every(obj => areAllValuesEmpty(obj));
}

function removeEmptyObjects(list) {
  return list.filter(obj => !areAllValuesEmpty(obj));
}

export async function POST(request) {
  try {
    const { drugData, indications, playerName } = await request.json()
    const setId = drugData['SetID']    
    
    const newIndications = removeEmptyObjects(indications)

    if (newIndications.length != 0) {
      const client = await clientPromise
      const db = client.db("OncRef_Game")
      let drugInfo = await db.collection("original_drug_data").findOne({ '_id': setId });
      let { dailymed_indications, openfda_indications, open_ai_indications, locked, approved, ...newObject } = drugInfo;

      newObject['indications'] = newIndications
      newObject['approved_by'] = playerName
      newObject['locked'] = 'N'
      newObject['reviewed'] = 'N'
      // Update or insert drug data in collectionOne
      await db.collection("original_drug_data").updateOne(
        { '_id': setId },
        { $set: {
          'approved': 'Y',
          'locked': 'N',
          'approved_by': playerName
        } },
      )

      // Insert indications into collectionTwo
      if (newIndications.length > 0) {
        await db.collection("new_drug_data").insertOne(newObject)
      }
      return NextResponse.json({ success: true })
    }
    else {
      return NextResponse.json({ success: false, error: 'Submitted empty indications' })
    }
  } catch (error) {
    console.error('Failed to save data:', error)
    return NextResponse.json({ success: false, error: error.message }, { status: 500 })
  }
}