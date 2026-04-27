import { NextResponse } from 'next/server'
import clientPromise from '@/lib/mongodb'
import { DB_NAME, COLLECTION_NAME } from '@/lib/config'

export const dynamic = 'force-dynamic'

export async function POST(request) {
  try {
    const { setId, fcode, effectiveDate } = await request.json()

    if (!setId || !fcode) {
      return NextResponse.json({ success: false, error: 'Missing required fields' }, { status: 400 })
    }

    const client = await clientPromise
    const db = client.db(DB_NAME)

    const result = await db.collection(COLLECTION_NAME).updateOne(
      { '_id': setId },
      {
        $set: {
          fcode: fcode.trim(),
          effective_date: effectiveDate?.trim() || '',
          fcode_updated_at: new Date()
        }
      }
    )

    if (result.matchedCount === 0) {
      return NextResponse.json({ error: 'Drug not found' }, { status: 404 })
    }

    return NextResponse.json({ message: 'Successfully updated F-Code information' })
  } catch (error) {
    console.error('Failed to save F-Code info:', error)
    return NextResponse.json({ error: 'Internal Server Error' }, { status: 500 })
  }
}
