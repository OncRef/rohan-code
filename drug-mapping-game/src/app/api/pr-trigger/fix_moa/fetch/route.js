import { NextResponse } from 'next/server'
import clientPromise from '@/lib/mongodb'
import { DB_NAME, COLLECTION_NAME } from '@/lib/config'

export const dynamic = 'force-dynamic'

export async function GET(request) {
  try {
        const client = await clientPromise;
        const db = client.db(DB_NAME)
        const { searchParams } = new URL(request.url)
        const setId = searchParams.get('setId')

    let query = {
      $and: [
        { application_number: { $regex: '^(NDA|BLA)', $options: 'i' } },
        { $or: [
          { short_moa: { $exists: false } },
          { short_moa: null },
          { short_moa: "" }
        ]},
        { approved: "Y" }  // Only look at approved drugs
      ]
    }

    // If setId is provided, prioritize that specific drug
    if (setId) {
      query = { _id: setId }
    }

    const sortCriteria = {
      generic_name: 1,
      _id: 1
    }

    const drug = await db.collection(COLLECTION_NAME).findOne(query, { sort: sortCriteria })
    
    if (!drug) {
      return NextResponse.json({ message: "No drugs found" }, { status: 404 })
    }

    return NextResponse.json(drug)
  } catch (e) {
    console.error(e)
    return NextResponse.json({ error: 'Internal Server Error' }, { status: 500 })
  }
}