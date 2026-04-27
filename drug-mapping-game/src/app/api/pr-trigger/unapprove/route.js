import { NextResponse } from 'next/server'
import clientPromise from '@/lib/mongodb'
import { DB_NAME, COLLECTION_NAME } from '@/lib/config'

export async function POST(request) {
  try {
    const { setId } = await request.json()
    if (!setId) {
      return NextResponse.json({ success: false, error: 'No setId provided' }, { status: 400 })
    }

    const client = await clientPromise
    const db = client.db(DB_NAME)

    const result = await db.collection(COLLECTION_NAME).updateOne(
      { '_id': setId },
      { 
        $set: {
          approved: 'N'
        },
        $unset: {
          approved_at: '',
          approved_by: ''
        }
      }
    )

    if (!result.acknowledged) {
      return NextResponse.json({ success: false, error: 'Failed to unapprove document' }, { status: 500 })
    }

    return NextResponse.json({ success: true })
  } catch (error) {
    console.error('Failed to unapprove:', error)
    return NextResponse.json({ success: false, error: error.message }, { status: 500 })
  }
}


