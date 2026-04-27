import { NextResponse } from 'next/server'
import clientPromise from '@/lib/mongodb'
import { DB_NAME, COLLECTION_NAME } from '@/lib/config'

export async function GET() {
  try {
    const client = await clientPromise
    const db = client.db(DB_NAME)
    const count = await db.collection(COLLECTION_NAME).countDocuments({ approved: 'N' })
    return NextResponse.json({ count })
  } catch (error) {
    console.error('Failed to get pending count:', error)
    return NextResponse.json({ count: '?' }, { status: 500 })
  }
}
