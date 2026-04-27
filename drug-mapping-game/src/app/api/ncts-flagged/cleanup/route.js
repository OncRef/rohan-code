import { NextResponse } from 'next/server'
import clientPromise from '@/lib/mongodb'

export async function POST() {
    try {
        // console.log('Doing cleanup')
        const client = await clientPromise;
        const db = client.db('OncRef_Game');

        const result = await db.collection('all_drugs').updateMany(
            { '$and': [ { 'nct_game_locked': 'Y' }, { 'nct_game_flag': 'Y' } ] },
            // { '$and': [ { 'locked': 'Y' }, { 'ncts_processed': 'N' }, { 'reviewed': 'Y' } ] },
            { '$set': {
                'nct_game_locked': 'N'
            }
        })

        return NextResponse.json({ success: true })
    } catch (error) {
        console.error("Failed to lock drug:", error);
        return NextResponse.json({ success: false, error: error.message }, { status: 500 })
    }
}