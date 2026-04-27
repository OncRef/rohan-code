import { NextResponse } from 'next/server'
import clientPromise from '@/lib/mongodb'
import { DB_NAME, COLLECTION_NAME } from '@/lib/config'

export const dynamic = 'force-dynamic'

export async function GET(request) {
  try {
    const client = await clientPromise
    const db = client.db(DB_NAME)

    const { searchParams } = new URL(request.url)
    const setId = searchParams.get('setId')

    let query = {
      $and: [
        {
          $or: [
            { fcode: { $exists: false } },
            { fcode: null },
            { fcode: '' }
          ]
        },
        { approved: 'Y' },
        { locked: { $ne: 'Y' } }
      ]
    }

    if (setId) {
      query = { _id: setId }
    }

    const sortCriteria = {
      generic_name: 1,
      _id: 1
    }

    const drug = await db.collection(COLLECTION_NAME).findOne(query, { sort: sortCriteria })

    if (!drug) {
      return NextResponse.json({ message: 'No drugs found' }, { status: 404 })
    }

    return NextResponse.json(drug)
  } catch (error) {
    console.error('Failed to fetch drug needing F-Code:', error)
    return NextResponse.json({ error: 'Internal Server Error' }, { status: 500 })
  }
}
