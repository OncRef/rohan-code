import { NextResponse } from 'next/server'
import clientPromise from '@/lib/mongodb'

export async function GET() {
    try {
        const client = await clientPromise;
        const db = client.db('OncRef_Game');

        // const drug = await db.collection("original_drug_data").findOne({
        //     'approved': 'N',
        //     'locked': 'N'
        // });

        const filter = {
            reviewed: 'N',
            locked: 'N',
            flag: { $ne: 'Y' },
            bucket: 'first_pass'
        }

        const pipeline = [
            { $match: filter },
            { $sample: { size: 1 } }
        ]
        const result = await db.collection("new_drug_data").aggregate(pipeline).toArray()

        const drug = result[0]
        // console.log(drug)

        return NextResponse.json(drug);
    } catch (error) {
        console.error("Failed to fetch drug:", error);
        return NextResponse.json({ success: false, error: error.message }, { status: 500 })
    }
}