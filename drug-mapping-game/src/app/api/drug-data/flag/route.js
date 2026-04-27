import { NextResponse } from 'next/server'
import clientPromise from '../../../../lib/mongodb'

export async function POST(request) {
    try {
        const { setId } = await request.json();
        // console.log('Called unlock for', setId)
        const client = await clientPromise;
        const db = client.db('OncRef_Game');
        
        const result = await db.collection('original_drug_data').updateOne(
            { '_id': setId },
            { '$set': {
                'locked': 'N',
                'flag': 'Y'
            } 
        })

        console.log(result)

        return NextResponse.json({ success: true })
    } catch (error) {
        console.error("Failed to lock drug:", error);
        return NextResponse.json({ success: false, error: error.message }, { status: 500 })
    }
}