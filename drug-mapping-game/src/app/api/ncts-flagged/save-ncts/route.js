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
    const { drugData, indications, playerName, brandName, drugComments } = await request.json()
    const setId = drugData['SetID']    
    
    const newIndications = removeEmptyObjects(indications)

    for (let indication of newIndications) {
      Object.keys(indication).forEach(key => indication[key] = typeof indication[key] == 'string' ? indication[key].trim(): indication[key]);
      if (indication.hasOwnProperty('trials')) {
        indication['trials'] = removeEmptyObjects(indication['trials'])
        for (let trial of indication['trials']) {
          trial['sub_cancer'] = trial['sub_cancer'].trim()
          trial['ncts'] = trial['ncts'].trim().replaceAll("\n", ", ")
        }
      } else {
        indication['trials'] = []
      }
    }

    const currentTimestamp = new Date();

    // console.dir(newIndications, { depth: null })

    if (newIndications.length != 0) {
      const client = await clientPromise
      const db = client.db("OncRef_Game")
      // let drugInfo = await db.collection("all_drugs").findOne({ '_id': setId });

      // Update all_drugs collection for current setid
      let result = await db.collection("all_drugs").updateOne(
        { '_id': setId },
        { $set: {
          brand_name: brandName.trim(),
          indications: newIndications,
          nct_game_approved: 'Y',
          nct_game_locked: 'N',
          nct_game_approved_by: playerName,
          updated_at: currentTimestamp,
          game_comments: drugComments
        } },
      )

      if (!result.acknowledged) return NextResponse.json({ success: false, error: 'Update Failed' })

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