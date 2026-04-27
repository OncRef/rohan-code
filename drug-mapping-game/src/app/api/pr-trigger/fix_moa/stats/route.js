import { NextResponse } from 'next/server'
import clientPromise from '@/lib/mongodb'
import { DB_NAME, COLLECTION_NAME } from '@/lib/config'

export const dynamic = 'force-dynamic'

export async function GET() {
  try {
    const client = await clientPromise
    const db = client.db(DB_NAME)

    // Find all drugs that have a short_moa field that is not empty
    const query = {
      short_moa: { $exists: true, $ne: "" }
    }

    const drugs = await db.collection(COLLECTION_NAME)
      .find(query)
      .project({
        _id: 1,
        generic_name: 1,
        brand_name: 1,
        short_moa: 1,
        short_moa_updated_at: 1
      })
      .sort({ generic_name: 1 })
      .toArray()

    return NextResponse.json({ 
      success: true, 
      drugs,
      count: drugs.length
    })
  } catch (error) {
    console.error('Failed to fetch MOA stats:', error)
    return NextResponse.json({ 
      success: false, 
      error: 'Failed to fetch MOA statistics' 
    }, { 
      status: 500 
    })
  }
}