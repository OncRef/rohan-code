import { NextResponse } from 'next/server'
import clientPromise from '@/lib/mongodb'

export async function POST() {
    try {
        // console.log('Doing cleanup')
        const client = await clientPromise;
        const db = client.db('OncRef_Game');

        const result = await db.collection('original_drug_data').updateMany(
            { '$and': [ { 'locked': 'Y' }, { 'approved': 'N' } ] },
            { '$set': {
                'locked': 'N'
            }
        })

        return NextResponse.json({ success: true })
    } catch (error) {
        console.error("Failed to lock drug:", error);
        return NextResponse.json({ success: false, error: error.message }, { status: 500 })
    }
}