import { NextResponse } from 'next/server'
import clientPromise from '@/lib/mongodb'
import { DB_NAME, COLLECTION_NAME } from '@/lib/config'
export async function GET(request) {
    try {
        const client = await clientPromise;
        const db = client.db(DB_NAME)
        const { searchParams } = new URL(request.url)
        const setId = searchParams.get('setId')

        const filters1 = setId ? { _id: setId } : {
            approved: 'N',
            locked: 'N'
        }

        const sortCriteria = {
            generic_name: 1,
            _id: 1
        }
        const drug = await db.collection(COLLECTION_NAME).findOne(filters1, {sort: sortCriteria})
        return NextResponse.json(drug);
    } catch (error) {
        console.error("Failed to fetch drug:", error);
        return NextResponse.json({ success: false, error: error.message }, { status: 500 })
    }
}