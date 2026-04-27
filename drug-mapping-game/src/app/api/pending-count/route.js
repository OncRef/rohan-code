import { NextResponse } from 'next/server'
import clientPromise from '@/lib/mongodb'
import { DB_NAME, COLLECTION_NAME } from '@/lib/config'

export async function GET(request) {
  try {
    const { searchParams } = new URL(request.url)
    const game = searchParams.get('game') || 'pr-trigger'

    const client = await clientPromise
    let count = 0

    if (game === 'pr-trigger') {
      const db = client.db(DB_NAME)
      count = await db.collection(COLLECTION_NAME).countDocuments({ approved: 'N' })
    } else if (game === 'drug-data') {
      const db = client.db('OncRef_Game')
      count = await db.collection('original_drug_data').countDocuments({ approved: 'N', flag: { $ne: 'Y' } })
    } else if (game === 'ncts') {
      const db = client.db('OncRef_Game')
      count = await db.collection('new_drug_data').countDocuments({ nct_game_approved: 'N', nct_game_locked: 'N' })
    } else if (game === 'ncts-flagged') {
      const db = client.db('OncRef_Game')
      count = await db.collection('new_drug_data').countDocuments({ nct_game_approved: 'N', nct_game_flag: 'Y' })
    } else if (game === 'review') {
      const db = client.db('OncRef_Game')
      count = await db.collection('new_drug_data').countDocuments({ reviewed: { $ne: 'Y' } })
    }

    return NextResponse.json({ count })
  } catch (error) {
    console.error('Failed to get pending count:', error)
    return NextResponse.json({ count: '?' }, { status: 500 })
  }
}
