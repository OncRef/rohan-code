import { NextResponse } from 'next/server'
import clientPromise from '@/lib/mongodb'
import { DB_NAME, COLLECTION_NAME } from '@/lib/config'

export async function POST(request) {
  try {
    const { setId } = await request.json()
    if (!setId) {
      return NextResponse.json({ success: false, error: 'No setId provided' })
    }

    const client = await clientPromise
    const db = client.db(DB_NAME)

    const result = await db.collection(COLLECTION_NAME).updateOne(
      { '_id': setId },
      { 
        $set: {
          locked: 'N'
        },
        $unset: {
          locked_at: ""
              }      }
    )

    if (!result.acknowledged) {
      return NextResponse.json({ success: false, error: 'Failed to unlock document' })
    }

    return NextResponse.json({ success: true })
  } catch (error) {
    console.error('Failed to unlock:', error)
    return NextResponse.json({ success: false, error: error.message }, { status: 500 })
  }
}
