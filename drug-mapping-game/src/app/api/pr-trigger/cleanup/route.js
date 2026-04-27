import { NextResponse } from 'next/server'
import clientPromise from '@/lib/mongodb'
import { DB_NAME, COLLECTION_NAME } from '@/lib/config'

export async function POST() {
  try {
    const client = await clientPromise
    const db = client.db(DB_NAME)

    // Reset all locked documents that haven't been approved
    const result = await db.collection(COLLECTION_NAME).updateMany(
      {
        locked: 'Y',
        $or: [
          { approved: { $ne: 'Y' } },
          { approved: { $exists: false } }
        ]
      },
      {
        $set: {
          locked: 'N'
        },
        $unset: {
          locked_at: ""
        }
      }
    )

    return NextResponse.json({ success: true, modified: result.modifiedCount })
  } catch (error) {
    console.error('Failed to cleanup:', error)
    return NextResponse.json({ success: false, error: error.message }, { status: 500 })
  }
}
