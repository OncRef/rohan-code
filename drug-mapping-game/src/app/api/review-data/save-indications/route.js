import { NextResponse } from 'next/server'
import clientPromise from '@/lib/mongodb'
import isEqual from 'lodash/isEqual'

function isEmpty(obj) {
  for (const prop in obj) {
    if (Object.hasOwn(obj, prop)) {
      return false;
    }
  }
  return true;
}

function areAllValuesEmpty(obj) {
  return Object.values(obj).every(value => value.trim() === "");
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

      let drugInfo = await db.collection("new_drug_data").findOne({ '_id': setId });
      let oldIndications = drugInfo['indications'];
      let changesMade = 'N';
      if (!isEqual(oldIndications, newIndications)) changesMade = 'Y';

      console.log('Changes made:', changesMade)

      // let { dailymed_indications, openfda_indications, open_ai_indications, locked, approved, ...newObject } = drugInfo;

      // newObject['indications'] = newIndications
      // newObject['approved_by'] = playerName
      // Update or insert drug data in collectionOne
      await db.collection("new_drug_data").updateOne(
        { '_id': setId },
        { $set: {
          'indications': newIndications,
          'reviewed': 'Y',
          'locked': 'N',
          'reviewed_by': playerName,
          'changes_made': changesMade
        } },
      )

      if (drugInfo['bucket'] === 'second_pass') {
        await db.collection("original_drug_data").updateMany(
          { 'master_set_id': setId },
          {
            $set: {
              'master_reviewed': 'Y',
              'processedind': newIndications
            }
          }
        )
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