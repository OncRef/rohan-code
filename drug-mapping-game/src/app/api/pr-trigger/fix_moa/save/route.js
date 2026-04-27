import { NextResponse } from 'next/server'
import clientPromise from '@/lib/mongodb'
import { DB_NAME, COLLECTION_NAME } from '@/lib/config'

export const dynamic = 'force-dynamic'

export async function POST(request) {
  try {
    const { setId, shortMoa } = await request.json()
    
    if (!setId || shortMoa === undefined) {
      return NextResponse.json({ success: false, error: 'Missing required fields' }, { status: 400 })
    }

    const client = await clientPromise
    const db = client.db(DB_NAME)
    
    const result = await db.collection(COLLECTION_NAME).updateOne(
      { '_id': setId },
      { 
        $set: { 
          short_moa: shortMoa,
          short_moa_updated_at: new Date()
        }
      }
    )

    if (result.matchedCount === 0) {
      return NextResponse.json({ error: 'Drug not found' }, { status: 404 })
    }

    return NextResponse.json({ message: 'Successfully updated' })
  } catch (e) {
    console.error(e)
    return NextResponse.json({ error: 'Internal Server Error' }, { status: 500 })
  }
}