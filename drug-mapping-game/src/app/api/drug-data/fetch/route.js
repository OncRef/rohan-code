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

        const filters1 = {
            approved: 'N',
            locked: 'N',
            flag: { $ne: 'Y' },
            bucket: 'second_pass'
        }

        const filters2 = {
            approved: 'N',
            locked: 'N',
            flag: { $ne: 'Y' },
            bucket: 'first_pass',
            master_reviewed: 'Y'
        }

        const pipeline1 = [
            { $match: filters1 },
            { $sample: { size: 1 } }
        ]

        const pipeline2 = [
            { $match: filters2 },
            { $sample: { size: 1 } }
        ]

        let result = await db.collection("original_drug_data").aggregate(pipeline1).toArray()
        // console.log(result.length)
        // let drug = result[0]

        let drug = null
        if (result.length) drug = result[0]
        else {
            result = await db.collection("original_drug_data").aggregate(pipeline2).toArray()
            drug = result[0]
        }

        if (!drug) {
            return NextResponse.json({ success: false, error: 'No pending drugs found' }, { status: 404 })
        }
        return NextResponse.json(drug);
    } catch (error) {
        console.error("Failed to fetch drug:", error);
        return NextResponse.json({ success: false, error: error.message }, { status: 500 })
    }
}