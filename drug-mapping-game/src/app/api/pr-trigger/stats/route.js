import { NextResponse } from 'next/server'
import clientPromise from '@/lib/mongodb'
import { DB_NAME, COLLECTION_NAME } from '@/lib/config'

export async function GET(request) {
  try {
    const { searchParams } = new URL(request.url)
    const player = searchParams.get('player')
    const filter = searchParams.get('filter') // needs_review | approved | not_approved | locked

    const query = {}

    // Optional player filter
    if (player && player !== 'DEFAULT') {
      query.submitted_by = player
    }

    // Status filters
    if (filter === 'needs_review') {
      query.needs_review = 'Y'
    } else if (filter === 'approved') {
      query.approved = 'Y'
    } else if (filter === 'not_approved') {
      query.approved = 'N'
      // query.$or = [
      //   { approved: { $ne: 'Y' } },
      //   { approved: { $exists: false } }
      // ]
    } else if (filter === 'locked') {
      query.locked = 'Y'
    }

    const client = await clientPromise
    const db = client.db(DB_NAME)

    // Find all documents by filter(s)
    const cursor = db.collection(COLLECTION_NAME)
      .find(query)
      .sort({ submitted_at: -1 }) // Most recent first

    const data = await cursor.toArray()

    return NextResponse.json({ data })
  } catch (error) {
    console.error('Failed to fetch stats:', error)
    return NextResponse.json({ success: false, error: error.message }, { status: 500 })
  }
}
